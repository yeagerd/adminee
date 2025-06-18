"""
CoordinatorAgent - Main orchestrator for the multi-agent workflow system.

This agent serves as the central coordinator that:
- Receives user requests
- Determines which specialized agent should handle the request
- Coordinates between agents
- Provides final responses to users

Part of the multi-agent workflow system.
"""

import logging
from typing import List

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager

logger = logging.getLogger(__name__)


async def analyze_user_request(ctx: Context, user_request: str, analysis: str) -> str:
    """Analyze and record the user's request for tracking and coordination."""
    logger.info(f"🧠 Coordinator: Analyzing request - '{user_request}'")
    logger.info(f"📋 Analysis: {analysis}")

    current_state = await ctx.get("state", {})
    if "request_analysis" not in current_state:
        current_state["request_analysis"] = {}

    current_state["request_analysis"]["original_request"] = user_request
    current_state["request_analysis"]["analysis"] = analysis
    current_state["request_analysis"]["status"] = "analyzing"

    await ctx.set("state", current_state)
    return f"Request analyzed: {analysis}"


async def summarize_findings(ctx: Context, summary: str) -> str:
    """Summarize findings from all agents for the final response."""
    logger.info("📊 Coordinator: Summarizing findings from all agents")

    current_state = await ctx.get("state", {})

    # Collect information from all agent findings
    calendar_info = current_state.get("calendar_info", {})
    email_info = current_state.get("email_info", {})
    document_info = current_state.get("document_info", {})
    draft_info = current_state.get("draft_info", {})

    # Log what information was gathered
    if calendar_info:
        logger.info(f"📅 Calendar findings: {len(calendar_info)} items")
    if email_info:
        logger.info(f"📧 Email findings: {len(email_info)} items")
    if document_info:
        logger.info(f"📄 Document findings: {len(document_info)} items")
    if draft_info:
        logger.info(f"✏️ Draft actions: {list(draft_info.keys())}")

    findings = {
        "calendar_findings": calendar_info,
        "email_findings": email_info,
        "document_findings": document_info,
        "draft_actions": draft_info,
        "coordinator_summary": summary,
    }

    current_state["final_summary"] = findings
    current_state["request_analysis"]["status"] = "completed"
    await ctx.set("state", current_state)

    logger.info(f"✅ Coordinator: Final summary prepared - {summary}")
    return f"Findings summarized and recorded: {summary}"


class CoordinatorAgent(FunctionAgent):
    """
    Main coordinator agent for the multi-agent workflow system.

    This agent:
    - Receives and analyzes user requests
    - Coordinates between specialized agents
    - Ensures tasks are completed properly
    - Provides comprehensive final responses
    """

    def __init__(
        self,
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        **llm_kwargs,
    ):
        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create coordinator-specific tools
        tools = self._create_coordinator_tools()

        # Initialize FunctionAgent
        super().__init__(
            name="CoordinatorAgent",
            description=(
                "Main coordinator agent that manages the workflow between specialized agents. "
                "Handles user requests, coordinates between CalendarAgent, EmailAgent, "
                "DocumentAgent, and DraftAgent, and provides comprehensive responses."
            ),
            system_prompt=(
                "You are Briefly, a personal assistant. Internally, you are the Coordinator, the main orchestrator of the multi-agent system. "
                "Your role is to:\n"
                "1. Analyze user requests and determine what needs to be done\n"
                "2. Hand off to appropriate specialized agents based on the request type\n"
                "3. Coordinate between agents when multiple types of information are needed\n"
                "4. If the user request is not clear, ask for clarification\n"
                "5. Synthesize information from all agents into comprehensive responses\n"
                "6. Ensure user requests are fully satisfied before responding\n\n"
                "CRITICAL ROUTING RULES - You MUST hand off to the correct agent:\n"
                "- If user wants to READ/VIEW/CHECK calendar → CalendarAgent\n"
                "- If user wants to CREATE/DRAFT/MAKE calendar event → DraftAgent\n"
                "- If user wants to READ/search emails → EmailAgent\n"
                "- If user wants to create/draft/compose email → DraftAgent\n"
                "- If user wants to search documents/notes → DocumentAgent\n"
                "- If user says 'create', 'draft', 'make', 'compose' anything → DraftAgent\n\n"
                "EXAMPLES:\n"
                "- 'create a calendar event' → DraftAgent (NOT CalendarAgent)\n"
                "- 'draft an email' → DraftAgent (NOT EmailAgent)\n"
                "- 'what's on my calendar' → CalendarAgent\n"
                "- 'show me emails' → EmailAgent\n\n"
                "When you receive a request:\n"
                "- Use analyze_user_request to record your analysis\n"
                "- Immediately hand off to the appropriate specialized agent based on the routing rules above\n"
                "- When all agents have completed their work, use summarize_findings to create a comprehensive response\n"
                "- Always be thorough and ensure user needs are fully addressed\n\n"
                "Available agents:\n"
                "- CalendarAgent: READ calendar events, scheduling queries, check availability\n"
                "- EmailAgent: READ emails, search email history, retrieve messages\n"
                "- DocumentAgent: SEARCH documents, notes, and files\n"
                "- DraftAgent: CREATE drafts for emails, calendar events, calendar changes, or any composition task"
            ),
            llm=llm,
            tools=tools,
            can_handoff_to=[
                "CalendarAgent",
                "EmailAgent",
                "DocumentAgent",
                "DraftAgent",
            ],
        )

        logger.info("CoordinatorAgent initialized as main orchestrator")

    def _create_coordinator_tools(self) -> List[FunctionTool]:
        """Create coordinator-specific tools."""
        tools = []

        # Request analysis tool
        analyze_request_tool = FunctionTool.from_defaults(
            fn=analyze_user_request,
            name="analyze_user_request",
            description=(
                "Analyze the user's request and record the analysis. "
                "Use this to understand what the user wants and plan the workflow."
            ),
        )
        tools.append(analyze_request_tool)

        # Summary tool
        summarize_tool = FunctionTool.from_defaults(
            fn=summarize_findings,
            name="summarize_findings",
            description=(
                "Summarize findings from all agents and prepare the final response. "
                "Use this after specialized agents have completed their work."
            ),
        )
        tools.append(summarize_tool)

        return tools


def create_coordinator_agent(
    llm_model: str = "gpt-4.1-nano", llm_provider: str = "openai", **llm_kwargs
) -> CoordinatorAgent:
    """
    Factory function to create a CoordinatorAgent instance.

    Args:
        llm_model: LLM model name
        llm_provider: LLM provider name
        **llm_kwargs: Additional LLM configuration

    Returns:
        Configured CoordinatorAgent instance
    """
    return CoordinatorAgent(
        llm_model=llm_model, llm_provider=llm_provider, **llm_kwargs
    )
