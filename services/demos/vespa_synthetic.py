#!/usr/bin/env python3
"""
Vespa-Powered Chat Demo - Enhanced chat experience using Vespa data
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
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


class VespaChatDemo:
    """Enhanced chat demo using Vespa search capabilities"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vespa_endpoint = config["vespa_endpoint"]
        self.demo_user_id = config.get("demo_user_id", "demo_user_1")

        # Initialize search tools
        self.vespa_search = VespaSearchTool(self.vespa_endpoint, self.demo_user_id)
        self.user_data_search = UserDataSearchTool(
            self.vespa_endpoint, self.demo_user_id
        )
        self.semantic_search = SemanticSearchTool(
            self.vespa_endpoint, self.demo_user_id
        )

        # Demo conversation scenarios
        self.conversation_scenarios = [
            {
                "name": "Cross-Platform Email Search",
                "user_query": "Quarterly planning doc and invites from last month",
                "expected_results": ["emails", "calendar_events", "files"],
                "follow_up_questions": [
                    "Show me the most recent planning documents",
                    "Who was invited to these meetings?",
                    "What were the key discussion points?",
                ],
            },
            {
                "name": "Person-Centric Search",
                "user_query": "Threads with Alex Chen about SOW",
                "expected_results": ["emails", "calendar_events"],
                "follow_up_questions": [
                    "When was the last communication with Alex?",
                    "What's the status of the SOW?",
                    "Show me related calendar events",
                ],
            },
            {
                "name": "Semantic Document Discovery",
                "user_query": "Travel receipts and expense reports",
                "expected_results": ["emails", "files"],
                "follow_up_questions": [
                    "What was the total travel expense?",
                    "Show me receipts from last quarter",
                    "Who submitted these expenses?",
                ],
            },
            {
                "name": "Time-Scoped Search",
                "user_query": "Meetings next week with finance team",
                "expected_results": ["calendar_events", "emails"],
                "follow_up_questions": [
                    "What's the agenda for these meetings?",
                    "Who from finance will be attending?",
                    "Are there any pre-meeting materials?",
                ],
            },
        ]

    async def cleanup(self):
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

            logger.info("Resource cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cleanup()

    async def run_chat_demo(self) -> Dict[str, Any]:
        """Run the complete chat demo"""
        logger.info("Starting Vespa-powered chat demo...")

        demo_start = time.time()
        demo_results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "conversation_scenarios": [],
            "performance_metrics": {},
            "search_quality": {},
            "user_experience": {},
        }

        try:
            # Run conversation scenarios
            for scenario in self.conversation_scenarios:
                logger.info(f"Running scenario: {scenario['name']}")
                scenario_result = await self._run_conversation_scenario(scenario)
                demo_results["conversation_scenarios"].append(scenario_result)

            # Calculate performance metrics
            demo_results["performance_metrics"] = self._calculate_performance_metrics(
                demo_results["conversation_scenarios"]
            )

            # Assess search quality
            demo_results["search_quality"] = self._assess_search_quality(
                demo_results["conversation_scenarios"]
            )

            # Evaluate user experience
            demo_results["user_experience"] = self._evaluate_user_experience(
                demo_results["conversation_scenarios"]
            )

            demo_results["end_time"] = datetime.now(timezone.utc).isoformat()
            demo_results["status"] = "completed"

            demo_duration = time.time() - demo_start
            logger.info(
                f"Chat demo completed successfully in {demo_duration:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"Chat demo failed: {e}")
            demo_results["status"] = "failed"
            demo_results["error"] = str(e)
            demo_results["end_time"] = datetime.now(timezone.utc).isoformat()
        finally:
            # Ensure cleanup happens even if there's an exception
            await self.cleanup()

        return demo_results

    async def _run_conversation_scenario(
        self, scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single conversation scenario"""
        scenario_result = {
            "name": scenario["name"],
            "user_query": scenario["user_query"],
            "initial_search": None,
            "follow_up_conversations": [],
            "total_results": 0,
            "search_time_ms": 0,
            "relevance_score": 0.0,
        }

        try:
            # Initial search
            logger.info(f"Processing query: {scenario['user_query']}")
            initial_search = await self._process_user_query(scenario["user_query"])
            scenario_result["initial_search"] = initial_search
            scenario_result["total_results"] = initial_search.get("total_found", 0)
            scenario_result["search_time_ms"] = initial_search.get("search_time_ms", 0)

            # Process follow-up questions
            for follow_up in scenario["follow_up_questions"]:
                follow_up_result = await self._process_follow_up_question(
                    follow_up, initial_search, scenario["user_query"]
                )
                scenario_result["follow_up_conversations"].append(follow_up_result)

            # Calculate relevance score
            scenario_result["relevance_score"] = self._calculate_scenario_relevance(
                scenario_result
            )

            logger.info(
                f"Scenario '{scenario['name']}' completed with relevance score {scenario_result['relevance_score']:.2f}"
            )

        except Exception as e:
            logger.error(f"Scenario '{scenario['name']}' failed: {e}")
            scenario_result["error"] = str(e)

        return scenario_result

    async def _process_user_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using Vespa search"""
        try:
            start_time = time.time()

            # Use user data search for comprehensive results
            search_results = await self.user_data_search.search_all_data(
                query, max_results=20
            )

            search_time = (time.time() - start_time) * 1000

            # Enhance results with chat-friendly formatting
            enhanced_results = self._enhance_results_for_chat(search_results, query)

            return {
                "status": "success",
                "query": query,
                "results": enhanced_results,
                "total_found": search_results.get("total_messages", 0),
                "search_time_ms": round(search_time, 2),
                "search_type": "comprehensive",
                "result_summary": self._generate_result_summary(enhanced_results),
            }

        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "results": [],
                "total_found": 0,
                "search_time_ms": 0,
            }

    async def _process_follow_up_question(
        self, follow_up: str, initial_search: Dict[str, Any], original_query: str
    ) -> Dict[str, Any]:
        """Process a follow-up question based on initial search context"""
        try:
            # Combine original query context with follow-up
            contextual_query = f"{original_query} {follow_up}"

            # Use semantic search for follow-up questions
            semantic_results = await self.semantic_search.semantic_search(
                contextual_query, max_results=10
            )

            # Enhance with context from initial search
            enhanced_results = self._enhance_follow_up_results(
                semantic_results, initial_search, follow_up
            )

            return {
                "follow_up_question": follow_up,
                "contextual_query": contextual_query,
                "results": enhanced_results,
                "context_utilization": self._assess_context_utilization(
                    initial_search, enhanced_results
                ),
                "relevance_improvement": self._calculate_relevance_improvement(
                    initial_search, enhanced_results
                ),
            }

        except Exception as e:
            logger.error(f"Failed to process follow-up '{follow_up}': {e}")
            return {"follow_up_question": follow_up, "error": str(e), "results": []}

    def _enhance_results_for_chat(
        self, search_results: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        """Enhance search results for chat interface"""
        enhanced = {
            "query": query,
            "summary": search_results.get("summary", {}),
            "grouped_results": {},
            "chat_suggestions": [],
            "quick_actions": [],
        }

        # Process grouped results
        grouped_results = search_results.get("grouped_results", {})
        for result_type, results in grouped_results.items():
            enhanced["grouped_results"][result_type] = self._format_results_for_chat(
                results, result_type
            )

        # Generate chat suggestions
        enhanced["chat_suggestions"] = self._generate_chat_suggestions(
            query, search_results
        )

        # Generate quick actions
        enhanced["quick_actions"] = self._generate_quick_actions(query, search_results)

        return enhanced

    def _format_results_for_chat(
        self, results: List[Dict[str, Any]], result_type: str
    ) -> List[Dict[str, Any]]:
        """Format results for chat display"""
        formatted = []

        for result in results:
            formatted_result = {
                "id": result.get("id"),
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "relevance_score": result.get("relevance_score", 0.0),
                "chat_display": self._create_chat_display(result, result_type),
                "metadata": self._extract_chat_metadata(result, result_type),
            }
            formatted.append(formatted_result)

        return formatted

    def _create_chat_display(self, result: Dict[str, Any], result_type: str) -> str:
        """Create a chat-friendly display string for a result"""
        if result_type == "emails":
            return f"📧 **{result.get('title', 'No subject')}**\nFrom: {result.get('sender', 'Unknown')}\n{result.get('snippet', '')}"
        elif result_type == "calendar":
            return (
                f"📅 **{result.get('title', 'No title')}**\n{result.get('snippet', '')}"
            )
        elif result_type == "contacts":
            return f"👤 **{result.get('display_name', 'Unknown')}**\n{result.get('company', '')}"
        elif result_type == "files":
            return (
                f"📁 **{result.get('title', 'No title')}**\n{result.get('snippet', '')}"
            )
        else:
            return (
                f"📄 **{result.get('title', 'No title')}**\n{result.get('snippet', '')}"
            )

    def _extract_chat_metadata(
        self, result: Dict[str, Any], result_type: str
    ) -> Dict[str, Any]:
        """Extract metadata relevant for chat interactions"""
        metadata = {
            "type": result_type,
            "relevance_score": result.get("relevance_score", 0.0),
            "timestamp": result.get("created_at") or result.get("updated_at"),
        }

        if result_type == "emails":
            metadata.update(
                {
                    "sender": result.get("sender"),
                    "thread_id": result.get("thread_id"),
                    "folder": result.get("folder"),
                }
            )
        elif result_type == "calendar":
            metadata.update(
                {
                    "start_time": result.get("start_time"),
                    "attendees": result.get("attendees", []),
                }
            )

        return metadata

    def _generate_chat_suggestions(
        self, query: str, search_results: Dict[str, Any]
    ) -> List[str]:
        """Generate helpful chat suggestions based on search results"""
        suggestions = []

        # Add type-specific suggestions
        grouped_results = search_results.get("grouped_results", {})

        if grouped_results.get("emails"):
            suggestions.append("📧 Show me more emails from this sender")
            suggestions.append("📧 Find related email threads")

        if grouped_results.get("calendar"):
            suggestions.append("📅 Show upcoming related meetings")
            suggestions.append("📅 Find meeting attendees")

        if grouped_results.get("contacts"):
            suggestions.append("👤 Show contact details")
            suggestions.append("👤 Find related communications")

        # Add general suggestions
        suggestions.append("🔍 Refine my search")
        suggestions.append("📊 Show me a summary")

        return suggestions[:5]  # Limit to 5 suggestions

    def _generate_quick_actions(
        self, query: str, search_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate quick action buttons for chat interface"""
        actions = []

        # Add search refinement actions
        actions.append(
            {
                "action": "refine_search",
                "label": "🔍 Refine Search",
                "description": "Narrow down results",
            }
        )

        # Add export actions
        actions.append(
            {
                "action": "export_results",
                "label": "📤 Export Results",
                "description": "Save results to file",
            }
        )

        # Add scheduling actions if calendar events found
        if search_results.get("grouped_results", {}).get("calendar"):
            actions.append(
                {
                    "action": "schedule_meeting",
                    "label": "📅 Schedule Meeting",
                    "description": "Create new calendar event",
                }
            )

        return actions

    def _enhance_follow_up_results(
        self,
        semantic_results: Dict[str, Any],
        initial_search: Dict[str, Any],
        follow_up: str,
    ) -> Dict[str, Any]:
        """Enhance follow-up results with context from initial search"""
        enhanced = {
            "follow_up": follow_up,
            "semantic_results": semantic_results,
            "context_integration": {},
            "improved_relevance": [],
        }

        # Integrate context from initial search
        if semantic_results.get("status") == "success":
            enhanced["context_integration"] = self._integrate_search_context(
                semantic_results, initial_search
            )

            # Improve relevance using context
            enhanced["improved_relevance"] = self._improve_relevance_with_context(
                semantic_results, initial_search
            )

        return enhanced

    def _integrate_search_context(
        self, semantic_results: Dict[str, Any], initial_search: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate context from initial search into follow-up results"""
        context_integration = {
            "original_query_context": initial_search.get("query", ""),
            "result_types_found": list(
                initial_search.get("results", {}).get("grouped_results", {}).keys()
            ),
            "total_initial_results": initial_search.get("total_found", 0),
            "context_utilization_score": 0.0,
        }

        # Calculate context utilization score
        if semantic_results.get("results"):
            semantic_result_types = set()
            for result in semantic_results["results"]:
                if result.get("type"):
                    semantic_result_types.add(result["type"])

            # Check overlap with initial search
            initial_types = set(context_integration["result_types_found"])
            overlap = len(semantic_result_types.intersection(initial_types))
            context_integration["context_utilization_score"] = (
                overlap / len(initial_types) if initial_types else 0.0
            )

        return context_integration

    def _improve_relevance_with_context(
        self, semantic_results: Dict[str, Any], initial_search: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Improve relevance of follow-up results using initial search context"""
        improved_results = []

        if semantic_results.get("status") != "success":
            return improved_results

        initial_context = initial_search.get("results", {}).get("grouped_results", {})

        for result in semantic_results.get("results", []):
            improved_result = result.copy()

            # Boost relevance for results that match initial context
            if result.get("type") in initial_context:
                improved_result["context_boosted_score"] = (
                    result.get("semantic_score", 0.0) * 1.2
                )
                improved_result["context_relevance"] = "high"
            else:
                improved_result["context_boosted_score"] = result.get(
                    "semantic_score", 0.0
                )
                improved_result["context_relevance"] = "medium"

            improved_results.append(improved_result)

        # Sort by improved relevance
        improved_results.sort(
            key=lambda x: x.get("context_boosted_score", 0.0), reverse=True
        )

        return improved_results

    def _calculate_scenario_relevance(self, scenario_result: Dict[str, Any]) -> float:
        """Calculate overall relevance score for a scenario"""
        if not scenario_result.get("initial_search"):
            return 0.0

        initial_search = scenario_result["initial_search"]

        # Base relevance from initial search
        base_relevance = min(
            initial_search.get("total_found", 0) / 10.0, 1.0
        )  # Normalize to 0-1

        # Boost for follow-up quality
        follow_up_quality = 0.0
        if scenario_result.get("follow_up_conversations"):
            successful_follow_ups = sum(
                1
                for f in scenario_result["follow_up_conversations"]
                if not f.get("error")
            )
            follow_up_quality = successful_follow_ups / len(
                scenario_result["follow_up_conversations"]
            )

        # Combine scores
        relevance_score = (base_relevance * 0.7) + (follow_up_quality * 0.3)

        return round(relevance_score, 2)

    def _calculate_performance_metrics(
        self, conversation_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate performance metrics across all scenarios"""
        total_scenarios = len(conversation_scenarios)
        successful_scenarios = sum(
            1 for s in conversation_scenarios if not s.get("error")
        )

        # Calculate average search time
        search_times = [
            s.get("search_time_ms", 0)
            for s in conversation_scenarios
            if s.get("search_time_ms")
        ]
        avg_search_time = sum(search_times) / len(search_times) if search_times else 0

        # Calculate average relevance score
        relevance_scores = [
            s.get("relevance_score", 0.0)
            for s in conversation_scenarios
            if s.get("relevance_score")
        ]
        avg_relevance = (
            sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        )

        return {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "success_rate": (
                (successful_scenarios / total_scenarios) * 100
                if total_scenarios > 0
                else 0
            ),
            "average_search_time_ms": round(avg_search_time, 2),
            "average_relevance_score": round(avg_relevance, 2),
        }

    def _assess_search_quality(
        self, conversation_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess the quality of search results"""
        quality_metrics = {
            "result_coverage": 0.0,
            "relevance_distribution": {},
            "context_utilization": 0.0,
            "follow_up_effectiveness": 0.0,
        }

        if not conversation_scenarios:
            return quality_metrics

        # Calculate result coverage
        total_expected_results = sum(
            len(s.get("expected_results", [])) for s in conversation_scenarios
        )
        total_actual_results = sum(
            s.get("total_results", 0) for s in conversation_scenarios
        )
        quality_metrics["result_coverage"] = min(
            total_actual_results / max(total_expected_results, 1), 1.0
        )

        # Analyze relevance distribution
        relevance_scores = [
            s.get("relevance_score", 0.0)
            for s in conversation_scenarios
            if s.get("relevance_score")
        ]
        if relevance_scores:
            quality_metrics["relevance_distribution"] = {
                "high": len([r for r in relevance_scores if r >= 0.8]),
                "medium": len([r for r in relevance_scores if 0.5 <= r < 0.8]),
                "low": len([r for r in relevance_scores if r < 0.5]),
            }

        # Calculate context utilization
        context_scores = []
        for scenario in conversation_scenarios:
            for follow_up in scenario.get("follow_up_conversations", []):
                if follow_up.get("context_utilization"):
                    context_scores.append(
                        follow_up["context_utilization"].get(
                            "context_utilization_score", 0.0
                        )
                    )

        if context_scores:
            quality_metrics["context_utilization"] = sum(context_scores) / len(
                context_scores
            )

        # Calculate follow-up effectiveness
        total_follow_ups = sum(
            len(s.get("follow_up_conversations", [])) for s in conversation_scenarios
        )
        successful_follow_ups = sum(
            len([f for f in s.get("follow_up_conversations", []) if not f.get("error")])
            for s in conversation_scenarios
        )
        quality_metrics["follow_up_effectiveness"] = (
            successful_follow_ups / total_follow_ups if total_follow_ups > 0 else 0.0
        )

        return quality_metrics

    def _evaluate_user_experience(
        self, conversation_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate the overall user experience"""
        ux_metrics = {
            "conversation_flow": 0.0,
            "result_presentation": 0.0,
            "interaction_quality": 0.0,
            "overall_satisfaction": 0.0,
        }

        if not conversation_scenarios:
            return ux_metrics

        # Evaluate conversation flow
        flow_scores = []
        for scenario in conversation_scenarios:
            if scenario.get("initial_search") and scenario.get(
                "follow_up_conversations"
            ):
                # Check if follow-ups build on initial results
                initial_results = scenario["initial_search"].get("total_found", 0)
                follow_up_quality = len(
                    [
                        f
                        for f in scenario["follow_up_conversations"]
                        if not f.get("error")
                    ]
                )
                flow_score = min(follow_up_quality / 3.0, 1.0)  # Normalize to 0-1
                flow_scores.append(flow_score)

        if flow_scores:
            ux_metrics["conversation_flow"] = sum(flow_scores) / len(flow_scores)

        # Evaluate result presentation
        presentation_scores = []
        for scenario in conversation_scenarios:
            if (
                scenario.get("initial_search", {})
                .get("results", {})
                .get("chat_suggestions")
            ):
                # Check if results include helpful suggestions and actions
                suggestions_count = len(
                    scenario["initial_search"]["results"]["chat_suggestions"]
                )
                actions_count = len(
                    scenario["initial_search"]["results"]["quick_actions"]
                )
                presentation_score = min(
                    (suggestions_count + actions_count) / 10.0, 1.0
                )
                presentation_scores.append(presentation_score)

        if presentation_scores:
            ux_metrics["result_presentation"] = sum(presentation_scores) / len(
                presentation_scores
            )

        # Calculate overall satisfaction
        ux_metrics["overall_satisfaction"] = (
            ux_metrics["conversation_flow"] * 0.4
            + ux_metrics["result_presentation"] * 0.3
            + ux_metrics["interaction_quality"] * 0.3
        )

        return ux_metrics

    def _generate_result_summary(self, search_results: Dict[str, Any]) -> str:
        """Generate a summary of search results for chat display"""
        try:
            total_found = search_results.get("total_found", 0)
            results = search_results.get("results", [])

            if total_found == 0:
                return "No results found for your query."

            # Group results by type
            result_types = {}
            for result in results:
                result_type = result.get("type", "unknown")
                if result_type not in result_types:
                    result_types[result_type] = []
                result_types[result_type].append(result)

            # Generate summary
            summary_parts = [f"Found {total_found} results:"]
            for result_type, type_results in result_types.items():
                summary_parts.append(
                    f"• {len(type_results)} {result_type.replace('_', ' ')}"
                )

            return " ".join(summary_parts)

        except Exception as e:
            logger.error(f"Error generating result summary: {e}")
            return "Results found but unable to generate summary."

    def _assess_context_utilization(
        self, initial_search: Dict[str, Any], enhanced_results: Dict[str, Any]
    ) -> float:
        """Assess how well context from initial search is utilized in follow-ups"""
        try:
            if not initial_search or not enhanced_results:
                return 0.0

            initial_results = initial_search.get("results", [])
            enhanced_results_list = enhanced_results.get("results", [])

            if not initial_results or not enhanced_results_list:
                return 0.0

            # Check if enhanced results reference or build upon initial results
            context_utilization_score = 0.0

            # Simple heuristic: check if enhanced results have more detail or build on initial
            if len(enhanced_results_list) > len(initial_results):
                context_utilization_score += 0.3

            # Check if enhanced results include follow-up suggestions
            if enhanced_results.get("chat_suggestions"):
                context_utilization_score += 0.4

            # Check if enhanced results include quick actions
            if enhanced_results.get("quick_actions"):
                context_utilization_score += 0.3

            return min(context_utilization_score, 1.0)

        except Exception as e:
            logger.error(f"Error assessing context utilization: {e}")
            return 0.0

    def _calculate_relevance_improvement(
        self, initial_search: Dict[str, Any], enhanced_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate how much relevance has improved from initial search to enhanced results"""
        try:
            if not initial_search or not enhanced_results:
                return {
                    "improvement_score": 0.0,
                    "relevance_gain": 0.0,
                    "result_enhancement": 0.0,
                    "context_enhancement": 0.0,
                }

            initial_results = initial_search.get("results", [])
            enhanced_results_list = enhanced_results.get("results", [])

            if not initial_results or not enhanced_results_list:
                return {
                    "improvement_score": 0.0,
                    "relevance_gain": 0.0,
                    "result_enhancement": 0.0,
                    "context_enhancement": 0.0,
                }

            # Calculate base metrics
            initial_count = len(initial_results)
            enhanced_count = len(enhanced_results_list)

            # Result enhancement: how many more results we got
            result_enhancement = max(
                0, (enhanced_count - initial_count) / max(initial_count, 1)
            )

            # Context enhancement: additional features like suggestions and actions
            context_enhancement = 0.0
            if enhanced_results.get("chat_suggestions"):
                context_enhancement += 0.3
            if enhanced_results.get("quick_actions"):
                context_enhancement += 0.3
            if enhanced_results.get("grouped_results"):
                context_enhancement += 0.4

            # Relevance gain: improvement in result quality
            initial_relevance = sum(
                r.get("relevance_score", 0.0) for r in initial_results
            ) / max(len(initial_results), 1)
            enhanced_relevance = sum(
                r.get("relevance_score", 0.0) for r in enhanced_results_list
            ) / max(len(enhanced_results_list), 1)
            relevance_gain = max(0, enhanced_relevance - initial_relevance)

            # Overall improvement score
            improvement_score = (
                (result_enhancement * 0.3)
                + (context_enhancement * 0.4)
                + (relevance_gain * 0.3)
            )

            return {
                "improvement_score": round(improvement_score, 3),
                "relevance_gain": round(relevance_gain, 3),
                "result_enhancement": round(result_enhancement, 3),
                "context_enhancement": round(context_enhancement, 3),
            }

        except Exception as e:
            logger.error(f"Error calculating relevance improvement: {e}")
            return {
                "improvement_score": 0.0,
                "relevance_gain": 0.0,
                "result_enhancement": 0.0,
                "context_enhancement": 0.0,
            }


async def main():
    """Main function for running the Vespa chat demo"""
    import argparse

    parser = argparse.ArgumentParser(description="Run Vespa-powered chat demo")
    parser.add_argument(
        "--vespa-endpoint", default="http://localhost:8080", help="Vespa endpoint"
    )
    parser.add_argument("--demo-user-id", default="demo_user_1", help="Demo user ID")
    parser.add_argument("--output-file", help="Output file for demo results")

    args = parser.parse_args()

    # Demo configuration
    config = {"vespa_endpoint": args.vespa_endpoint, "demo_user_id": args.demo_user_id}

    # Create and run demo with proper resource cleanup
    try:
        async with VespaChatDemo(config) as demo:
            results = await demo.run_chat_demo()

            # Print summary
            print("\n" + "=" * 60)
            print("VESPA CHAT DEMO RESULTS SUMMARY")
            print("=" * 60)
            print(f"Status: {results['status']}")

            if results["status"] == "completed":
                performance = results.get("performance_metrics", {})
                print(
                    f"Scenarios: {performance.get('successful_scenarios', 0)}/{performance.get('total_scenarios', 0)} successful"
                )
                print(f"Success Rate: {performance.get('success_rate', 0):.1f}%")
                print(
                    f"Average Search Time: {performance.get('average_search_time_ms', 0):.2f}ms"
                )
                print(
                    f"Average Relevance: {performance.get('average_relevance_score', 0):.2f}"
                )

                search_quality = results.get("search_quality", {})
                print(
                    f"Result Coverage: {search_quality.get('result_coverage', 0):.1%}"
                )
                print(
                    f"Context Utilization: {search_quality.get('context_utilization', 0):.1%}"
                )

                ux = results.get("user_experience", {})
                print(f"Overall Satisfaction: {ux.get('overall_satisfaction', 0):.1%}")

            print("=" * 60)

            # Save results to file
            if args.output_file:
                with open(args.output_file, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\nDetailed results saved to: {args.output_file}")

            return results

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
