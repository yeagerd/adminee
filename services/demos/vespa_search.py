#!/usr/bin/env python3
"""
Vespa Search Demo - Comprehensive search capabilities demonstration

This demo focuses on testing and showcasing Vespa's search capabilities
without the complexity of data ingestion and backfill functionality.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import time

from services.vespa_query.search_engine import SearchEngine
from services.chat.agents.llm_tools import VespaSearchTool, UserDataSearchTool, SemanticSearchTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VespaSearchDemo:
    """Comprehensive search demo using Vespa capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vespa_endpoint = config["vespa_endpoint"]
        self.demo_user_id = config.get("demo_user_id", "demo_user_1")
        
        # Initialize search tools
        self.vespa_search = VespaSearchTool(self.vespa_endpoint, self.demo_user_id)
        self.user_data_search = UserDataSearchTool(self.vespa_endpoint, self.demo_user_id)
        self.semantic_search = SemanticSearchTool(self.vespa_endpoint, self.demo_user_id)
        
        # Comprehensive search test scenarios
        self.search_scenarios = [
            {
                "name": "Basic Search Functionality",
                "queries": [
                    "test query",
                    "simple search",
                    "basic functionality"
                ],
                "expected": "Basic search responses"
            },
            {
                "name": "User Isolation Testing",
                "queries": [
                    f"user {self.demo_user_id} data",
                    "personal documents",
                    "my emails"
                ],
                "expected": "User-scoped results"
            },
            {
                "name": "Source Type Filtering",
                "queries": [
                    "emails from last week",
                    "calendar events tomorrow",
                    "contact information",
                    "file documents"
                ],
                "expected": "Type-specific filtering"
            },
            {
                "name": "Semantic Search",
                "queries": [
                    "meeting planning documents",
                    "project collaboration",
                    "team communication"
                ],
                "expected": "Concept-based results"
            },
            {
                "name": "Performance Benchmarking",
                "queries": [
                    "quick search test",
                    "performance query",
                    "speed test"
                ],
                "expected": "Response time metrics"
            }
        ]
        
        # Advanced search test scenarios
        self.advanced_scenarios = [
            {
                "name": "Hybrid Search (BM25 + Vector)",
                "ranking_profile": "hybrid",
                "queries": [
                    "important meeting notes",
                    "urgent project updates",
                    "critical documents"
                ]
            },
            {
                "name": "BM25 Ranking",
                "ranking_profile": "bm25", 
                "queries": [
                    "exact keyword match",
                    "specific terms",
                    "precise search"
                ]
            },
            {
                "name": "Semantic Ranking",
                "ranking_profile": "semantic",
                "queries": [
                    "similar concepts",
                    "related ideas",
                    "contextual meaning"
                ]
            }
        ]
    
    async def cleanup(self):
        """Clean up resources and close aiohttp sessions"""
        try:
            logger.info("Cleaning up resources...")
            
            # Close search engine sessions - handle all nested instances
            if hasattr(self.vespa_search, 'search_engine'):
                await self.vespa_search.search_engine.close()
            
            # UserDataSearchTool has a VespaSearchTool which has a SearchEngine
            if hasattr(self.user_data_search, 'vespa_search') and hasattr(self.user_data_search.vespa_search, 'search_engine'):
                await self.user_data_search.vespa_search.search_engine.close()
            
            if hasattr(self.semantic_search, 'search_engine'):
                await self.semantic_search.search_engine.close()
                
            logger.info("Resource cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cleanup()
    
    async def run_search_demo(self) -> Dict[str, Any]:
        """Run the comprehensive search demo"""
        logger.info("Starting Vespa search capabilities demo...")
        
        demo_start = time.time()
        demo_results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "search_scenarios": [],
            "advanced_scenarios": [],
            "performance_metrics": {},
            "search_quality": {},
            "end_time": None,
            "status": "running"
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
            demo_results["performance_metrics"] = self._calculate_performance_metrics(demo_results)
            
            # Assess search quality
            demo_results["search_quality"] = self._assess_search_quality(demo_results)
            
            demo_results["end_time"] = datetime.now(timezone.utc).isoformat()
            demo_results["status"] = "completed"
            
            demo_duration = time.time() - demo_start
            logger.info(f"Search demo completed successfully in {demo_duration:.2f} seconds")
            
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
            "expected": scenario["expected"]
        }
        
        for query in scenario["queries"]:
            try:
                start_time = time.time()
                
                # Test with user data search
                results = await self.user_data_search.search_all_data(query, max_results=10)
                
                response_time = (time.time() - start_time) * 1000
                
                query_result = {
                    "query": query,
                    "status": results.get("status", "unknown"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": results.get("total_found", 0),
                    "success": results.get("status") == "success"
                }
                
                scenario_result["queries"].append(query_result)
                
                if query_result["success"]:
                    scenario_result["successful_queries"] += 1
                else:
                    scenario_result["failed_queries"] += 1
                    
            except Exception as e:
                logger.error(f"Query '{query}' failed: {e}")
                scenario_result["queries"].append({
                    "query": query,
                    "status": "error",
                    "error": str(e),
                    "success": False
                })
                scenario_result["failed_queries"] += 1
        
        # Calculate average response time
        successful_times = [q["response_time_ms"] for q in scenario_result["queries"] if q.get("response_time_ms")]
        if successful_times:
            scenario_result["average_response_time"] = sum(successful_times) / len(successful_times)
        
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
            "average_response_time": 0.0
        }
        
        for query in scenario["queries"]:
            try:
                start_time = time.time()
                
                # Test with specific ranking profile
                results = await self.vespa_search.search(
                    query=query,
                    max_results=10,
                    ranking_profile=scenario["ranking_profile"]
                )
                
                response_time = (time.time() - start_time) * 1000
                
                query_result = {
                    "query": query,
                    "status": results.get("status", "unknown"),
                    "response_time_ms": round(response_time, 2),
                    "total_found": results.get("total_found", 0),
                    "ranking_profile": scenario["ranking_profile"],
                    "success": results.get("status") == "success"
                }
                
                scenario_result["queries"].append(query_result)
                
                if query_result["success"]:
                    scenario_result["successful_queries"] += 1
                else:
                    scenario_result["failed_queries"] += 1
                    
            except Exception as e:
                logger.error(f"Advanced query '{query}' failed: {e}")
                scenario_result["queries"].append({
                    "query": query,
                    "status": "error",
                    "error": str(e),
                    "success": False
                })
                scenario_result["failed_queries"] += 1
        
        # Calculate average response time
        successful_times = [q["response_time_ms"] for q in scenario_result["queries"] if q.get("response_time_ms")]
        if successful_times:
            scenario_result["average_response_time"] = sum(successful_times) / len(successful_times)
        
        return scenario_result
    
    def _calculate_performance_metrics(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics across all scenarios"""
        all_queries = []
        
        # Collect queries from basic scenarios
        for scenario in demo_results.get("search_scenarios", []):
            all_queries.extend(scenario.get("queries", []))
        
        # Collect queries from advanced scenarios
        for scenario in demo_results.get("advanced_scenarios", []):
            all_queries.extend(scenario.get("queries", []))
        
        if not all_queries:
            return {"total_queries": 0, "success_rate": 0.0, "average_response_time": 0.0}
        
        total_queries = len(all_queries)
        successful_queries = sum(1 for q in all_queries if q.get("success", False))
        success_rate = (successful_queries / total_queries) * 100 if total_queries > 0 else 0
        
        # Calculate average response time
        response_times = [q.get("response_time_ms", 0) for q in all_queries if q.get("response_time_ms")]
        average_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": round(success_rate, 2),
            "average_response_time_ms": round(average_response_time, 2),
            "total_scenarios": len(demo_results.get("search_scenarios", [])) + len(demo_results.get("advanced_scenarios", []))
        }
    
    def _assess_search_quality(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of search results"""
        quality_metrics = {
            "overall_success_rate": 0.0,
            "scenario_success_rates": {},
            "response_time_distribution": {},
            "ranking_profile_performance": {}
        }
        
        # Calculate overall success rate
        performance = demo_results.get("performance_metrics", {})
        quality_metrics["overall_success_rate"] = performance.get("success_rate", 0.0)
        
        # Calculate scenario success rates
        for scenario in demo_results.get("search_scenarios", []):
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["scenario_success_rates"][scenario["name"]] = round((successful / total) * 100, 2)
        
        for scenario in demo_results.get("advanced_scenarios", []):
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["scenario_success_rates"][scenario["name"]] = round((successful / total) * 100, 2)
        
        # Analyze response time distribution
        all_times = []
        for scenario in demo_results.get("search_scenarios", []):
            all_times.extend([q.get("response_time_ms", 0) for q in scenario.get("queries", []) if q.get("response_time_ms")])
        for scenario in demo_results.get("advanced_scenarios", []):
            all_times.extend([q.get("response_time_ms", 0) for q in scenario.get("queries", []) if q.get("response_time_ms")])
        
        if all_times:
            quality_metrics["response_time_distribution"] = {
                "fast": len([t for t in all_times if t < 10]),      # < 10ms
                "medium": len([t for t in all_times if 10 <= t < 50]),  # 10-50ms
                "slow": len([t for t in all_times if t >= 50])      # >= 50ms
            }
        
        # Analyze ranking profile performance
        for scenario in demo_results.get("advanced_scenarios", []):
            profile = scenario.get("ranking_profile", "unknown")
            total = scenario.get("total_queries", 0)
            successful = scenario.get("successful_queries", 0)
            if total > 0:
                quality_metrics["ranking_profile_performance"][profile] = round((successful / total) * 100, 2)
        
        return quality_metrics

    async def run_single_query(self, query: str) -> Dict[str, Any]:
        """Run a single query and return results"""
        try:
            start_time = time.time()
            
            # Use user data search for comprehensive results
            results = await self.user_data_search.search_all_data(query, max_results=20)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "query": query,
                "status": results.get("status", "unknown"),
                "response_time_ms": round(response_time, 2),
                "total_found": results.get("total_found", 0),
                "results": results.get("results", []),
                "success": results.get("status") == "success"
            }
            
        except Exception as e:
            logger.error(f"Query '{query}' failed: {e}")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "success": False
            }

    def print_query_results(self, results: Dict[str, Any]):
        """Print query results in a formatted way"""
        print(f"\n{'='*60}")
        print(f"QUERY RESULTS: {results['query']}")
        print(f"{'='*60}")
        print(f"Status: {results['status']}")
        print(f"Response Time: {results.get('response_time_ms', 0):.2f}ms")
        print(f"Total Found: {results.get('total_found', 0)}")
        
        if results.get("success") and results.get("results"):
            print(f"\nTop Results:")
            for i, result in enumerate(results["results"][:5], 1):
                print(f"\n{i}. {result.get('title', 'No title')}")
                print(f"   Type: {result.get('source_type', 'Unknown')}")
                print(f"   Relevance: {result.get('relevance', 'N/A')}")
                if result.get('snippet'):
                    print(f"   Snippet: {result['snippet'][:100]}...")
        elif results.get("error"):
            print(f"Error: {results['error']}")
        
        print(f"{'='*60}")

    async def run_interactive_mode(self):
        """Run interactive search mode"""
        print("\n" + "="*60)
        print("VESPA INTERACTIVE SEARCH MODE")
        print("="*60)
        print("Type your search queries below. Type 'quit', 'exit', or 'q' to exit.")
        print("Type 'help' for search tips.")
        print("="*60)
        
        while True:
            try:
                query = input("\nSearch query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                elif query.lower() == 'help':
                    print("\nSearch Tips:")
                    print("- Use quotes for exact phrases: \"meeting notes\"")
                    print("- Search by type: emails, calendar events, contacts")
                    print("- Use natural language: \"emails from last week\"")
                    print("- Try semantic search: \"project collaboration\"")
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

async def main():
    """Main function for running the Vespa search demo"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Vespa search capabilities demo")
    parser.add_argument("--vespa-endpoint", default="http://localhost:8080", help="Vespa endpoint")
    parser.add_argument("--demo-user-id", default="demo_user_1", help="Demo user ID")
    parser.add_argument("--output-file", help="Output file for demo results")
    parser.add_argument("--demo", action="store_true", help="Run the comprehensive demo instead of interactive mode")
    parser.add_argument("--query", help="Run a single query non-interactively")
    
    args = parser.parse_args()
    
    # Demo configuration
    config = {
        "vespa_endpoint": args.vespa_endpoint,
        "demo_user_id": args.demo_user_id
    }
    
    try:
        async with VespaSearchDemo(config) as demo:
            if args.demo:
                # Run the comprehensive demo
                results = await demo.run_search_demo()
                
                # Print summary
                print("\n" + "="*60)
                print("VESPA SEARCH DEMO RESULTS SUMMARY")
                print("="*60)
                print(f"Status: {results['status']}")
                
                if results["status"] == "completed":
                    performance = results.get("performance_metrics", {})
                    print(f"Total Queries: {performance.get('total_queries', 0)}")
                    print(f"Success Rate: {performance.get('success_rate', 0):.1f}%")
                    print(f"Average Response Time: {performance.get('average_response_time_ms', 0):.2f}ms")
                    print(f"Total Scenarios: {performance.get('total_scenarios', 0)}")
                    
                    search_quality = results.get("search_quality", {})
                    print(f"Overall Success Rate: {search_quality.get('overall_success_rate', 0):.1f}%")
                    
                    # Show scenario success rates
                    print("\nScenario Success Rates:")
                    for scenario, rate in search_quality.get("scenario_success_rates", {}).items():
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
                
                print("="*60)
                
                # Save results to file
                if args.output_file:
                    with open(args.output_file, 'w') as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"\nDetailed results saved to: {args.output_file}")
                
                return results
                
            elif args.query:
                # Run a single query non-interactively
                print(f"Running query: {args.query}")
                results = await demo.run_single_query(args.query)
                demo.print_query_results(results)
                return results
                
            else:
                # Interactive mode (default)
                await demo.run_interactive_mode()
                
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
