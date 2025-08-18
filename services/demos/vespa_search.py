#!/usr/bin/env python3
"""
Vespa Search Demo - Comprehensive search capabilities demonstration

This demo focuses on testing and showcasing Vespa's search capabilities
without the complexity of data ingestion and backfill functionality.

FEATURES:
  • Interactive search mode with real-time querying
  • Comprehensive search demo with multiple test scenarios
  • User statistics collection and display
  • Multi-user database statistics and aggregations
  • Performance benchmarking and metrics
  • Support for different ranking profiles (hybrid, BM25, semantic)

USAGE EXAMPLES:
  # Interactive mode with user stats (default)
  python3 vespa_search.py user@example.com

  # Show statistics for all users
  python3 vespa_search.py user@example.com --stats

  # Only show statistics (no interactive mode)
  python3 vespa_search.py user@example.com --stats-only

  # Run comprehensive search demo
  python3 vespa_search.py user@example.com --demo

  # Execute single query non-interactively
  python3 vespa_search.py user@example.com --query "meeting notes"

  # Custom Vespa endpoint
  python3 vespa_search.py user@example.com --vespa-endpoint http://localhost:8080

  # Dump all content stored in Vespa for the user
  python3 vespa_search.py user@example.com --dump

STATISTICS PROVIDED:
  • Current user document count and breakdowns
  • Source type distribution (emails, calendar, contacts, etc.)
  • Provider breakdown (Outlook, Gmail, etc.)
  • All users aggregate statistics
  • Query performance metrics and response times

SEARCH CAPABILITIES:
  • Full-text search across titles, content, and search text
  • User-scoped data isolation
  • Hybrid ranking (BM25 + vector similarity)
  • Semantic search with embeddings
  • Source type and provider filtering
  • Real-time search with performance metrics

REQUIREMENTS:
  • Vespa instance running and accessible
  • User data indexed in Vespa database
  • Python dependencies: aiohttp, asyncio
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.chat.agents.llm_tools import (
    SemanticSearchTool,
    UserDataSearchTool,
    VespaSearchTool,
)
from services.vespa_query.search_engine import SearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VespaSearchDemo:
    """Comprehensive search demo using Vespa capabilities"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vespa_endpoint = config["vespa_endpoint"]
        self.user_email = config.get("user_email", "trybriefly@outlook.com")
        self.user_id = None  # Will be resolved from email

        # Initialize search engine for stats
        self.search_engine = SearchEngine(self.vespa_endpoint)
        
        # Search tools will be initialized after user_id is resolved
        self.vespa_search = None
        self.user_data_search = None
        self.semantic_search = None

    def _initialize_search_tools(self):
        """Initialize search tools after user_id is resolved"""
        if self.user_id:
            self.vespa_search = VespaSearchTool(self.vespa_endpoint, self.user_id)
            self.user_data_search = UserDataSearchTool(self.vespa_endpoint, self.user_id)
            self.semantic_search = SemanticSearchTool(self.vespa_endpoint, self.user_id)

        # Comprehensive search test scenarios
        self.search_scenarios = [
            {
                "name": "Basic Search Functionality",
                "queries": ["test query", "simple search", "basic functionality"],
                "expected": "Basic search responses",
            },
        ]

    async def resolve_email_to_user_id(self) -> Optional[str]:
        """Resolve email address to user ID using the same endpoint the frontend uses"""
        try:
            import httpx

            user_service_url = "http://localhost:8001"

            async with httpx.AsyncClient() as client:
                # Use the same endpoint the frontend uses: /v1/internal/users/exists
                response = await client.get(
                    f"{user_service_url}/v1/internal/users/exists",
                    params={"email": self.user_email},
                    headers={"X-API-Key": "test-FRONTEND_USER_KEY"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("exists", False):
                        user_id = data.get("user_id")
                        print(f"✅ Found user ID: {user_id} for email: {self.user_email}")
                        return user_id
                    else:
                        print(f"❌ No user found for email: {self.user_email}")
                        return None
                else:
                    print(f"❌ Failed to resolve email: HTTP {response.status_code}")
                    return None

        except Exception as e:
            print(f"❌ Error resolving email to user ID: {e}")
            return None

    async def initialize(self) -> bool:
        """Initialize the search demo by resolving user ID"""
        print(f"🔍 Resolving email {self.user_email} to user ID...")
        self.user_id = await self.resolve_email_to_user_id()
        
        if self.user_id:
            print(f"✅ Resolved user ID: {self.user_id} for email: {self.user_email}")
            # Initialize search tools now that we have the user ID
            self._initialize_search_tools()
            return True
        else:
            print(f"❌ Failed to resolve email {self.user_email} to user ID")
            return False

    async def cleanup(self) -> None:
        """Clean up resources and close aiohttp sessions"""
        try:
            logger.info("Cleaning up resources...")

            # Close search engine sessions - handle all nested instances
            if hasattr(self.vespa_search, "search_engine"):
                await self.vespa_search.search_engine.close()

            # UserDataSearchTool has a VespaSearchTool which has a SearchEngine
            if hasattr(self.user_data_search, "vespa_search") and hasattr(
                self.user_data_search.vespa_search, "search_engine"
            ):
                await self.user_data_search.vespa_search.search_engine.close()

            if hasattr(self.semantic_search, "search_engine"):
                await self.semantic_search.search_engine.close()

            # Close our stats search engine
            if hasattr(self, "search_engine"):
                await self.search_engine.close()

            logger.info("Resource cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self) -> "VespaSearchDemo":
        """Async context manager entry"""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit with cleanup"""
        await self.cleanup()

    async def run_search_demo(self) -> Dict[str, Any]:
        """Run the comprehensive search demo"""
        logger.info("Starting Vespa search capabilities demo...")

        demo_start = time.time()
        demo_results: Dict[str, Any] = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "search_scenarios": [],
            "advanced_scenarios": [],
            "performance_metrics": {},
            "search_quality": {},
            "end_time": None,
            "status": "running",
        }

        try:
            # Test basic search functionality
            logger.info("Testing basic search functionality...")
            for scenario in self.search_scenarios:
                scenario_result = await self._test_search_scenario(scenario)
                demo_results["search_scenarios"].append(scenario_result)

            # Test advanced search features
            logger.info("Testing advanced search features...")
            for scenario in self.advanced_scenarios:
                scenario_result = await self._test_advanced_scenario(scenario)
                demo_results["advanced_scenarios"].append(scenario_result)

            # Calculate performance metrics
            demo_results["performance_metrics"] = self._calculate_performance_metrics(
                demo_results
            )

            # Assess search quality
            demo_results["search_quality"] = self._assess_search_quality(demo_results)

            demo_results["end_time"] = datetime.now(timezone.utc).isoformat()
            demo_results["status"] = "completed"

            demo_duration = time.time() - demo_start
            logger.info(
                f"Search demo completed successfully in {demo_duration:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"Search demo failed: {e}")
            demo_results["status"] = "failed"
            demo_results["error"] = str(e)
            demo_results["end_time"] = datetime.now(timezone.utc).isoformat()

        return demo_results

    async def _test_search_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a basic search scenario"""
        scenario_result = {
            "name": scenario["name"],
            "queries": [],
            "total_queries": len(scenario["queries"]),
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "expected": scenario["expected"],
        }

        for query in scenario["queries"]:
            try:
                start_time = time.time()

                # Test with user data search
                results = await self.user_data_search.search_all_data(
                    query, max_results=10
                )

                response_time = (time.time() - start_time) * 1000

                query_result = {
                    "query": query,
                    "status": results.get("status", "unknown"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": results.get("total_found", 0),
                    "success": results.get("status") == "success",
                }

                scenario_result["queries"].append(query_result)

                if query_result["success"]:
                    scenario_result["successful_queries"] += 1
                else:
                    scenario_result["failed_queries"] += 1

            except Exception as e:
                logger.error(f"Query '{query}' failed: {e}")
                scenario_result["queries"].append(
                    {
                        "query": query,
                        "status": "error",
                        "error": str(e),
                        "success": False,
                    }
                )
                scenario_result["failed_queries"] += 1

        # Calculate average response time
        successful_times = [
            q["response_time_ms"]
            for q in scenario_result["queries"]
            if q.get("response_time_ms")
        ]
        if successful_times:
            scenario_result["average_response_time"] = sum(successful_times) / len(
                successful_times
            )

        return scenario_result

    async def _test_advanced_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test an advanced search scenario with specific ranking profiles"""
        scenario_result = {
            "name": scenario["name"],
            "ranking_profile": scenario["ranking_profile"],
            "queries": [],
            "total_queries": len(scenario["queries"]),
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
        }

        for query in scenario["queries"]:
            try:
                start_time = time.time()

                # Test with specific ranking profile
                results = await self.vespa_search.search(
                    query=query,
                    max_results=10,
                    ranking_profile=scenario["ranking_profile"],
                )

                response_time = (time.time() - start_time) * 1000

                query_result = {
                    "query": query,
                    "status": results.get("status", "unknown"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": results.get("total_found", 0),
                    "ranking_profile": scenario["ranking_profile"],
                    "success": results.get("status") == "success",
                }

                scenario_result["queries"].append(query_result)

                if query_result["success"]:
                    scenario_result["successful_queries"] += 1
                else:
                    scenario_result["failed_queries"] += 1

            except Exception as e:
                logger.error(f"Advanced query '{query}' failed: {e}")
                scenario_result["queries"].append(
                    {
                        "query": query,
                        "status": "error",
                        "error": str(e),
                        "success": False,
                    }
                )
                scenario_result["failed_queries"] += 1

        # Calculate average response time
        successful_times = [
            q["response_time_ms"]
            for q in scenario_result["queries"]
            if q.get("response_time_ms")
        ]
        if successful_times:
            scenario_result["average_response_time"] = sum(successful_times) / len(
                successful_times
            )

        return scenario_result

    def _calculate_performance_metrics(
        self, demo_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate performance metrics across all scenarios"""
        all_queries = []

        # Collect queries from basic scenarios
        for scenario in demo_results.get("search_scenarios", []):
            all_queries.extend(scenario.get("queries", []))

        # Collect queries from advanced scenarios
        for scenario in demo_results.get("advanced_scenarios", []):
            all_queries.extend(scenario.get("queries", []))

        if not all_queries:
            return {
                "total_queries": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0,
            }

        total_queries = len(all_queries)
        successful_queries = sum(1 for q in all_queries if q.get("success", False))
        success_rate = (
            (successful_queries / total_queries) * 100 if total_queries > 0 else 0
        )

        # Calculate average response time
        response_times = [
            q.get("response_time_ms", 0)
            for q in all_queries
            if q.get("response_time_ms")
        ]
        average_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": round(success_rate, 2),
            "average_response_time_ms": round(average_response_time, 2),
            "total_scenarios": len(demo_results.get("search_scenarios", []))
            + len(demo_results.get("advanced_scenarios", [])),
        }

    def _assess_search_quality(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of search results"""
        quality_metrics: Dict[str, Any] = {
            "overall_success_rate": 0.0,
            "scenario_success_rates": {},
            "response_time_distribution": {},
            "ranking_profile_performance": {},
        }

        # Calculate overall success rate
        performance = demo_results.get("performance_metrics", {})
        quality_metrics["overall_success_rate"] = performance.get("success_rate", 0.0)

        # Calculate scenario success rates
        for scenario in demo_results.get("search_scenarios", []):
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["scenario_success_rates"][scenario["name"]] = round(
                    (successful / total) * 100, 2
                )

        for scenario in demo_results.get("advanced_scenarios", []):
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["scenario_success_rates"][scenario["name"]] = round(
                    (successful / total) * 100, 2
                )

        # Analyze response time distribution
        all_times = []
        for scenario in demo_results.get("search_scenarios", []):
            all_times.extend(
                [
                    q.get("response_time_ms", 0)
                    for q in scenario.get("queries", [])
                    if q.get("response_time_ms")
                ]
            )
        for scenario in demo_results.get("advanced_scenarios", []):
            all_times.extend(
                [
                    q.get("response_time_ms", 0)
                    for q in scenario.get("queries", [])
                    if q.get("response_time_ms")
                ]
            )

        if all_times:
            quality_metrics["response_time_distribution"] = {
                "fast": len([t for t in all_times if t < 10]),  # < 10ms
                "medium": len([t for t in all_times if 10 <= t < 50]),  # 10-50ms
                "slow": len([t for t in all_times if t >= 50]),  # >= 50ms
            }

        # Analyze ranking profile performance
        for scenario in demo_results.get("advanced_scenarios", []):
            profile = scenario.get("ranking_profile", "unknown")
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["ranking_profile_performance"][profile] = round(
                    (successful / total) * 100, 2
                )

        return quality_metrics

    async def run_single_query(self, query: str) -> Dict[str, Any]:
        """Run a single query and return results"""
        try:
            start_time = time.time()

            # Use user data search for comprehensive results
            search_results = await self.user_data_search.search_all_data(
                query, max_results=20
            )

            response_time = (time.time() - start_time) * 1000

            # Extract results from the grouped structure
            if search_results.get("status") == "success":
                # Flatten grouped results into a single list for display
                all_results = []
                grouped_results = search_results.get("grouped_results", {})
                for result_type, results in grouped_results.items():
                    all_results.extend(results)

                # Sort by relevance score
                all_results.sort(
                    key=lambda x: x.get("relevance_score", 0.0), reverse=True
                )

                return {
                    "query": query,
                    "status": search_results.get("status", "unknown"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": search_results.get("total_found", 0),
                    "results": all_results,
                    "success": True,
                    "summary": search_results.get("summary", {}),
                    "grouped_results": grouped_results,
                }
            else:
                return {
                    "query": query,
                    "status": search_results.get("status", "error"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": 0,
                    "results": [],
                    "success": False,
                    "error": search_results.get("error", "Unknown error"),
                }

        except Exception as e:
            logger.error(f"Query '{query}' failed: {e}")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "success": False,
            }

    def print_query_results(self, results: Dict[str, Any]) -> None:
        """Print query results in a detailed, well-formatted way for frontend and LLM use cases"""
        print(f"\n{'='*80}")
        print(f"🔍 SEARCH RESULTS: '{results['query']}'")
        print(f"{'='*80}")
        print(f"📊 Status: {results['status']}")
        print(f"⏱️  Response Time: {results.get('response_time_ms', 0):.2f}ms")
        print(f"📈 Total Found: {results.get('total_found', 0)}")

        if results.get("success") and results.get("results"):
            print(f"\n📋 SEARCH SUMMARY:")
            print(f"   • Query: '{results['query']}'")
            print(f"   • Results: {len(results['results'])} documents")
            print(f"   • Search Method: Hybrid (BM25 + Vector Similarity)")
            print(f"   • Ranking Profile: Hybrid ranking with semantic understanding")

            print(f"\n🎯 TOP RESULTS:")
            print(f"{'─'*80}")

            for i, result in enumerate(results["results"][:10], 1):
                # Result header with rank and type
                result_type = result.get("type", "Unknown")
                type_emoji = self._get_type_emoji(result_type)
                relevance = result.get("relevance_score", 0.0)
                relevance_pct = f"{relevance * 100:.1f}%" if relevance else "N/A"

                print(f"\n{i:2d}. {type_emoji} {result.get('title', 'No title')}")
                print(f"    {'─' * 60}")

                # Basic metadata
                print(f"    📁 Type: {result_type.title()}")
                print(f"    🎯 Relevance: {relevance_pct} (Score: {relevance:.4f})")
                print(f"    🏷️  Provider: {result.get('provider', 'Unknown')}")
                print(f"    🆔 ID: {result.get('id', 'N/A')}")

                # Search method and confidence information
                search_method = result.get("search_method", "Unknown")
                match_confidence = result.get("match_confidence", "Unknown")
                print(f"    🔍 Search Method: {search_method}")
                print(f"    ✅ Match Confidence: {match_confidence}")

                # Keyword match information
                keyword_info = result.get("keyword_matches", {})
                if keyword_info and keyword_info.get("count", 0) > 0:
                    print(
                        f"    🎯 Keyword Matches: {keyword_info['count']} words ({keyword_info.get('match_ratio', 0):.1%})"
                    )
                    if keyword_info.get("words"):
                        print(
                            f"    📝 Matched Words: {', '.join(keyword_info['words'][:5])}"
                        )

                # Vector similarity if available
                if result.get("vector_similarity") is not None:
                    print(
                        f"    🧠 Vector Similarity: {result['vector_similarity']:.4f}"
                    )

                # Content metrics
                content_len = result.get("content_length", 0)
                search_len = result.get("search_text_length", 0)
                if content_len > 0:
                    print(f"    📏 Content Length: {content_len} chars")
                if search_len > 0:
                    print(f"    🔍 Search Text Length: {search_len} chars")

                # Type-specific metadata
                if result_type == "email":
                    print(f"    📧 From: {result.get('sender', 'Unknown')}")
                    print(
                        f"    📮 To: {', '.join(result.get('recipients', ['Unknown']))}"
                    )
                    print(f"    📂 Folder: {result.get('folder', 'Unknown')}")
                    print(f"    🧵 Thread: {result.get('thread_id', 'N/A')}")
                elif result_type == "calendar":
                    print(f"    📅 Start: {result.get('start_time', 'Unknown')}")
                    print(f"    ⏰ End: {result.get('end_time', 'Unknown')}")
                    print(
                        f"    👥 Attendees: {', '.join(result.get('attendees', ['None']))}"
                    )
                    print(f"    📍 Location: {result.get('location', 'No location')}")
                elif result_type == "contact":
                    print(
                        f"    👤 Display Name: {result.get('display_name', 'Unknown')}"
                    )
                    print(f"    🏢 Company: {result.get('company', 'Unknown')}")
                    print(f"    💼 Job Title: {result.get('job_title', 'Unknown')}")

                # Content and search text
                if result.get("content"):
                    content_preview = (
                        result["content"][:150] + "..."
                        if len(result["content"]) > 150
                        else result["content"]
                    )
                    print(f"    📝 Content: {content_preview}")

                if result.get("search_text"):
                    search_preview = (
                        result["search_text"][:150] + "..."
                        if len(result["search_text"]) > 150
                        else result["search_text"]
                    )
                    print(f"    🔍 Search Text: {search_preview}")

                # Snippet with query highlighting
                if result.get("snippet"):
                    print(f"    💡 Snippet: {result['snippet']}")

                # Timestamps
                if result.get("created_at"):
                    created = self._format_timestamp(result["created_at"])
                    print(f"    📅 Created: {created}")
                if result.get("updated_at"):
                    updated = self._format_timestamp(result["updated_at"])
                    print(f"    🔄 Updated: {updated}")

                print(f"    {'─' * 60}")

            # Show additional results count if there are more
            if len(results["results"]) > 10:
                remaining = len(results["results"]) - 10
                print(f"\n📚 ... and {remaining} more results")

            # Search insights for LLM RAG
            print(f"\n🧠 SEARCH INSIGHTS FOR LLM RAG:")
            print(
                f"   • Primary Content Types: {self._get_content_type_summary(results['results'])}"
            )
            print(
                f"   • Top Relevance Range: {self._get_relevance_range(results['results'])}"
            )
            print(
                f"   • Content Freshness: {self._get_content_freshness(results['results'])}"
            )
            print(
                f"   • Search Confidence: {self._get_search_confidence(results['results'])}"
            )
            print(
                f"   • Search Methods: {self._get_search_methods_summary(results['results'])}"
            )
            print(
                f"   • Vector vs Keyword: {self._get_vector_keyword_breakdown(results['results'])}"
            )
            print(
                f"   • Content Quality: {self._get_content_quality_assessment(results['results'])}"
            )
            print(
                f"   • RAG Readiness: {self._get_rag_readiness_assessment(results['results'])}"
            )

        elif results.get("error"):
            print(f"❌ Error: {results['error']}")

        print(f"{'='*80}")

    def _get_type_emoji(self, result_type: str) -> str:
        """Get appropriate emoji for result type"""
        emoji_map = {
            "email": "📧",
            "calendar": "📅",
            "contact": "👤",
            "file": "📄",
            "document": "📋",
            "message": "💬",
        }
        return emoji_map.get(result_type.lower(), "📄")

    def _format_timestamp(self, timestamp: Any) -> str:
        """Format timestamp for display"""
        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp in milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))

            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except:
            return str(timestamp)

    def _get_content_type_summary(self, results: List[Dict[str, Any]]) -> str:
        """Get summary of content types in results"""
        type_counts: Dict[str, int] = {}
        for result in results:
            result_type = result.get("type", "Unknown")
            type_counts[result_type] = type_counts.get(result_type, 0) + 1

        if not type_counts:
            return "No content types found"

        summary_parts = []
        for content_type, count in sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            summary_parts.append(f"{content_type.title()}: {count}")

        return ", ".join(summary_parts)

    def _get_relevance_range(self, results: List[Dict[str, Any]]) -> str:
        """Get relevance score range for results"""
        if not results:
            return "No results"

        relevances = [
            r.get("relevance_score", 0.0)
            for r in results
            if r.get("relevance_score") is not None
        ]
        if not relevances:
            return "No relevance scores"

        min_rel = min(relevances)
        max_rel = max(relevances)
        avg_rel = sum(relevances) / len(relevances)

        return f"{min_rel:.3f} - {max_rel:.3f} (avg: {avg_rel:.3f})"

    def _get_content_freshness(self, results: List[Dict[str, Any]]) -> str:
        """Get content freshness summary"""
        if not results:
            return "No results"

        timestamps = []
        for result in results:
            if result.get("created_at"):
                try:
                    if isinstance(result["created_at"], (int, float)):
                        ts = result["created_at"] / 1000
                    else:
                        ts = datetime.fromisoformat(
                            str(result["created_at"]).replace("Z", "+00:00")
                        ).timestamp()
                    timestamps.append(ts)
                except:
                    continue

        if not timestamps:
            return "Unknown"

        now = datetime.now(timezone.utc).timestamp()
        oldest = min(timestamps)
        newest = max(timestamps)

        oldest_days = (now - oldest) / (24 * 3600)
        newest_days = (now - newest) / (24 * 3600)

        if oldest_days < 1:
            return "All content from today"
        elif oldest_days < 7:
            return f"Content from last {int(oldest_days)} days"
        elif oldest_days < 30:
            return f"Content from last {int(oldest_days)} days"
        else:
            return f"Content from last {int(oldest_days)} days (some content may be outdated)"

    def _get_search_confidence(self, results: List[Dict[str, Any]]) -> str:
        """Get search confidence assessment"""
        if not results:
            return "No results"

        high_relevance = sum(1 for r in results if r.get("relevance_score", 0) > 0.7)
        medium_relevance = sum(
            1 for r in results if 0.3 <= r.get("relevance_score", 0) <= 0.7
        )
        low_relevance = sum(1 for r in results if r.get("relevance_score", 0) < 0.3)

        total = len(results)

        if high_relevance / total > 0.6:
            return "High confidence - Strong semantic matches found"
        elif (high_relevance + medium_relevance) / total > 0.6:
            return "Medium confidence - Good keyword and semantic matches"
        else:
            return (
                "Low confidence - Limited semantic relevance, consider refining query"
            )

    def _get_search_methods_summary(self, results: List[Dict[str, Any]]) -> str:
        """Get summary of search methods used"""
        if not results:
            return "No results"

        method_counts: Dict[str, int] = {}
        for result in results:
            method = result.get("search_method", "Unknown")
            method_counts[method] = method_counts.get(method, 0) + 1

        if not method_counts:
            return "Unknown search methods"

        summary_parts = []
        for method, count in sorted(
            method_counts.items(), key=lambda x: x[1], reverse=True
        ):
            summary_parts.append(f"{method}: {count}")

        return ", ".join(summary_parts)

    def _get_vector_keyword_breakdown(self, results: List[Dict[str, Any]]) -> str:
        """Get breakdown of vector vs keyword search results"""
        if not results:
            return "No results"

        vector_count = sum(1 for r in results if "Vector" in r.get("search_method", ""))
        keyword_count = sum(
            1 for r in results if "Keyword" in r.get("search_method", "")
        )
        hybrid_count = sum(1 for r in results if "Hybrid" in r.get("search_method", ""))
        other_count = len(results) - vector_count - keyword_count - hybrid_count

        breakdown_parts = []
        if vector_count > 0:
            breakdown_parts.append(f"Vector: {vector_count}")
        if keyword_count > 0:
            breakdown_parts.append(f"Keyword: {keyword_count}")
        if hybrid_count > 0:
            breakdown_parts.append(f"Hybrid: {hybrid_count}")
        if other_count > 0:
            breakdown_parts.append(f"Other: {other_count}")

        return ", ".join(breakdown_parts)

    def _get_content_quality_assessment(self, results: List[Dict[str, Any]]) -> str:
        """Assess content quality for RAG use"""
        if not results:
            return "No results"

        # Analyze content length and completeness
        short_content = sum(1 for r in results if r.get("content_length", 0) < 100)
        medium_content = sum(
            1 for r in results if 100 <= r.get("content_length", 0) < 500
        )
        long_content = sum(1 for r in results if r.get("content_length", 0) >= 500)

        total = len(results)

        if long_content / total > 0.6:
            return "High quality - Most content is substantial (>500 chars)"
        elif (medium_content + long_content) / total > 0.6:
            return "Good quality - Mix of medium and long content"
        else:
            return "Variable quality - Many short content pieces, may need filtering"

    def _get_rag_readiness_assessment(self, results: List[Dict[str, Any]]) -> str:
        """Assess how ready the results are for RAG use"""
        if not results:
            return "Not ready - No results"

        # Check for high-quality, relevant content
        high_quality = sum(
            1
            for r in results
            if r.get("relevance_score", 0) > 0.6
            and r.get("content_length", 0) > 200
            and r.get("match_confidence") in ["High", "Very High"]
        )

        medium_quality = sum(
            1
            for r in results
            if r.get("relevance_score", 0) > 0.4 and r.get("content_length", 0) > 100
        )

        total = len(results)

        if high_quality / total > 0.5:
            return "Excellent - High-quality content ready for RAG"
        elif (high_quality + medium_quality) / total > 0.7:
            return "Good - Most content suitable for RAG with some filtering"
        elif medium_quality / total > 0.5:
            return "Fair - Moderate quality, may need content enhancement"
        else:
            return "Limited - Low-quality content, consider refining search or enhancing data"

    async def dump_all_user_content(self) -> None:
        """Dump all content stored in Vespa for the current user"""
        try:
            print(f"\n{'='*80}")
            print(f"📋 CONTENT DUMP FOR USER: {self.user_email}")
            print(f"{'='*80}")

            # Get all documents for the user
            all_docs_query = {
                "yql": "select * from briefly_document where source_type contains \"email\"",
                "hits": 400,  # Respect Vespa's configured limit
                "timeout": "10s",
                "streaming.groupname": self.user_id,  # Use resolved user ID for streaming group
            }

            print("🔍 Retrieving all documents from Vespa...")
            await self.search_engine.start()

            start_time = time.time()

            # Collect all documents using pagination if needed
            all_documents = []
            offset = 0
            total_count = 0

            while True:
                query = all_docs_query.copy()
                query["offset"] = offset

                try:
                    results = await self.search_engine.search(query)
                    root = results.get("root", {})
                    children = root.get("children", [])

                    if not children:
                        break

                    all_documents.extend(children)
                    total_count = root.get("fields", {}).get("totalCount", 0)

                    print(
                        f"📄 Retrieved {len(children)} documents (offset: {offset}, total so far: {len(all_documents)})"
                    )

                    # If we got fewer results than requested, we've reached the end
                    if len(children) < 400:
                        break

                    offset += 400

                except Exception as e:
                    print(f"⚠️  Error retrieving documents at offset {offset}: {e}")
                    break

            query_time = (time.time() - start_time) * 1000

            print(f"✅ Retrieved {len(all_documents)} documents in {query_time:.2f}ms")
            print(f"📊 Total documents in Vespa: {total_count}")

            if not all_documents:
                print("❌ No documents found for this user")
                return

            # Group documents by type
            docs_by_type: Dict[str, List[Dict[str, Any]]] = {}
            for child in all_documents:
                fields = child.get("fields", {})
                doc_type = fields.get("source_type", "unknown")
                if doc_type not in docs_by_type:
                    docs_by_type[doc_type] = []
                docs_by_type[doc_type].append(child)

            # Display documents by type
            for doc_type, docs in sorted(docs_by_type.items()):
                print(f"\n{'─'*80}")
                print(f"📁 {doc_type.upper()} DOCUMENTS ({len(docs)})")
                print(f"{'─'*80}")

                for i, doc in enumerate(docs, 1):
                    fields = doc.get("fields", {})
                    # Use the correct Vespa field names that match DocumentMapper output
                    doc_id = fields.get("doc_id", "unknown")  # DocumentMapper maps 'id' -> 'doc_id'

                    print(f"\n{i:3d}. 📄 Document ID: {doc_id}")
                    print(f"    {'─' * 60}")

                    # Basic metadata
                    print(f"    🆔 Vespa ID: {doc.get('id', 'N/A')}")
                    print(f"    🏷️  Provider: {fields.get('provider', 'Unknown')}")
                    print(
                        f"    📅 Created: {self._format_timestamp(fields.get('created_at'))}"
                    )
                    print(
                        f"    🔄 Updated: {self._format_timestamp(fields.get('updated_at'))}"
                    )

                    # Title and content
                    if fields.get("title"):
                        print(f"    📝 Title: {fields.get('title')}")

                    if fields.get("content"):
                        content = fields.get("content")
                        # Calculate word count for better content understanding
                        word_count = len(content.split()) if content else 0
                        print(f"    📄 Content ({len(content)} chars, {word_count} words):")
                        
                        # Show more content for emails - first 2000 chars or ~300 words
                        if len(content) > 2000:
                            # Find a good break point near 2000 chars
                            preview = content[:2000]
                            # Try to break at a sentence or word boundary
                            last_period = preview.rfind('.')
                            last_space = preview.rfind(' ')
                            if last_period > 1600:  # If we have a sentence break in reasonable range
                                preview = preview[:last_period + 1]
                            elif last_space > 1800:  # Otherwise break at word boundary
                                preview = preview[:last_space]
                            
                            print(f"      {preview}...")
                            print(f"      [Content truncated. Full content: {len(content)} chars, {word_count} words]")
                        else:
                            print(f"      {content}")

                    if fields.get("search_text"):
                        search_text = fields.get("search_text")
                        search_word_count = len(search_text.split()) if search_text else 0
                        print(f"    🔍 Search Text ({len(search_text)} chars, {search_word_count} words):")
                        if len(search_text) > 500:
                            print(f"      {search_text[:500]}...")
                        else:
                            print(f"      {search_text}")

                    # Type-specific fields
                    if doc_type == "email":
                        # Use the correct Vespa field names from DocumentMapper
                        print(f"    📧 From: {fields.get('sender', 'Unknown')}")  # DocumentMapper maps 'from' -> 'sender'
                        print(
                            f"    📮 To: {', '.join(fields.get('recipients', ['Unknown']))}"  # DocumentMapper maps 'to' -> 'recipients'
                        )
                        print(f"    📂 Folder: {fields.get('folder', 'Unknown')}")
                        print(f"    🧵 Thread: {fields.get('thread_id', 'N/A')}")

                        # Enhanced email metadata display
                        metadata = fields.get("metadata", {})
                        if metadata:
                            print(f"    📊 Email Metadata:")
                            # Show important email metadata first
                            important_keys = ['is_read', 'is_important', 'has_attachments', 'labels']
                            for key in important_keys:
                                if key in metadata:
                                    value = metadata[key]
                                    if key == 'labels' and isinstance(value, list):
                                        if value:
                                            print(f"      • {key}: {', '.join(str(v) for v in value)}")
                                        else:
                                            print(f"      • {key}: (empty)")
                                    else:
                                        print(f"      • {key}: {value}")
                            
                            # Show other metadata
                            for key, value in metadata.items():
                                if key not in important_keys:
                                    if isinstance(value, (list, dict)):
                                        if isinstance(value, list) and value:
                                            print(f"      • {key}: {', '.join(str(v) for v in value)}")
                                        elif isinstance(value, dict) and value:
                                            print(f"      • {key}: {dict(list(value.items())[:3])}...")
                                        else:
                                            print(f"      • {key}: (empty)")
                                    else:
                                        print(f"      • {key}: {value}")
                        
                        # Display thread information
                        if fields.get("quoted_content"):
                            quoted_content = fields.get("quoted_content")
                            quoted_word_count = len(quoted_content.split()) if quoted_content else 0
                            print(f"    🧵 Quoted Content ({len(quoted_content)} chars, {quoted_word_count} words):")
                            if len(quoted_content) > 500:
                                print(f"      {quoted_content[:500]}...")
                                print(f"      [Quoted content truncated. Full quoted content: {len(quoted_content)} chars, {quoted_word_count} words]")
                            else:
                                print(f"      {quoted_content}")
                        
                        if fields.get("thread_summary"):
                            thread_summary = fields.get("thread_summary", {})
                            if thread_summary:
                                print(f"    📊 Thread Summary:")
                                for key, value in thread_summary.items():
                                    if isinstance(value, (list, dict)):
                                        if isinstance(value, list) and value:
                                            print(f"      • {key}: {', '.join(str(v) for v in value)}")
                                        elif isinstance(value, dict) and value:
                                            print(f"      • {key}: {dict(list(value.items())[:3])}...")
                                        else:
                                            print(f"      • {key}: (empty)")
                                    else:
                                        print(f"      • {key}: {value}")

                    elif doc_type == "calendar":
                        print(f"    📅 Start: {fields.get('start_time', 'Unknown')}")
                        print(f"    ⏰ End: {fields.get('end_time', 'Unknown')}")
                        print(
                            f"    👥 Attendees: {', '.join(fields.get('attendees', ['None']))}"
                        )
                        print(
                            f"    📍 Location: {fields.get('location', 'No location')}"
                        )
                        print(f"    🌅 All Day: {fields.get('is_all_day', False)}")
                        print(f"    🔄 Recurring: {fields.get('recurring', False)}")

                    elif doc_type == "contact":
                        print(f"    👤 Display Name: {fields.get('title', 'Unknown')}")
                        print(f"    🏢 Company: {fields.get('company', 'Unknown')}")
                        print(f"    💼 Job Title: {fields.get('job_title', 'Unknown')}")
                        print(
                            f"    📧 Emails: {', '.join(fields.get('email_addresses', ['None']))}"
                        )
                        print(
                            f"    📱 Phones: {', '.join(fields.get('phone_numbers', ['None']))}"
                        )
                        print(f"    🏠 Address: {fields.get('address', 'No address')}")

                    # Raw fields for debugging - show only the most useful ones
                    print(f"    🔧 Raw Fields:")
                    useful_fields = [
                        'doc_id', 'source_type', 'provider', 'created_at', 'updated_at',
                        'thread_id', 'folder', 'sender', 'recipients', 'title', 'content', 'search_text'
                    ]
                    for key, value in fields.items():
                        if key in useful_fields:
                            if isinstance(value, (list, dict)):
                                if isinstance(value, list) and value:
                                    if len(value) <= 3:
                                        print(f"      • {key}: {', '.join(str(v) for v in value)}")
                                    else:
                                        print(f"      • {key}: {', '.join(str(v) for v in value[:3])}... (and {len(value)-3} more)")
                                elif isinstance(value, dict) and value:
                                    print(f"      • {key}: {dict(list(value.items())[:3])}...")
                                else:
                                    print(f"      • {key}: (empty)")
                            else:
                                print(f"      • {key}: {value}")
                    
                    # Show a few other interesting fields that might be present
                    other_interesting = ['search_text', 'metadata']
                    for key in other_interesting:
                        if key in fields and key not in useful_fields:
                            value = fields[key]
                            if key == 'search_text':
                                preview = str(value)[:100] if value else "(empty)"
                                print(f"      • {key}: {preview}...")
                            elif key == 'metadata':
                                if isinstance(value, dict) and value:
                                    print(f"      • {key}: {len(value)} metadata items")
                                else:
                                    print(f"      • {key}: (empty)")
                    
                    # Debug: Show all available fields to understand document structure
                    print(f"    🔍 All Available Fields:")
                    for key, value in fields.items():
                        if key not in useful_fields + other_interesting:
                            if isinstance(value, (list, dict)):
                                if isinstance(value, list) and value:
                                    if len(value) <= 5:
                                        print(f"      • {key}: {', '.join(str(v) for v in value)}")
                                    else:
                                        print(f"      • {key}: {', '.join(str(v) for v in value[:5])}... (and {len(value)-5} more)")
                                elif isinstance(value, dict) and value:
                                    print(f"      • {key}: {dict(list(value.items())[:5])}...")
                                else:
                                    print(f"      • {key}: (empty)")
                            else:
                                # For string values, show preview if long
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"      • {key}: {value[:100]}...")
                                else:
                                    print(f"      • {key}: {value}")

                    print(f"    {'─' * 60}")

            # Summary
            print(f"\n{'='*80}")
            print(f"📊 DUMP SUMMARY")
            print(f"{'='*80}")
            print(f"User: {self.user_email}")
            print(f"Total Documents: {total_count}")
            print(
                f"Document Types: {', '.join(f'{t}: {len(docs)}' for t, docs in docs_by_type.items())}"
            )
            
            # Content statistics
            total_content_chars = 0
            total_content_words = 0
            content_docs = 0
            
            for doc in all_documents:
                fields = doc.get("fields", {})
                content = fields.get("content", "")
                if content:
                    total_content_chars += len(content)
                    total_content_words += len(content.split())
                    content_docs += 1
            
            if content_docs > 0:
                avg_chars = total_content_chars / content_docs
                avg_words = total_content_words / content_docs
                print(f"Content Statistics:")
                print(f"  • Documents with content: {content_docs}")
                print(f"  • Total content: {total_content_chars:,} characters, {total_content_words:,} words")
                print(f"  • Average per document: {avg_chars:.0f} chars, {avg_words:.0f} words")
            
            print(f"Query Time: {query_time:.2f}ms")
            print(f"Vespa Endpoint: {self.vespa_endpoint}")
            print(f"{'='*80}")

        except Exception as e:
            print(f"❌ Error dumping content: {e}")
            logger.error(f"Failed to dump content: {e}")
        finally:
            await self.search_engine.close()

    async def run_interactive_mode(self) -> None:
        """Run interactive search mode"""
        print("\n" + "=" * 60)
        print("VESPA INTERACTIVE SEARCH MODE")
        print("=" * 60)
        print("Type your search queries below. Type 'quit', 'exit', or 'q' to exit.")
        print("Type 'help' for search tips.")
        print("=" * 60)

        while True:
            try:
                query = input("\nSearch query: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                elif query.lower() == "help":
                    print("\nSearch Tips:")
                    print('- Use quotes for exact phrases: "meeting notes"')
                    print("- Search by type: emails, calendar events, contacts")
                    print('- Use natural language: "emails from last week"')
                    print('- Try semantic search: "project collaboration"')
                    continue
                elif not query:
                    continue

                print(f"\nSearching for: {query}")
                results = await self.run_single_query(query)
                self.print_query_results(results)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics for the current user"""
        try:
            await self.search_engine.start()

            # Query to get total document count for this user
            user_query = {
                "yql": "select * from briefly_document where source_type contains \"email\"",
                "hits": 0,  # We only want the count, not the actual documents
                "timeout": "5s",
                "streaming.groupname": self.user_id,  # Use resolved user ID for streaming group
            }

            start_time = time.time()
            results = await self.search_engine.search(user_query)
            query_time = (time.time() - start_time) * 1000

            total_documents = (
                results.get("root", {}).get("fields", {}).get("totalCount", 0)
            )

            # Get breakdown by source type
            source_type_query = {
                "yql": "select source_type from briefly_document where source_type contains \"email\"",
                "hits": 0,
                "timeout": "5s",
                "grouping": "source_type",
                "streaming.groupname": self.user_id,  # Use resolved user ID for streaming group
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
                "yql": "select provider from briefly_document where source_type contains \"email\"",
                "hits": 0,
                "timeout": "5s",
                "grouping": "provider",
                "streaming.groupname": self.user_id,  # Use resolved user ID for streaming group
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
            logger.error(f"Error getting user stats: {e}")
            return {
                "user_email": self.user_email,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_all_users_stats(self) -> Dict[str, Any]:
        """Get statistics for all users in the database"""
        try:
            # In streaming mode, we can't query all users at once without specifying a group
            # Instead, we'll return a message explaining this limitation
            return {
                "message": "In streaming mode, user statistics must be queried individually for each user",
                "streaming_mode_note": "Use get_user_stats_for_email() for individual user statistics",
                "total_users": "N/A - streaming mode limitation",
                "total_documents": "N/A - streaming mode limitation",
                "user_stats": [],
                "aggregate_source_types": {},
                "aggregate_providers": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting all users stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_user_stats_for_email(self, user_email: str) -> Dict[str, Any]:
        """Get statistics for a specific user email"""
        try:
            # Query to get total document count for this user
            user_query = {
                "yql": f'select * from briefly_document where user_id contains "{user_email}"',
                "hits": 0,
                "timeout": "5s",
                "streaming.groupname": user_email,  # Add streaming mode support for user isolation
            }

            start_time = time.time()
            results = await self.search_engine.search(user_query)
            query_time = (time.time() - start_time) * 1000

            total_documents = (
                results.get("root", {}).get("fields", {}).get("totalCount", 0)
            )

            # Get breakdown by source type
            source_type_query = {
                "yql": f'select source_type from briefly_document where user_id contains "{user_email}"',
                "hits": 0,
                "timeout": "5s",
                "grouping": "source_type",
                "streaming.groupname": user_email,  # Add streaming mode support for user isolation
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
                "yql": f'select provider from briefly_document where user_id contains "{user_email}"',
                "hits": 0,
                "timeout": "5s",
                "grouping": "provider",
                "streaming.groupname": user_email,  # Add streaming mode support for user isolation
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
                "user_email": user_email,
                "total_documents": total_documents,
                "source_type_breakdown": source_breakdown,
                "provider_breakdown": provider_breakdown,
                "query_time_ms": round(query_time, 2),
            }

        except Exception as e:
            logger.error(f"Error getting stats for user {user_email}: {e}")
            return {"user_email": user_email, "error": str(e)}

    def print_user_stats(self, stats: Dict[str, Any]) -> None:
        """Print user statistics in a formatted way"""
        print(f"\n{'='*60}")
        print(f"USER STATISTICS: {stats['user_email']}")
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

    def print_all_users_stats(self, stats: Dict[str, Any]) -> None:
        """Print statistics for all users"""
        print(f"{'='*60}")
        print("ALL USERS STATISTICS")
        print(f"{'='*60}")

        if "error" in stats:
            print(f"Error: {stats['error']}")
            return

        # Handle both numeric and string values for streaming mode compatibility
        total_users = stats.get("total_users", 0)
        total_documents = stats.get("total_documents", 0)

        if isinstance(total_users, (int, float)):
            print(f"Total Users: {total_users:,}")
        else:
            print(f"Total Users: {total_users}")

        if isinstance(total_documents, (int, float)):
            print(f"Total Documents: {total_documents:,}")
        else:
            print(f"Total Documents: {total_documents}")

        # Show streaming mode message if present
        if "message" in stats:
            print(f"\nNote: {stats['message']}")
            if "streaming_mode_note" in stats:
                print(f"  {stats['streaming_mode_note']}")

        # Aggregate source types
        aggregate_source_types = stats.get("aggregate_source_types", {})
        if aggregate_source_types:
            print(f"\nAggregate Source Type Breakdown:")
            for source_type, count in sorted(
                aggregate_source_types.items(), key=lambda x: x[1], reverse=True
            ):
                if isinstance(count, (int, float)):
                    print(f"  {source_type}: {count:,}")
                else:
                    print(f"  {source_type}: {count}")

        # Aggregate providers
        aggregate_providers = stats.get("aggregate_providers", {})
        if aggregate_providers:
            print(f"\nAggregate Provider Breakdown:")
            for provider, count in sorted(
                aggregate_providers.items(), key=lambda x: x[1], reverse=True
            ):
                if isinstance(count, (int, float)):
                    print(f"  {provider}: {count:,}")
                else:
                    print(f"  {provider}: {count}")

        # Individual user stats
        user_stats = stats.get("user_stats", [])
        if user_stats:
            print(f"\nIndividual User Statistics:")
            for user_stat in user_stats:
                if "error" not in user_stat:
                    total_docs = user_stat.get("total_documents", 0)
                    if isinstance(total_docs, (int, float)):
                        print(
                            f"\n  {user_stat['user_email']}: {total_docs:,} documents"
                        )
                    else:
                        print(f"\n  {user_stat['user_email']}: {total_docs} documents")

        print(f"{'='*60}")


async def main() -> Optional[Dict[str, Any]]:
    """Main function for running the Vespa search demo"""
    import argparse

    parser = argparse.ArgumentParser(
        description="""Vespa Search Demo - Comprehensive search capabilities demonstration

This demo focuses on testing and showcasing Vespa's search capabilities
without the complexity of data ingestion and backfill functionality.

FEATURES:
  • Interactive search mode with real-time querying
  • Comprehensive search demo with multiple test scenarios
  • User statistics collection and display
  • Multi-user database statistics and aggregations
  • Performance benchmarking and metrics
  • Support for different ranking profiles (hybrid, BM25, semantic)

USAGE EXAMPLES:
  # Interactive mode with user stats (default)
  python3 vespa_search.py user@example.com

  # Show statistics for all users
  python3 vespa_search.py user@example.com --stats

  # Only show statistics (no interactive mode)
  python3 vespa_search.py user@example.com --stats-only

  # Run comprehensive search demo
  python3 vespa_search.py user@example.com --demo

  # Execute single query non-interactively
  python3 vespa_search.py user@example.com --query "meeting notes"

  # Custom Vespa endpoint
  python3 vespa_search.py user@example.com --vespa-endpoint http://localhost:8080

  # Dump all content stored in Vespa for the user
  python3 vespa_search.py user@example.com --dump

STATISTICS PROVIDED:
  • Current user document count and breakdowns
  • Source type distribution (emails, calendar, contacts, etc.)
  • Provider breakdown (Outlook, Gmail, etc.)
  • All users aggregate statistics
  • Query performance metrics and response times

SEARCH CAPABILITIES:
  • Full-text search across titles, content, and search text
  • User-scoped data isolation
  • Hybrid ranking (BM25 + vector similarity)
  • Semantic search with embeddings
  • Source type and provider filtering
  • Real-time search with performance metrics

REQUIREMENTS:
  • Vespa instance running and accessible
  • User data indexed in Vespa database
  • Python dependencies: aiohttp, asyncio""",
        epilog="Example: python3 vespa_search.py trybriefly@outlook.com --demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "email",
        help="Email address of the user to search (e.g., trybriefly@outlook.com)",
    )
    parser.add_argument(
        "--vespa-endpoint", default="http://localhost:8080", help="Vespa endpoint"
    )
    parser.add_argument("--output-file", help="Output file for demo results")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the comprehensive demo instead of interactive mode",
    )
    parser.add_argument("--query", help="Run a single query non-interactively")
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics for all users (in addition to current user stats)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't run interactive mode",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump all content stored in Vespa for the user",
    )

    args = parser.parse_args()

    # Demo configuration
    config = {"vespa_endpoint": args.vespa_endpoint, "user_email": args.email}

    try:
        async with VespaSearchDemo(config) as demo:
            # Initialize the demo by resolving email to user ID
            if not await demo.initialize():
                print(f"❌ Failed to initialize search demo for email: {args.email}")
                return None
            
            # Show stats for the current user when starting (unless --stats-only)
            if not args.stats_only:
                print(f"\nCollecting statistics for user: {args.email}")
                user_stats = await demo.get_user_stats()
                demo.print_user_stats(user_stats)
                print()

            if args.demo:
                # Run the comprehensive demo
                results = await demo.run_search_demo()

                # Print summary
                print("\n" + "=" * 60)
                print("VESPA SEARCH DEMO RESULTS SUMMARY")
                print("=" * 60)
                print(f"Status: {results['status']}")

                if results["status"] == "completed":
                    performance = results.get("performance_metrics", {})
                    print(f"Total Queries: {performance.get('total_queries', 0)}")
                    print(f"Success Rate: {performance.get('success_rate', 0):.1f}%")
                    print(
                        f"Average Response Time: {performance.get('average_response_time_ms', 0):.2f}ms"
                    )
                    print(f"Total Scenarios: {performance.get('total_scenarios', 0)}")

                    search_quality = results.get("search_quality", {})
                    print(
                        f"Overall Success Rate: {search_quality.get('overall_success_rate', 0):.1f}%"
                    )

                    # Show scenario success rates
                    print("\nScenario Success Rates:")
                    for scenario, rate in search_quality.get(
                        "scenario_success_rates", {}
                    ).items():
                        print(f"  {scenario}: {rate:.1f}%")

                    # Show response time distribution
                    time_dist = search_quality.get("response_time_distribution", {})
                    if time_dist:
                        print(f"\nResponse Time Distribution:")
                        print(f"  Fast (<10ms): {time_dist.get('fast', 0)}")
                        print(f"  Medium (10-50ms): {time_dist.get('medium', 0)}")
                        print(f"  Slow (≥50ms): {time_dist.get('slow', 0)}")

                    # Show ranking profile performance
                    ranking_perf = search_quality.get("ranking_profile_performance", {})
                    if ranking_perf:
                        print(f"\nRanking Profile Performance:")
                        for profile, rate in ranking_perf.items():
                            print(f"  {profile}: {rate:.1f}%")

                print("=" * 60)

                # Save results to file
                if args.output_file:
                    with open(args.output_file, "w") as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"\nDetailed results saved to: {args.output_file}")

                return results

            elif args.query:
                # Run a single query non-interactively
                print(f"Running query: {args.query}")
                results = await demo.run_single_query(args.query)
                demo.print_query_results(results)
                return results

            elif args.stats or args.stats_only:
                # Show all users stats (user stats already shown above if not --stats-only)
                print("\nCollecting statistics for all users...")
                all_users_stats = await demo.get_all_users_stats()
                demo.print_all_users_stats(all_users_stats)
                return all_users_stats

            elif args.dump:
                # Dump all content stored in Vespa for the user
                print(f"\nDumping all content stored in Vespa for user: {args.email}")
                await demo.dump_all_user_content()
                return {"status": "dumped", "user": args.email}

            else:
                # Interactive mode (default)
                await demo.run_interactive_mode()

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
