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
from typing import Any, Callable, List, Sequence

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import _draft_storage

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
    - Enforces one-draft policy across conversations
    """

    @staticmethod
    def _get_existing_drafts(thread_id: str) -> dict:
        """Get all existing drafts for a thread."""
        drafts = {}

        # Check for email draft
        email_key = f"{thread_id}_email"
        if email_key in _draft_storage:
            drafts["email"] = _draft_storage[email_key]

        # Check for calendar event draft
        calendar_key = f"{thread_id}_calendar_event"
        if calendar_key in _draft_storage:
            drafts["calendar_event"] = _draft_storage[calendar_key]

        # Check for calendar edit draft
        calendar_edit_key = f"{thread_id}_calendar_edit"
        if calendar_edit_key in _draft_storage:
            drafts["calendar_edit"] = _draft_storage[calendar_edit_key]

        return drafts

    @staticmethod
    def _create_context_aware_prompt(thread_id: str) -> str:
        """Create a context-aware system prompt based on existing drafts."""
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Common prefix that can be cached
        base_prompt = (
            "You are Briefly, a personal assistant and coordinator of specialized agents. "
            "Your role is to analyze user requests, coordinate between agents as needed, "
            "and synthesize comprehensive responses.\n\n"
            f"CURRENT DATE AND TIME: {current_datetime}\n"
            f"Today's date is {current_date}. Use this for any date-related queries or calculations.\n\n"
        )

        coordination_principles = (
            "COORDINATION PRINCIPLES:\n"
            "- Think about what information is needed to fulfill the user's request\n"
            "- Coordinate multiple agents when necessary (e.g., check availability before scheduling)\n"
            "- Use appropriate agents for their specialized capabilities\n"
            "- Synthesize responses from multiple agents into coherent answers\n"
            "- Always maintain context and provide helpful, actionable responses\n\n"
            "AVAILABLE AGENTS:\n"
            "- CalendarAgent: Calendar operations, availability checking, event management\n"
            "- EmailAgent: Email composition, sending, and management\n"
            "- DocumentAgent: Document creation, editing, note-taking\n"
            "- DraftAgent: Draft management (email/calendar), editing, completion\n\n"
        )

        # Import here to avoid circular dependency
        from services.chat.agents.draft_agent import DraftAgent

        # Check for existing drafts using the helper
        has_drafts = bool(DraftAgent._get_existing_drafts(thread_id))

        if has_drafts:
            # Static prompt for when drafts exist
            draft_context = (
                "🚨 ACTIVE DRAFT DETECTED:\n"
                "This conversation has an active draft that need attention.\n\n"
                "DISAMBIGUATION LOGIC:\n"
                "- If user refers to 'it', 'this', 'the draft', 'the event', 'the meeting', or similar generic terms → likely referring to ACTIVE DRAFT\n"
                "- If user uses vague edit requests like 'change the time', 'update the title' → likely about ACTIVE DRAFT\n"
                "- If user specifies existing events with details like 'my 3pm meeting', 'tomorrow's call with John' → consider if its likely the ACTIVE DRAFT or a different, existing calendar event\n"
                "- If user wants to schedule/create something new while an ACTIVE DRAFT exists → apply one-draft policy\n\n"
                "ONE-DRAFT POLICY (STRICTLY ENFORCED):\n"
                "- Only one active draft per conversation is supported\n"
                "- DraftAgent will return an ERROR if trying to create a different draft type\n"
                "- If user wants to create a DIFFERENT type of draft:\n"
                "  * Explain the one-draft policy and the error from DraftAgent\n"
                "  * Ask: 'Would you like me to delete the current draft and create a new one instead?'\n"
                "  * Only proceed to use the DraftAgent to delete the ACTIVE DRAFT after explicit user confirmation\n"
                "- If user wants to MODIFY existing drafts:\n"
                "  * This is encouraged and allowed - hand off to DraftAgent\n"
                "- Be helpful but firm about the one-draft policy\n"
            )
        else:
            # Static prompt for clean state
            draft_context = (
                "✅ CLEAN STATE:\n"
                "No active drafts in this conversation - you can create any type of draft as requested.\n"
            )

        return base_prompt + coordination_principles + draft_context

    def __init__(
        self,
        thread_id: int,
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        **llm_kwargs: Any,
    ):
        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create coordinator-specific tools
        tools: Sequence[Callable[..., Any]] = self._create_coordinator_tools()

        # Create context-aware system prompt based on existing drafts
        context_aware_prompt = self._create_context_aware_prompt(str(thread_id))

        # Initialize FunctionAgent
        super().__init__(
            name="CoordinatorAgent",
            description=(
                "Main coordinator agent that manages the workflow between specialized agents. "
                "Handles user requests, coordinates between CalendarAgent, EmailAgent, "
                "DocumentAgent, and DraftAgent, and provides comprehensive responses."
            ),
            system_prompt=context_aware_prompt,
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=[
                "CalendarAgent",
                "EmailAgent",
                "DocumentAgent",
                "DraftAgent",
            ],
        )
        self._thread_id = str(thread_id)
        logger.debug(
            f"CoordinatorAgent initialized as main orchestrator with thread_id={self._thread_id}"
        )

    @property
    def thread_id(self) -> str:
        """Get the thread_id for this agent."""
        return getattr(self, "_thread_id")

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
    thread_id: int,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs: Any,
) -> CoordinatorAgent:
    """
    Factory function to create a CoordinatorAgent instance.

    Args:
        thread_id: Thread ID for draft context awareness
        llm_model: LLM model name
        llm_provider: LLM provider name
        **llm_kwargs: Additional LLM configuration

    Returns:
        Configured CoordinatorAgent instance
    """
    return CoordinatorAgent(
        thread_id=thread_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
