#!/usr/bin/env python3
"""
Vespa Backfill Demo - Real Office Data Integration

This demo performs real backfill operations using the existing office service
infrastructure to crawl real emails, calendar events, and contacts, then
publishes them to Pub/Sub for the Vespa loader service to consume.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# Environment validation - check if virtual environment is active
def validate_environment() -> None:
    """Validate that the virtual environment is active and dependencies are available."""
    try:
        import pydantic

        print("✅ Virtual environment is active - pydantic is available")
    except ImportError:
        print("❌ ERROR: Virtual environment is not active!")
        print("\nThe backfill script requires the virtual environment to be activated.")
        print("Please run the following command first:")
        print("\n  source .venv/bin/activate")
        print("\nOr on Windows:")
        print("\n  .venv\\Scripts\\activate")
        print("\nThen try running the script again:")
        print(f"\n  python {sys.argv[0]} {' '.join(sys.argv[1:])}")
        print("\nThis ensures all required dependencies (like pydantic) are available.")
        sys.exit(1)


# Validate environment before importing other modules
validate_environment()

from services.common.logging_config import get_logger
from services.demos.settings_demos import get_demo_settings
from services.office.api.backfill import BackfillRequest
from services.office.core.email_crawler import EmailCrawler
from services.office.core.pubsub_publisher import PubSubPublisher
from services.office.models.backfill import ProviderEnum
from services.vespa_query.search_engine import SearchEngine

logger = get_logger(__name__)


class VespaBackfillDemo:
    """Real backfill demo using office service infrastructure"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.settings = get_demo_settings()

        # Demo configuration with sensible limits for testing
        self.user_email = config.get("user_email", "trybriefly@outlook.com")
        self.providers = config.get(
            "providers", ["microsoft"]
        )  # Start with just Microsoft
        self.batch_size = config.get("batch_size", 10)  # Small batch size for testing
        self.rate_limit = config.get("rate_limit", 2.0)  # Slower rate for testing
        self.max_emails_per_user = config.get(
            "max_emails_per_user", self.settings.demo_max_emails
        )  # Use centralized setting
        self.start_date = config.get("start_date")
        self.end_date = config.get("end_date")
        self.folders = config.get("folders", ["INBOX"])  # Just INBOX for testing

        # Service endpoints from common settings
        self.office_service_url = self.settings.office_service_url
        self.user_service_url = self.settings.user_service_url

        # Initialize components
        self.pubsub_publisher = PubSubPublisher(
            project_id=config.get("project_id", "briefly-dev"),
            emulator_host=config.get("emulator_host", "localhost:8085"),
        )

        # Initialize Vespa search engine for stats
        self.vespa_endpoint = config.get("vespa_endpoint", "http://localhost:8080")
        self.search_engine = SearchEngine(self.vespa_endpoint)

        # API keys from common settings
        self.api_keys = {
            "office": getattr(
                self.settings, "api_frontend_office_key", "test-FRONTEND_OFFICE_KEY"
            ),
            "user": getattr(
                self.settings, "api_frontend_user_key", "test-FRONTEND_USER_KEY"
            ),
            "backfill": getattr(
                self.settings, "api_backfill_office_key", "test-BACKFILL-OFFICE-KEY"
            ),
        }

        # Keep user ID separate from email; resolved later
        self.user_id: Optional[str] = None

    async def clear_pubsub_topics(self) -> None:
        """Clear Pub/Sub topics to stop flooding"""
        logger.info("Clearing Pub/Sub topics to stop flooding...")
        try:
            # This is a simple approach - in production you'd want more sophisticated cleanup
            logger.warning(
                "Pub/Sub topic clearing not implemented - consider restarting the emulator"
            )
            logger.info(
                "To stop flooding, restart the Pub/Sub emulator or clear topics manually"
            )
        except Exception as e:
            logger.error(f"Failed to clear Pub/Sub topics: {e}")

    async def ensure_pubsub_topics(self) -> None:
        """Ensure required Pub/Sub topics exist"""
        logger.info("Ensuring required Pub/Sub topics exist...")
        try:
            import requests

            # Required topics
            topics = ["email-backfill", "calendar-updates", "contact-updates"]
            project_id = self.settings.pubsub_project_id
            emulator_host = self.settings.pubsub_emulator_host

            for topic in topics:
                topic_path = f"projects/{project_id}/topics/{topic}"

                # First check if topic already exists
                check_url = f"http://{emulator_host}/v1/{topic_path}"
                try:
                    check_response = requests.get(check_url, timeout=5)
                    if check_response.status_code == 200:
                        logger.info(f"✅ Topic {topic} already exists")
                        continue
                except Exception as e:
                    logger.debug(f"Could not check topic {topic}: {e}")

                # Topic doesn't exist, try to create it
                create_url = f"http://{emulator_host}/v1/projects/{project_id}/topics"
                data = {"name": topic_path}

                try:
                    response = requests.post(create_url, json=data, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ Topic {topic} created successfully")
                    elif response.status_code == 409:
                        logger.info(f"✅ Topic {topic} already exists (race condition)")
                    else:
                        logger.error(
                            f"❌ Failed to create topic {topic}: HTTP {response.status_code}"
                        )
                        if response.text:
                            logger.error(f"   Response: {response.text}")
                except Exception as e:
                    logger.error(f"❌ Failed to create topic {topic}: {e}")

            logger.info("Pub/Sub topics check completed")

        except Exception as e:
            logger.error(f"❌ Pub/Sub topics check failed: {e}")
            logger.info("Demo will continue but Pub/Sub publishing may fail")

    async def stop_all_backfill_jobs(self) -> None:
        """Stop all running backfill jobs"""
        logger.info("Stopping all running backfill jobs...")
        try:
            import httpx

            # Get list of running jobs using internal endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Prefer resolved user_id; resolve from email if needed
                target_user_id = (
                    self.user_id
                    if getattr(self, "user_id", None)
                    else await self._resolve_email_to_user_id(self.user_email)
                )
                response = await client.get(
                    f"{self.office_service_url}/internal/backfill/status?user_id={target_user_id}",
                    headers={"X-API-Key": self.api_keys["backfill"]},
                )

                if response.status_code == 200:
                    jobs = response.json()
                    for job in jobs:
                        if job.get("status") == "running":
                            job_id = job.get("job_id")
                            logger.info(f"Cancelling running job: {job_id}")

                            # Cancel the job using internal endpoint
                            cancel_response = await client.delete(
                                f"{self.office_service_url}/internal/backfill/{job_id}?user_id={target_user_id}",
                                headers={"X-API-Key": self.api_keys["backfill"]},
                            )

                            if cancel_response.status_code == 200:
                                logger.info(f"Successfully cancelled job: {job_id}")
                            else:
                                logger.warning(
                                    f"Failed to cancel job {job_id}: {cancel_response.status_code}"
                                )
                else:
                    logger.warning(f"Failed to get job status: {response.status_code}")

        except Exception as e:
            logger.error(f"Error stopping backfill jobs: {e}")

    async def __aenter__(self) -> "VespaBackfillDemo":
        """Async context manager entry"""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit"""
        # Cleanup resources if needed
        if hasattr(self, "search_engine"):
            await self.search_engine.close()

    async def get_user_vespa_stats(self) -> Dict[str, Any]:
        """Get current Vespa statistics for the user"""
        try:
            await self.search_engine.start()

            # Query to get total document count for this user
            user_query = {
                "yql": "select * from briefly_document where true",
                "hits": 1,  # Use 1 to ensure we get the totalCount field
                "timeout": "5s",
                "streaming.groupname": self.user_id,  # Use internal user ID for streaming group
            }

            start_time = time.time()
            results = await self.search_engine.search(user_query)
            query_time = (time.time() - start_time) * 1000

            total_documents = (
                results.get("root", {}).get("fields", {}).get("totalCount", 0)
            )

            # Get breakdown by source type
            source_type_query = {
                "yql": "select source_type from briefly_document where true",
                "hits": 1,
                "timeout": "5s",
                "grouping": "source_type",
                "streaming.groupname": self.user_id,  # Use internal user ID for streaming group
            }

            source_results = await self.search_engine.search(source_type_query)
            source_breakdown = {}

            if "root" in source_results and "children" in source_results["root"]:
                for child in source_results["root"]["children"]:
                    if "value" in child:
                        source_type = child["value"]
                        count = child.get("fields", {}).get("count()", 0)
                        source_breakdown[source_type] = count

            # Get breakdown by provider
            provider_query = {
                "yql": "select provider from briefly_document where true",
                "hits": 1,
                "timeout": "5s",
                "grouping": "provider",
                "streaming.groupname": self.user_id,  # Use internal user ID for streaming group
            }

            provider_results = await self.search_engine.search(provider_query)
            provider_breakdown = {}

            if "root" in provider_results and "children" in provider_results["root"]:
                for child in provider_results["root"]["children"]:
                    if "value" in child:
                        provider = child["value"]
                        count = child.get("fields", {}).get("count()", 0)
                        provider_breakdown[provider] = count

            return {
                "user_email": self.user_email,
                "total_documents": total_documents,
                "source_type_breakdown": source_breakdown,
                "provider_breakdown": provider_breakdown,
                "query_time_ms": round(query_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting Vespa stats for user {self.user_email}: {e}")
            return {
                "user_email": self.user_email,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def print_vespa_stats(
        self, stats: Dict[str, Any], label: str = "VESPA STATISTICS"
    ) -> None:
        """Print Vespa statistics in a formatted way"""
        print(f"\n{'='*60}")
        print(f"{label}: {stats['user_email']}")
        print(f"{'='*60}")

        if "error" in stats:
            print(f"Error: {stats['error']}")
            return

        print(f"Total Documents: {stats.get('total_documents', 0):,}")
        print(f"Query Time: {stats.get('query_time_ms', 0):.2f}ms")

        # Source type breakdown
        source_breakdown = stats.get("source_type_breakdown", {})
        if source_breakdown:
            print(f"\nSource Type Breakdown:")
            for source_type, count in sorted(
                source_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {source_type}: {count:,}")

        # Provider breakdown
        provider_breakdown = stats.get("provider_breakdown", {})
        if provider_breakdown:
            print(f"\nProvider Breakdown:")
            for provider, count in sorted(
                provider_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {provider}: {count:,}")

        print(f"{'='*60}")

    def print_stats_comparison(
        self, before_stats: Dict[str, Any], after_stats: Dict[str, Any]
    ) -> None:
        """Print before and after stats comparison"""
        print(f"\n{'='*60}")
        print("VESPA STATS COMPARISON - BEFORE vs AFTER BACKFILL")
        print(f"{'='*60}")

        if "error" in before_stats or "error" in after_stats:
            print("⚠️  Some stats could not be retrieved due to errors")
            if "error" in before_stats:
                print(f"Before stats error: {before_stats['error']}")
            if "error" in after_stats:
                print(f"After stats error: {after_stats['error']}")
            return

        before_total = before_stats.get("total_documents", 0)
        after_total = after_stats.get("total_documents", 0)
        difference = after_total - before_total

        print(f"User: {before_stats['user_email']}")
        print(f"Total Documents: {before_total:,} → {after_total:,} ({difference:+d})")

        if difference > 0:
            print(f"✅ Documents added: +{difference:,}")
        elif difference < 0:
            print(f"⚠️  Documents removed: {difference:,}")
        else:
            print(f"ℹ️  No change in document count")

        # Compare source type breakdowns
        before_source = before_stats.get("source_type_breakdown", {})
        after_source = after_stats.get("source_type_breakdown", {})

        if before_source or after_source:
            print(f"\nSource Type Changes:")
            all_source_types = set(before_source.keys()) | set(after_source.keys())

            for source_type in sorted(all_source_types):
                before_count = before_source.get(source_type, 0)
                after_count = after_source.get(source_type, 0)
                change = after_count - before_count

                if change != 0:
                    change_symbol = "+" if change > 0 else ""
                    print(
                        f"  {source_type}: {before_count:,} → {after_count:,} ({change_symbol}{change:,})"
                    )
                else:
                    print(f"  {source_type}: {before_count:,} (no change)")

        # Compare provider breakdowns
        before_provider = before_stats.get("provider_breakdown", {})
        after_provider = after_stats.get("provider_breakdown", {})

        if before_provider or after_provider:
            print(f"\nProvider Changes:")
            all_providers = set(before_provider.keys()) | set(after_provider.keys())

            for provider in sorted(all_providers):
                before_count = before_provider.get(provider, 0)
                after_count = after_provider.get(provider, 0)
                change = after_count - before_count

                if change != 0:
                    change_symbol = "+" if change > 0 else ""
                    print(
                        f"  {provider}: {before_count:,} → {after_count:,} ({change_symbol}{change:,})"
                    )
                else:
                    print(f"  {provider}: {before_count:,} (no change)")

                print(f"{'='*60}")

    async def _validate_data_ingestion(
        self,
        before_stats: Dict[str, Any],
        after_stats: Dict[str, Any],
        results: Dict[str, Any],
    ) -> None:
        """Validate that data was actually ingested into Vespa"""
        print(f"{'='*60}")
        print("📊 DATA INGESTION VALIDATION")
        print(f"{'='*60}")

        # Check if any data was actually published
        total_published = results.get("total_data_published", 0)
        if total_published == 0:
            print("❌ CRITICAL ISSUE: No data was published to Vespa!")
            print("\n🔍 INVESTIGATION REQUIRED:")
            print("1. Check if OAuth integrations are configured")
            print("2. Verify API clients can be created")
            print("3. Check office service logs for errors")
            print("4. Ensure user has valid OAuth tokens")
            print("\n💡 NEXT STEPS:")
            print("- Complete OAuth integration setup")
            print("- Check office service configuration")
            print("- Verify API keys are set correctly")
            print("- Review office service logs")
        else:
            print(f"✅ SUCCESS: {total_published} items published to Vespa")

        # Show detailed provider results
        job_details = results.get("job_details", [])
        if job_details:
            print(f"\n📋 PROVIDER RESULTS:")
            for job in job_details:
                provider = job.get("provider", "unknown")
                status = job.get("status", "unknown")
                duration = job.get("duration_seconds", 0)
                emails_processed = job.get("emails_processed", 0)
                emails_published = job.get("emails_published", 0)

                print(f"  {provider.upper()}: {status} ({duration:.1f}s)")
                print(f"    - Emails processed: {emails_processed}")
                print(f"    - Emails published: {emails_published}")

                # Show specific errors if any
                if job.get("error"):
                    print(f"    - ERROR: {job['error']}")

        # Show Vespa statistics comparison
        before_count = before_stats.get("total_documents", 0)
        after_count = after_stats.get("total_documents", 0)
        print(f"\n📈 VESPA STATISTICS:")
        print(f"  Before backfill: {before_count} documents")
        print(f"  After backfill:  {after_count} documents")
        print(f"  Net change:      {after_count - before_count} documents")

        if after_count == before_count and total_published > 0:
            print("\n⚠️  WARNING: Data published but Vespa count unchanged!")
            print("   This suggests the Vespa loader service may not be working")
            print("   Check Vespa loader service logs and configuration")

        print(f"{'='*60}")

    async def run_backfill_demo(self) -> Dict[str, Any]:
        """Run the complete real backfill demo"""
        logger.info("Starting Vespa real backfill demo...")

        start_time = datetime.now(timezone.utc)
        results: Dict[str, Any] = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "users_processed": 0,
            "total_data_published": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "job_details": [],
            "performance_metrics": {},
            "vespa_stats": {},
        }

        try:
            # Get initial Vespa stats before backfill
            logger.info("Collecting initial Vespa statistics...")
            before_stats = await self.get_user_vespa_stats()
            results["vespa_stats"]["before"] = before_stats
            self.print_vespa_stats(before_stats, "INITIAL VESPA STATISTICS")

            # Resolve email to user ID
            logger.info(f"Resolving email {self.user_email} to user ID...")
            user_id = await self._resolve_email_to_user_id(self.user_email)
            if not user_id:
                print(f"❌ Failed to resolve user ID for email: {self.user_email}")
                print("   Please ensure the user exists in the user service.")
                return results

            print(f"✅ Resolved user ID: {user_id} for email: {self.user_email}")

            # Store both email and user ID for use in different contexts
            original_email = self.user_email
            self.user_id = user_id

            # Check OAuth integration status before proceeding
            logger.info("Checking OAuth integration status...")
            integration_status = await self._check_integration_status(self.user_id)
            results["integration_status"] = integration_status

            # If office service is not running, fail fast
            if not integration_status.get("office_service_running", False):
                print(
                    "❌ Office service is not running. Please start the office service first."
                )
                return results

            # If user service is not running, fail fast
            if not integration_status.get("user_service_running", False):
                print(
                    "❌ User service is not running. Please start the user service first."
                )
                return results

            # If user doesn't exist, provide clear guidance
            if not integration_status.get("user_exists", False):
                print(
                    "❌ User not found. Please complete OAuth integration through the frontend first."
                )
                return results

            # Refresh OAuth tokens if needed (same logic as frontend)
            logger.info("Checking and refreshing OAuth tokens if needed...")
            token_refresh_result = await self._refresh_oauth_tokens_if_needed(
                self.user_id
            )
            results["token_refresh"] = token_refresh_result

            # If no active integrations after token refresh, fail fast
            if not token_refresh_result.get("success", False):
                print(
                    "❌ Failed to refresh OAuth tokens. Please check your integrations."
                )
                return results

            active_integrations = token_refresh_result.get("active_integrations", [])
            if not active_integrations:
                print("❌ No active OAuth integrations found after token refresh.")
                print(
                    "   Please complete OAuth integration through the frontend first."
                )
                return results

            print(
                f"✅ Found {len(active_integrations)} active OAuth integrations: {', '.join(active_integrations)}"
            )
            print("🚀 Proceeding with backfill using real data...")

            # Process the specified user
            logger.info(f"Starting backfill for user: {self.user_id}")

            try:
                # Process each provider for the user
                for provider in self.providers:
                    job_result = await self._run_user_provider_backfill(
                        self.user_id, provider
                    )

                    if job_result["status"] == "success":
                        results["successful_jobs"] += 1
                        results["total_data_published"] += job_result.get(
                            "total_published", 0
                        )
                    else:
                        results["failed_jobs"] += 1

                    results["job_details"].append(job_result)

                results["users_processed"] += 1

            except Exception as e:
                logger.error(f"Failed to process user {self.user_id}: {e}")
                results["failed_jobs"] += 1
                results["job_details"].append(
                    {
                        "user_id": self.user_id,
                        "provider": "unknown",
                        "status": "failed",
                        "error": str(e),
                    }
                )

            # Note: We're not using BackfillManager anymore, so no system-level metrics to collect
            # Individual job completion is already handled in _wait_for_job_completion

            # Get final Vespa stats after backfill
            logger.info("Collecting final Vespa statistics...")
            # Wait for async document processing to complete
            logger.info(
                "Waiting 5 seconds for async document processing to complete..."
            )
            await asyncio.sleep(5)
            after_stats = await self.get_user_vespa_stats()
            results["vespa_stats"]["after"] = after_stats
            self.print_vespa_stats(after_stats, "FINAL VESPA STATISTICS")

            # Print stats comparison
            self.print_stats_comparison(before_stats, after_stats)

            # Validate data ingestion success
            await self._validate_data_ingestion(before_stats, after_stats, results)

            results["status"] = "completed"
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()

            # Calculate performance metrics
            results["performance_metrics"] = self._calculate_performance_metrics(
                results
            )

        except Exception as e:
            logger.error(f"Backfill demo failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()

        return results

    async def _check_integration_status(self, user_id: str) -> Dict[str, Any]:
        """Check the status of OAuth integrations for the user"""
        print(f"{'='*60}")
        print("🔍 CHECKING OAUTH INTEGRATION STATUS")
        print(f"{'='*60}")

        try:
            import httpx

            # Check office service health first
            office_service_url = "http://localhost:8003"

            # First check if office service is running
            async with httpx.AsyncClient() as client:
                try:
                    health_response = await client.get(
                        f"{office_service_url}/health", timeout=10.0
                    )
                    if health_response.status_code == 200:
                        print("✅ Office service is running")
                    else:
                        print(
                            f"❌ Office service health check failed: {health_response.status_code}"
                        )
                        return {
                            "office_service_running": False,
                            "error": "Health check failed",
                        }
                except Exception as e:
                    print(f"❌ Cannot connect to office service: {e}")
                    print("   Make sure the office service is running on port 8003")
                    return {"office_service_running": False, "error": str(e)}

                # Check integration status through the user service
                user_service_url = "http://localhost:8001"
                try:
                    # Get user's integrations list
                    integrations_response = await client.get(
                        f"{user_service_url}/v1/users/{user_id}/integrations/",
                        headers={
                            "X-User-Id": user_id,
                            "X-API-Key": "test-FRONTEND_USER_KEY",
                        },
                        timeout=10.0,
                    )

                    if integrations_response.status_code == 200:
                        integrations_data = integrations_response.json()
                        print("✅ Integration status check completed")

                        # Show integration details
                        integrations = integrations_data.get("integrations", [])
                        if integrations:
                            print(f"\n📋 INTEGRATION STATUS:")
                            for integration in integrations:
                                provider = integration.get("provider", "unknown")
                                status = integration.get("status", "unknown")
                                connected = str(status).upper() == "ACTIVE"

                                status_str = str(status).upper()
                                if connected:
                                    print(f"  {provider.upper()}: ✅ {status_str}")
                                    if integration.get("last_sync_at"):
                                        print(
                                            f"    Last sync: {integration['last_sync_at']}"
                                        )
                                else:
                                    print(f"  {provider.upper()}: {status_str}")
                                    if integration.get("error_message"):
                                        print(
                                            f"    Error: {integration['error_message']}"
                                        )
                        else:
                            print("❌ No integrations found")
                            print("   User needs to complete OAuth setup")

                        return {
                            "office_service_running": True,
                            "user_service_running": True,
                            "user_exists": True,
                            "integrations": integrations,
                        }
                    else:
                        print(
                            f"❌ Integration status check failed: {integrations_response.status_code}"
                        )
                        if integrations_response.status_code == 404:
                            print("   User not found - may need to be created first")
                        return {
                            "office_service_running": True,
                            "user_service_running": True,
                            "user_exists": False,
                            "error": "Integration check failed",
                        }

                except Exception as e:
                    print(f"❌ Integration status check failed: {e}")
                    print(
                        "   This may indicate the user service is not running or accessible"
                    )
                    return {
                        "office_service_running": True,
                        "user_service_running": False,
                        "error": str(e),
                    }

        except Exception as e:
            print(f"❌ Failed to check integration status: {e}")
            return {"error": str(e)}

        print(f"{'='*60}")
        return {
            "office_service_running": True,
            "user_service_running": True,
            "user_exists": True,
        }

    async def _refresh_oauth_tokens_if_needed(self, user_id: str) -> Dict[str, Any]:
        """Refresh OAuth tokens if they are expired, following the same logic as the frontend"""
        print(f"{'='*60}")
        print("🔄 CHECKING AND REFRESHING OAUTH TOKENS")
        print(f"{'='*60}")

        try:
            import httpx

            user_service_url = "http://localhost:8001"
            office_service_url = "http://localhost:8003"

            async with httpx.AsyncClient() as client:
                # First, get the user's integrations to check their status
                try:
                    integrations_response = await client.get(
                        f"{user_service_url}/v1/users/{user_id}/integrations/",
                        headers={
                            "X-User-Id": user_id,
                            "X-API-Key": "test-FRONTEND_USER_KEY",
                        },
                        timeout=10.0,
                    )

                    if integrations_response.status_code == 200:
                        integrations = integrations_response.json()
                        active_integrations = []

                        for integration in integrations.get("integrations", []):
                            provider = integration.get("provider")
                            status = integration.get("status")
                            token_expires_at = integration.get("token_expires_at")

                            print(f"📋 Provider: {provider}, Status: {status}")

                            # Check if token is expired (same logic as frontend)
                            if token_expires_at:
                                try:
                                    expiration_date = datetime.fromisoformat(
                                        token_expires_at.replace("Z", "+00:00")
                                    )
                                    now = datetime.now(timezone.utc)
                                    is_expired = expiration_date <= now

                                    if is_expired:
                                        print(
                                            f"⚠️  {provider} token expired at {token_expires_at}"
                                        )
                                        print(
                                            f"🔄 Attempting to refresh {provider} tokens..."
                                        )

                                        # Refresh the expired token
                                        refresh_response = await client.put(
                                            f"{user_service_url}/v1/users/{user_id}/integrations/{provider}/refresh",
                                            headers={
                                                "X-User-Id": user_id,
                                                "X-API-Key": "test-FRONTEND_USER_KEY",
                                            },
                                            json={"force": True},
                                            timeout=30.0,
                                        )

                                        if refresh_response.status_code == 200:
                                            refresh_result = refresh_response.json()
                                            if refresh_result.get("success"):
                                                print(
                                                    f"✅ {provider} tokens refreshed successfully"
                                                )
                                                print(
                                                    f"   New expiration: {refresh_result.get('token_expires_at')}"
                                                )
                                                active_integrations.append(provider)
                                            else:
                                                print(
                                                    f"❌ {provider} token refresh failed: {refresh_result.get('error')}"
                                                )
                                        else:
                                            print(
                                                f"❌ {provider} token refresh HTTP error: {refresh_response.status_code}"
                                            )

                                    else:
                                        print(
                                            f"✅ {provider} token valid until {token_expires_at}"
                                        )
                                        active_integrations.append(provider)

                                except Exception as e:
                                    print(
                                        f"❌ Error checking {provider} token expiration: {e}"
                                    )
                            else:
                                print(f"⚠️  {provider} has no token expiration info")

                        return {
                            "success": True,
                            "active_integrations": active_integrations,
                            "total_integrations": len(
                                integrations.get("integrations", [])
                            ),
                            "message": f"Found {len(active_integrations)} active integrations",
                        }

                    else:
                        print(
                            f"❌ Failed to get integrations: HTTP {integrations_response.status_code}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {integrations_response.status_code}",
                            "message": "Could not retrieve user integrations",
                        }

                except Exception as e:
                    print(f"❌ Error checking integrations: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "message": "Failed to check user integrations",
                    }

        except Exception as e:
            print(f"❌ Error in token refresh process: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Token refresh process failed",
            }

    async def _run_user_provider_backfill(
        self, user_id: str, provider: str
    ) -> Dict[str, Any]:
        """Run backfill for a specific user and provider"""
        logger.info(f"Starting backfill for user {user_id} with provider {provider}")

        try:
            # Create backfill request
            request = BackfillRequest(
                provider=ProviderEnum(provider),
                batch_size=self.batch_size,
                rate_limit=(
                    max(1, int(1.0 / self.rate_limit)) if self.rate_limit > 0 else 100
                ),  # Ensure >= 1
                start_date=self.start_date,
                end_date=self.end_date,
                folders=self.folders,
                include_attachments=False,
                include_deleted=False,
                max_emails=self.max_emails_per_user,
                user_id=user_id,
            )

            # NOTE: office backfill internal API expects email in user_id query param
            job_id = await self._start_backfill_job_via_api(self.user_email, request)

            if not job_id:
                return {
                    "user_id": user_id,
                    "provider": provider,
                    "status": "failed",
                    "error": "Failed to start backfill job",
                }

            # Calculate timeout based on max emails (5 seconds per email)
            job_timeout_minutes = max(
                1, (self.max_emails_per_user * 5) // 60
            )  # At least 1 minute
            logger.info(
                f"Setting job timeout to {job_timeout_minutes} minutes for {self.max_emails_per_user} max emails"
            )

            # Wait for job completion
            job_result = await self._wait_for_job_completion(
                job_id, self.user_email, timeout_minutes=job_timeout_minutes
            )

            return {
                "user_id": user_id,
                "provider": provider,
                "status": "success",
                "job_id": job_id,
                "total_published": job_result.get("processed_emails", 0),
                "job_details": job_result,
            }

        except Exception as e:
            logger.error(
                f"Backfill failed for user {user_id} with provider {provider}: {e}"
            )
            return {
                "user_id": user_id,
                "provider": provider,
                "status": "failed",
                "error": str(e),
            }

    async def _start_backfill_job_via_api(
        self, user_id: str, request: BackfillRequest
    ) -> Optional[str]:
        """Start a backfill job via the office service API"""
        try:
            import httpx

            # Convert BackfillRequest to dict for API call
            request_data = {
                "provider": request.provider,
                "batch_size": request.batch_size,
                "rate_limit": request.rate_limit,
                "start_date": (
                    request.start_date.isoformat() if request.start_date else None
                ),
                "end_date": request.end_date.isoformat() if request.end_date else None,
                "folders": request.folders,
                "include_attachments": request.include_attachments,
                "include_deleted": request.include_deleted,
                "max_emails": self.max_emails_per_user,  # Pass max_emails to API
            }

            # Remove None values
            request_data = {k: v for k, v in request_data.items() if v is not None}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.office_service_url}/internal/backfill/start?user_id={user_id}",
                    json=request_data,
                    headers={
                        "X-API-Key": self.api_keys["backfill"],  # Use backfill API key
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Started backfill job: {result}")
                    return result.get("job_id")
                else:
                    logger.error(
                        f"Failed to start backfill job: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error starting backfill job via API: {e}")
            return None

    async def _wait_for_job_completion(
        self, job_id: str, user_id: str, timeout_minutes: int = 20
    ) -> Dict[str, Any]:
        """Wait for a backfill job to complete via the office service API"""
        logger.info(f"Waiting for backfill job {job_id} to complete...")

        start_time = datetime.now(timezone.utc)
        timeout = timedelta(minutes=timeout_minutes)

        try:
            import httpx

            while datetime.now(timezone.utc) - start_time < timeout:
                # Check job status via API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.office_service_url}/internal/backfill/status/{job_id}?user_id={user_id}",
                        headers={"X-API-Key": self.api_keys["backfill"]},
                    )

                    if response.status_code == 200:
                        job_status = response.json()
                        status = job_status.get("status")

                        logger.info(
                            f"Job {job_id} status: {status} - Progress: {job_status.get('progress', 0):.1f}%"
                        )

                        if status in ["completed", "failed", "cancelled"]:
                            return job_status

                        # Job still running, wait a bit
                        await asyncio.sleep(5)
                    else:
                        logger.warning(
                            f"Failed to get job status: {response.status_code}"
                        )
                        await asyncio.sleep(10)

            # Timeout reached
            logger.warning(f"Timeout waiting for job {job_id} to complete")
            return {
                "status": "timeout",
                "error": f"Job did not complete within {timeout_minutes} minutes",
            }

        except Exception as e:
            logger.error(f"Error waiting for job completion: {e}")
            return {"status": "error", "error": str(e)}

    async def _publish_user_data_to_pubsub(self, user_id: str, provider: str) -> int:
        """Publish user data to Pub/Sub for Vespa ingestion"""
        try:
            # Initialize email crawler
            email_crawler = EmailCrawler(
                user_id,
                provider,
                self.user_email,
                max_email_count=self.max_emails_per_user,
            )

            # Set rate limit
            email_crawler.rate_limit_delay = self.rate_limit

            total_published = 0

            # Crawl and publish emails
            async for email_batch in email_crawler.crawl_emails(
                batch_size=self.batch_size,
                start_date=self.start_date,
                end_date=self.end_date,
                folders=self.folders,
            ):
                try:
                    # Publish batch to Pub/Sub
                    message_ids = await self.pubsub_publisher.publish_batch_emails(
                        email_batch
                    )
                    total_published += len(message_ids)
                    logger.debug(
                        f"Published batch of {len(email_batch)} emails for user {user_id}"
                    )

                    # Rate limiting
                    if self.rate_limit > 0:
                        await asyncio.sleep(self.rate_limit)

                except Exception as e:
                    logger.error(
                        f"Failed to publish email batch for user {user_id}: {e}"
                    )
                    continue

            logger.info(
                f"Successfully published {total_published} emails to Pub/Sub for user {user_id}"
            )
            return total_published

        except Exception as e:
            logger.error(f"Failed to publish user data to Pub/Sub: {e}")
            return 0

    async def _wait_for_jobs_completion(self, timeout_minutes: int = 30) -> None:
        """Wait for all active jobs to complete"""
        logger.info(f"Waiting up to {timeout_minutes} minutes for jobs to complete...")

        # Since we're not using BackfillManager, we just wait for the timeout
        # The actual job completion is handled by the office service API
        # For small jobs, this timeout is usually much longer than needed
        await asyncio.sleep(timeout_minutes * 60)
        logger.info("Job completion timeout reached")

    def _calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from results"""
        duration = results.get("duration_seconds", 0)
        total_published = results.get("total_data_published", 0)

        metrics = {
            "throughput": {
                "items_per_second": (
                    round(total_published / duration, 2) if duration > 0 else 0
                ),
                "items_per_minute": (
                    round((total_published / duration) * 60, 2) if duration > 0 else 0
                ),
            },
            "success_rate": {
                "jobs": round(
                    (
                        results.get("successful_jobs", 0)
                        / max(results.get("users_processed", 1), 1)
                    )
                    * 100,
                    2,
                ),
                "data": round(
                    (total_published / max(results.get("total_data_published", 1), 1))
                    * 100,
                    2,
                ),
            },
            "efficiency": {
                "users_per_minute": (
                    round(results.get("users_processed", 0) / (duration / 60), 2)
                    if duration > 0
                    else 0
                ),
                "providers_per_user": len(self.providers),
            },
        }

        return metrics

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print formatted results"""
        print("\n" + "=" * 60)
        print("VESPA REAL BACKFILL DEMO RESULTS")
        print("=" * 60)

        print(f"Status: {results['status']}")
        print(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
        print(f"Users Processed: {results['users_processed']}")
        print(f"Successful Jobs: {results.get('successful_jobs', 0)}")
        print(f"Failed Jobs: {results.get('failed_jobs', 0)}")
        print(f"Total Data Published: {results.get('total_data_published', 0)} items")

        if results.get("total_emails_processed"):
            print(f"Total Emails Processed: {results['total_emails_processed']}")
            print(f"Total Emails Failed: {results.get('total_emails_failed', 0)}")

        if results["status"] == "failed" and "error" in results:
            print(f"Error: {results['error']}")

        # Print performance metrics
        perf_metrics = results.get("performance_metrics", {})
        if perf_metrics:
            print(f"\nPerformance Metrics:")
            print(
                f"  Throughput: {perf_metrics.get('throughput', {}).get('items_per_second', 0)} items/sec"
            )
            print(
                f"  Success Rate: {perf_metrics.get('success_rate', {}).get('jobs', 0)}%"
            )
            print(
                f"  Efficiency: {perf_metrics.get('efficiency', {}).get('users_per_minute', 0)} users/min"
            )

        # Print job details
        if results["job_details"]:
            print(f"\nJob Details:")
            for job in results["job_details"]:
                status_icon = "✅" if job["status"] == "success" else "❌"
                print(
                    f"  {status_icon} {job['user_id']} ({job['provider']}): {job.get('total_published', 0)} items in {job.get('duration_seconds', 0):.1f}s"
                )

        print("=" * 60)

    async def _resolve_email_to_user_id(self, email: str) -> Optional[str]:
        """Resolve email address to user ID using the same endpoint the frontend uses"""
        try:
            import httpx

            user_service_url = "http://localhost:8001"

            async with httpx.AsyncClient() as client:
                # Use the same endpoint the frontend uses: /v1/internal/users/exists
                response = await client.get(
                    f"{user_service_url}/v1/internal/users/exists",
                    params={"email": email},
                    headers={"X-API-Key": "test-FRONTEND_USER_KEY"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("exists", False):
                        user_id = data.get("user_id")
                        print(f"✅ Found user ID: {user_id} for email: {email}")
                        return user_id
                    else:
                        print(f"❌ No user found for email: {email}")
                        return None
                else:
                    print(f"❌ Failed to resolve email: HTTP {response.status_code}")
                    return None

        except Exception as e:
            print(f"❌ Error resolving email to user ID: {e}")
            return None


async def main() -> Optional[Dict[str, Any]]:
    """Main function for running the Vespa backfill demo"""
    parser = argparse.ArgumentParser(
        description="""Vespa Real Backfill Demo - Comprehensive data ingestion and indexing

This demo performs real backfill operations using the existing office service
infrastructure to crawl real emails, calendar events, and contacts, then
publishes them to Pub/Sub for the Vespa loader service to consume.

FEATURES:
  • Real email provider integration (Microsoft, Gmail, etc.)
  • Automated data crawling and backfill operations
  • Pub/Sub publishing for Vespa ingestion pipeline
  • Configurable batch processing and rate limiting
  • Date range filtering and folder selection
  • Job monitoring and status tracking
  • Performance metrics and efficiency analysis
  • Cleanup and job management capabilities

USAGE EXAMPLES:
  # Basic backfill with default settings
  python3 vespa_backfill.py user@example.com

  # Limit emails and set rate limiting
  python3 vespa_backfill.py user@example.com --max-emails 100 --rate-limit 1.0

  # Specific date range and folders
  python3 vespa_backfill.py user@example.com --start-date 2024-01-01 --end-date 2024-12-31 --folders INBOX SENT

  # Multiple providers with custom batch size
  python3 vespa_backfill.py user@example.com --providers microsoft gmail --batch-size 20

  # Cleanup first, then run fresh demo
  python3 vespa_backfill.py user@example.com --cleanup-first

  # Custom Pub/Sub configuration
  python3 vespa_backfill.py user@example.com --project-id my-project --emulator-host localhost:8085

BACKFILL PROCESS:
  1. Connect to email provider APIs (Microsoft Graph, Gmail, etc.)
  2. Crawl emails, calendar events, and contacts
  3. Process and normalize data
  4. Publish to Pub/Sub topics (email-backfill, calendar-updates, contact-updates)
  5. Vespa loader service consumes and indexes the data
  6. Monitor job progress and collect performance metrics

CONFIGURATION OPTIONS:
  • Email providers: Microsoft, Gmail, Outlook, etc.
  • Batch processing: Control batch sizes and rate limits
  • Date filtering: Specify start/end dates for historical data
  • Folder selection: Choose specific email folders to process
  • Pub/Sub settings: Project ID and emulator configuration
  • Cleanup options: Stop running jobs and clear topics

PERFORMANCE FEATURES:
  • Configurable rate limiting to respect API quotas
  • Batch processing for efficient data handling
  • Progress monitoring and job status tracking
  • Performance metrics collection and analysis
  • Resource cleanup and job management

REQUIREMENTS:
  • Office service running and accessible
  • User service for authentication and permissions
  • Pub/Sub emulator or production instance
  • Valid API keys for email providers
  • Vespa loader service for data ingestion
  • Python dependencies: httpx, asyncio, aiohttp""",
        epilog="Example: python3 vespa_backfill.py trybriefly@outlook.com --max-emails 10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "email",
        help="Email address of the user to backfill (e.g., trybriefly@outlook.com)",
    )
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--providers", nargs="+", help="Email providers to backfill")
    parser.add_argument("--batch-size", type=int, help="Batch size for processing")
    parser.add_argument(
        "--rate-limit", type=float, help="Rate limit delay between batches (seconds)"
    )
    parser.add_argument("--max-emails", type=int, help="Maximum emails per user")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--folders", nargs="+", help="Email folders to backfill")
    parser.add_argument("--project-id", help="Pub/Sub project ID")
    parser.add_argument("--emulator-host", help="Pub/Sub emulator host")
    parser.add_argument(
        "--vespa-endpoint", help="Vespa endpoint for statistics collection"
    )
    parser.add_argument(
        "--cleanup-first",
        action="store_true",
        help="Stop running jobs and clear Pub/Sub first",
    )

    args = parser.parse_args()

    # Build configuration
    config = {}
    if args.config:
        with open(args.config, "r") as f:
            config = json.load(f)

    # Override with command line arguments
    if args.email:
        config["user_email"] = args.email
    if args.providers:
        config["providers"] = args.providers
    if args.batch_size:
        config["batch_size"] = args.batch_size
    if args.rate_limit:
        config["rate_limit"] = args.rate_limit
    if args.max_emails:
        config["max_emails_per_user"] = args.max_emails
    if args.start_date:
        config["start_date"] = datetime.strptime(args.start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    if args.end_date:
        config["end_date"] = datetime.strptime(args.end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    if args.folders:
        config["folders"] = args.folders
    if args.project_id:
        config["project_id"] = args.project_id
    if args.emulator_host:
        config["emulator_host"] = args.emulator_host
    if args.vespa_endpoint:
        config["vespa_endpoint"] = args.vespa_endpoint

    try:
        async with VespaBackfillDemo(config) as demo:
            # Cleanup first if requested
            if args.cleanup_first:
                await demo.stop_all_backfill_jobs()
                await demo.clear_pubsub_topics()
                logger.info("Cleanup completed. Starting fresh demo...")

            # Ensure Pub/Sub topics exist
            await demo.ensure_pubsub_topics()

            # Run the demo
            results = await demo.run_backfill_demo()

            # Print summary
            print("\n" + "=" * 60)
            print("VESPA BACKFILL DEMO RESULTS SUMMARY")
            print("=" * 60)
            print(f"Status: {results['status']}")

            if results["status"] == "completed":
                print(f"Users Processed: {results.get('users_processed', 0)}")
                print(f"Successful Jobs: {results.get('successful_jobs', 0)}")
                print(f"Failed Jobs: {results.get('failed_jobs', 0)}")
                print(f"Total Data Published: {results.get('total_data_published', 0)}")

                # Show job details
                if results.get("job_details"):
                    print("\nJob Details:")
                    for job in results["job_details"]:
                        print(
                            f"  {job['user_id']} ({job['provider']}): {job['status']}"
                        )
                        if job.get("total_published"):
                            print(f"    Published: {job['total_published']} items")

            print("=" * 60)

            return results

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
