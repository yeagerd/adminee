#!/usr/bin/env python3
"""
Vespa Backfill Demo - Real Office Data Integration

This demo performs real backfill operations using the existing office service
infrastructure to crawl real emails, calendar events, and contacts, then
publishes them to Pub/Sub for the Vespa loader service to consume.
"""

import asyncio
import logging
import argparse
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import time

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.common.logging_config import get_logger
from services.demos.settings_demos import get_demo_settings
from services.demos.backfill_manager import BackfillManager
from services.office.api.backfill import BackfillRequest
from services.office.core.email_crawler import EmailCrawler
from services.office.core.pubsub_publisher import PubSubPublisher

logger = get_logger(__name__)

class VespaBackfillDemo:
    """Real backfill demo using office service infrastructure"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.settings = get_demo_settings()
        
        # Demo configuration with sensible limits for testing
        self.user_email = config.get("user_email", "trybriefly@outlook.com")
        self.providers = config.get("providers", ["microsoft"])  # Start with just Microsoft
        self.batch_size = config.get("batch_size", 10)  # Small batch size for testing
        self.rate_limit = config.get("rate_limit", 2.0)  # Slower rate for testing
        self.max_emails_per_user = config.get("max_emails_per_user", self.settings.demo_max_emails)  # Use centralized setting
        self.start_date = config.get("start_date")
        self.end_date = config.get("end_date")
        self.folders = config.get("folders", ["INBOX"])  # Just INBOX for testing
        
        # Service endpoints from common settings
        self.office_service_url = self.settings.office_service_url
        self.user_service_url = self.settings.user_service_url
        
        # Initialize components
        self.backfill_manager = BackfillManager()
        self.pubsub_publisher = PubSubPublisher(
            project_id=config.get("project_id", "briefly-dev"),
            emulator_host=config.get("emulator_host", "localhost:8085")
        )
        
        # API keys from common settings
        self.api_keys = {
            "office": getattr(self.settings, "api_frontend_office_key", "test-FRONTEND_OFFICE_KEY"),
            "user": getattr(self.settings, "api_frontend_user_key", "test-FRONTEND_USER_KEY"),
            "backfill": getattr(self.settings, "api_backfill_office_key", "test-BACKFILL-OFFICE-KEY"),
        }
    
    async def clear_pubsub_topics(self):
        """Clear Pub/Sub topics to stop flooding"""
        logger.info("Clearing Pub/Sub topics to stop flooding...")
        try:
            # This is a simple approach - in production you'd want more sophisticated cleanup
            logger.warning("Pub/Sub topic clearing not implemented - consider restarting the emulator")
            logger.info("To stop flooding, restart the Pub/Sub emulator or clear topics manually")
        except Exception as e:
            logger.error(f"Failed to clear Pub/Sub topics: {e}")
    
    async def ensure_pubsub_topics(self):
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
                        logger.error(f"❌ Failed to create topic {topic}: HTTP {response.status_code}")
                        if response.text:
                            logger.error(f"   Response: {response.text}")
                except Exception as e:
                    logger.error(f"❌ Failed to create topic {topic}: {e}")
            
            logger.info("Pub/Sub topics check completed")
            
        except Exception as e:
            logger.error(f"❌ Pub/Sub topics check failed: {e}")
            logger.info("Demo will continue but Pub/Sub publishing may fail")
    
    async def stop_all_backfill_jobs(self):
        """Stop all running backfill jobs"""
        logger.info("Stopping all running backfill jobs...")
        try:
            import httpx
            
            # Get list of running jobs using internal endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.office_service_url}/internal/backfill/status?user_id={self.user_email}",
                    headers={"X-API-Key": self.api_keys["backfill"]}
                )
                
                if response.status_code == 200:
                    jobs = response.json()
                    for job in jobs:
                        if job.get("status") == "running":
                            job_id = job.get("job_id")
                            logger.info(f"Cancelling running job: {job_id}")
                            
                            # Cancel the job using internal endpoint
                            cancel_response = await client.delete(
                                f"{self.office_service_url}/internal/backfill/{job_id}?user_id={self.user_email}",
                                headers={"X-API-Key": self.api_keys["backfill"]}
                            )
                            
                            if cancel_response.status_code == 200:
                                logger.info(f"Successfully cancelled job: {job_id}")
                            else:
                                logger.warning(f"Failed to cancel job {job_id}: {cancel_response.status_code}")
                else:
                    logger.warning(f"Failed to get job status: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error stopping backfill jobs: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup resources if needed
        pass
        
    async def run_backfill_demo(self) -> Dict[str, Any]:
        """Run the complete real backfill demo"""
        logger.info("Starting Vespa real backfill demo...")
        
        start_time = datetime.now(timezone.utc)
        results = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "users_processed": 0,
            "total_data_published": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "job_details": [],
            "performance_metrics": {}
        }
        
        try:
            # Process the specified user
            logger.info(f"Starting backfill for user: {self.user_email}")
            
            try:
                # Process each provider for the user
                for provider in self.providers:
                    job_result = await self._run_user_provider_backfill(self.user_email, provider)
                    
                    if job_result["status"] == "success":
                        results["successful_jobs"] += 1
                        results["total_data_published"] += job_result.get("total_published", 0)
                    else:
                        results["failed_jobs"] += 1
                    
                    results["job_details"].append(job_result)
                
                results["users_processed"] += 1
                
            except Exception as e:
                logger.error(f"Failed to process user {self.user_email}: {e}")
                results["failed_jobs"] += 1
                results["job_details"].append({
                    "user_id": self.user_email,
                    "provider": "unknown",
                    "status": "failed",
                    "error": str(e)
                })
            
            # Wait for all jobs to complete
            await self._wait_for_jobs_completion(timeout_minutes=30)
            
            # Collect final results
            final_results = await self._collect_final_results()
            results.update(final_results)
            
            results["status"] = "completed"
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Calculate performance metrics
            results["performance_metrics"] = self._calculate_performance_metrics(results)
            
        except Exception as e:
            logger.error(f"Backfill demo failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return results
    
    async def _run_user_provider_backfill(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Run backfill for a specific user and provider"""
        logger.info(f"Starting backfill for user {user_id} with provider {provider}")
        
        try:
            # Create backfill request
            request = BackfillRequest(
                provider=provider,
                batch_size=self.batch_size,
                rate_limit=max(1, int(1.0 / self.rate_limit)) if self.rate_limit > 0 else 100,  # Ensure >= 1
                start_date=self.start_date,
                end_date=self.end_date,
                folders=self.folders
            )
            
            # Start backfill job using the office service API
            job_id = await self._start_backfill_job_via_api(user_id, request)
            
            if not job_id:
                return {
                    "user_id": user_id,
                    "provider": provider,
                    "status": "failed",
                    "error": "Failed to start backfill job"
                }
            
            # Wait for job completion
            job_result = await self._wait_for_job_completion(job_id, user_id)
            
            return {
                "user_id": user_id,
                "provider": provider,
                "status": "success",
                "job_id": job_id,
                "total_published": job_result.get("processed_emails", 0),
                "job_details": job_result
            }
            
        except Exception as e:
            logger.error(f"Backfill failed for user {user_id} with provider {provider}: {e}")
            return {
                "user_id": user_id,
                "provider": provider,
                "status": "failed",
                "error": str(e)
            }
    
    async def _start_backfill_job_via_api(self, user_id: str, request: BackfillRequest) -> Optional[str]:
        """Start a backfill job via the office service API"""
        try:
            import httpx
            
            # Convert BackfillRequest to dict for API call
            request_data = {
                "provider": request.provider,
                "batch_size": request.batch_size,
                "rate_limit": request.rate_limit,
                "start_date": request.start_date.isoformat() if request.start_date else None,
                "end_date": request.end_date.isoformat() if request.end_date else None,
                "folders": request.folders,
                "include_attachments": request.include_attachments,
                "include_deleted": request.include_deleted,
                "max_emails": self.max_emails_per_user  # Pass max_emails to API
            }
            
            # Remove None values
            request_data = {k: v for k, v in request_data.items() if v is not None}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.office_service_url}/internal/backfill/start?user_id={user_id}",
                    json=request_data,
                    headers={
                        "X-API-Key": self.api_keys["backfill"],  # Use backfill API key
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Started backfill job: {result}")
                    return result.get("job_id")
                else:
                    logger.error(f"Failed to start backfill job: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error starting backfill job via API: {e}")
            return None
    
    async def _wait_for_job_completion(self, job_id: str, user_id: str, timeout_minutes: int = 20) -> Dict[str, Any]:
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
                        headers={"X-API-Key": self.api_keys["backfill"]}
                    )
                    
                    if response.status_code == 200:
                        job_status = response.json()
                        status = job_status.get("status")
                        
                        logger.info(f"Job {job_id} status: {status} - Progress: {job_status.get('progress', 0):.1f}%")
                        
                        if status in ["completed", "failed", "cancelled"]:
                            return job_status
                        
                        # Job still running, wait a bit
                        await asyncio.sleep(5)
                    else:
                        logger.warning(f"Failed to get job status: {response.status_code}")
                        await asyncio.sleep(10)
            
            # Timeout reached
            logger.warning(f"Timeout waiting for job {job_id} to complete")
            return {
                "status": "timeout",
                "error": f"Job did not complete within {timeout_minutes} minutes"
            }
            
        except Exception as e:
            logger.error(f"Error waiting for job completion: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _publish_user_data_to_pubsub(self, user_id: str, provider: str) -> int:
        """Publish user data to Pub/Sub for Vespa ingestion"""
        try:
            # Initialize email crawler
            email_crawler = EmailCrawler(user_id, provider, max_email_count=self.max_emails_per_user)
            
            # Set rate limit
            email_crawler.rate_limit_delay = self.rate_limit
            
            total_published = 0
            
            # Crawl and publish emails
            async for email_batch in email_crawler.crawl_emails(
                batch_size=self.batch_size,
                start_date=self.start_date,
                end_date=self.end_date,
                folders=self.folders
            ):
                try:
                    # Publish batch to Pub/Sub
                    message_ids = await self.pubsub_publisher.publish_batch_emails(email_batch)
                    total_published += len(message_ids)
                    logger.debug(f"Published batch of {len(email_batch)} emails for user {user_id}")
                    
                    # Rate limiting
                    if self.rate_limit > 0:
                        await asyncio.sleep(self.rate_limit)
                        
                except Exception as e:
                    logger.error(f"Failed to publish email batch for user {user_id}: {e}")
                    continue
            
            logger.info(f"Successfully published {total_published} emails to Pub/Sub for user {user_id}")
            return total_published
            
        except Exception as e:
            logger.error(f"Failed to publish user data to Pub/Sub: {e}")
            return 0
    
    async def _wait_for_jobs_completion(self, timeout_minutes: int = 30):
        """Wait for all active jobs to complete"""
        timeout_seconds = timeout_minutes * 60
        start_time = datetime.now(timezone.utc)
        
        while self.backfill_manager.active_jobs and \
              (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_seconds:
            
            active_count = len(self.backfill_manager.active_jobs)
            logger.info(f"Waiting for {active_count} active jobs to complete...")
            
            # Check job statuses
            for job_id, job in self.backfill_manager.active_jobs.items():
                if job.status in ["completed", "failed", "cancelled"]:
                    logger.info(f"Job {job_id} completed with status: {job.status}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        if self.backfill_manager.active_jobs:
            logger.warning(f"Timeout reached, {len(self.backfill_manager.active_jobs)} jobs still active")
    
    async def _collect_final_results(self) -> Dict[str, Any]:
        """Collect final results from all jobs"""
        all_jobs = list(self.backfill_manager.active_jobs.values()) + self.backfill_manager.job_history
        
        successful_jobs = [j for j in all_jobs if j.status == "completed"]
        failed_jobs = [j for j in all_jobs if j.status == "failed"]
        
        total_emails_processed = sum(j.processed_emails for j in all_jobs)
        total_emails_failed = sum(j.failed_emails for j in all_jobs)
        
        return {
            "successful_jobs": len(successful_jobs),
            "failed_jobs": len(failed_jobs),
            "total_emails_processed": total_emails_processed,
            "total_emails_failed": total_emails_failed,
            "system_summary": self.backfill_manager.get_system_summary()
        }
    
    def _calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from results"""
        duration = results.get("duration_seconds", 0)
        total_published = results.get("total_data_published", 0)
        
        metrics = {
            "throughput": {
                "items_per_second": round(total_published / duration, 2) if duration > 0 else 0,
                "items_per_minute": round((total_published / duration) * 60, 2) if duration > 0 else 0
            },
            "success_rate": {
                "jobs": round((results.get("successful_jobs", 0) / max(results.get("users_processed", 1), 1)) * 100, 2),
                "data": round((total_published / max(results.get("total_data_published", 1), 1)) * 100, 2)
            },
            "efficiency": {
                "users_per_minute": round(results.get("users_processed", 0) / (duration / 60), 2) if duration > 0 else 0,
                "providers_per_user": len(self.providers)
            }
        }
        
        return metrics
    
    def print_results(self, results: Dict[str, Any]):
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
        
        if results['status'] == 'failed' and 'error' in results:
            print(f"Error: {results['error']}")
        
        # Print performance metrics
        perf_metrics = results.get("performance_metrics", {})
        if perf_metrics:
            print(f"\nPerformance Metrics:")
            print(f"  Throughput: {perf_metrics.get('throughput', {}).get('items_per_second', 0)} items/sec")
            print(f"  Success Rate: {perf_metrics.get('success_rate', {}).get('jobs', 0)}%")
            print(f"  Efficiency: {perf_metrics.get('efficiency', {}).get('users_per_minute', 0)} users/min")
        
        # Print job details
        if results['job_details']:
            print(f"\nJob Details:")
            for job in results['job_details']:
                status_icon = "✅" if job['status'] == 'success' else "❌"
                print(f"  {status_icon} {job['user_id']} ({job['provider']}): {job.get('total_published', 0)} items in {job.get('duration_seconds', 0):.1f}s")
        
        print("=" * 60)

async def main():
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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("email", help="Email address of the user to backfill (e.g., trybriefly@outlook.com)")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--providers", nargs="+", help="Email providers to backfill")
    parser.add_argument("--batch-size", type=int, help="Batch size for processing")
    parser.add_argument("--rate-limit", type=float, help="Rate limit delay between batches (seconds)")
    parser.add_argument("--max-emails", type=int, help="Maximum emails per user")
    parser.add_argument("--start-date", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--folders", nargs="+", help="Email folders to backfill")
    parser.add_argument("--project-id", help="Pub/Sub project ID")
    parser.add_argument("--emulator-host", help="Pub/Sub emulator host")
    parser.add_argument("--cleanup-first", action="store_true", help="Stop running jobs and clear Pub/Sub first")
    
    args = parser.parse_args()
    
    # Build configuration
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
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
        config["start_date"] = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        config["end_date"] = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.folders:
        config["folders"] = args.folders
    if args.project_id:
        config["project_id"] = args.project_id
    if args.emulator_host:
        config["emulator_host"] = args.emulator_host
    
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
            print("\n" + "="*60)
            print("VESPA BACKFILL DEMO RESULTS SUMMARY")
            print("="*60)
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
                        print(f"  {job['user_id']} ({job['provider']}): {job['status']}")
                        if job.get("total_published"):
                            print(f"    Published: {job['total_published']} items")
            
            print("="*60)
            
            return results
            
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
