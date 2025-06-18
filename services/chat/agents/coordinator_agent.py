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
        base_prompt = (
            "You are Briefly, a personal assistant. Internally, you are the Coordinator, the main orchestrator of the multi-agent system. "
            "Your role is to analyze user requests, coordinate specialized agents, and provide comprehensive responses. "
        )

        existing_drafts = CoordinatorAgent._get_existing_drafts(thread_id)

        if existing_drafts:
            # There are existing drafts - enforce one-draft policy
            draft_descriptions = []
            for draft_type, draft_data in existing_drafts.items():
                if draft_type == "email":
                    desc = f"Email draft (To: {draft_data.get('to', 'Not set')}, Subject: {draft_data.get('subject', 'Not set')})"
                elif draft_type == "calendar_event":
                    desc = f"Calendar event draft ('{draft_data.get('title', 'Untitled')}' at {draft_data.get('start_time', 'No time set')})"
                elif draft_type == "calendar_edit":
                    desc = f"Calendar edit draft (Event ID: {draft_data.get('event_id', 'Unknown')})"
                draft_descriptions.append(desc)

            draft_context = (
                f"🚨 EXISTING DRAFT CONTEXT:\n"
                f"This conversation has {len(existing_drafts)} active draft(s):\n"
                f"{''.join([f'- {desc}' for desc in draft_descriptions])}\n\n"
                f"ONE-DRAFT POLICY ENFORCEMENT:\n"
                f"- ONLY ONE DRAFT TYPE ALLOWED PER CONVERSATION\n"
                f"- If user wants to create a NEW draft of a different type:\n"
                f"  * Inform them about the existing draft(s)\n"
                f"  * Ask them to either complete the current draft(s) or delete them first\n"
                f"  * Guide them to use DraftAgent's delete tools: 'delete_draft_email', 'delete_draft_calendar_event', 'delete_draft_calendar_edit'\n"
                f"  * Or suggest using 'clear_all_drafts' to clear everything\n"
                f"- If user wants to MODIFY existing drafts:\n"
                f"  * This is encouraged and allowed - hand off to DraftAgent\n"
                f"  * Use the appropriate DraftAgent tools for updates\n"
                f"- Be helpful but firm about the one-draft policy\n"
                f"- Explain that this prevents confusion and ensures focus\n\n"
            )
        else:
            # No existing drafts - normal operation
            draft_context = (
                "✅ CLEAN DRAFT STATE:\n"
                "No active drafts in this conversation - you can create any type of draft as requested.\n\n"
            )

        routing_rules = (
            "CRITICAL ROUTING RULES - You MUST hand off to the correct agent:\n"
            "- If user wants to read/VIEW/CHECK calendar → CalendarAgent\n"
            "- If user wants to CREATE/DRAFT/MAKE/SCHEDULE calendar event → DraftAgent\n"
            "- If user wants to EDIT/MODIFY existing calendar event → CalendarAgent FIRST (to get event_id), then DraftAgent\n"
            "- If user wants to read/SEARCH/FIND emails → EmailAgent\n"
            "- If user wants to CREATE/DRAFT/COMPOSE/WRITE email → DraftAgent\n"
            "- If user wants to read/SEARCH/FIND documents/notes → DocumentAgent\n"
            "- If user says 'create', 'draft', 'make', 'compose', 'schedule' anything → DraftAgent\n\n"
            "SMART CONTEXT RESOLUTION RULES:\n"
            "- If user asks make a change or edit without referring to a specific calendar event, email, document:\n"
            "  * If an event draft exists: assume the DraftAgent will infer the context and update the draft\n"
            "  * If no draft exists: Ask for clarification about which calendar event to edit\n\n"
            "IMPORTANT: CalendarAgent is READ-ONLY. It cannot create, schedule, or draft anything. "
            "For ANY calendar creation/scheduling, use DraftAgent.\n\n"
            "EXAMPLES:\n"
            "- 'create a calendar event' → DraftAgent (NOT CalendarAgent)\n"
            "- 'schedule a meeting' → DraftAgent (NOT CalendarAgent)\n"
            "- 'draft an email' → DraftAgent (NOT EmailAgent)\n"
            "- 'what's on my calendar' → CalendarAgent\n"
            "- 'show me emails' → EmailAgent\n"
            "- 'change my 3pm meeting to 4pm' → CalendarAgent first (find event), then DraftAgent (edit)\n\n"
        )

        workflow_instructions = (
            "WORKFLOW PROCESS:\n"
            "- Use analyze_user_request to record your analysis\n"
            "- Check for draft conflicts before routing to DraftAgent for new draft creation\n"
            "- Immediately hand off to the appropriate specialized agent based on the routing rules\n"
            "- For calendar event editing: ALWAYS get the event_id from CalendarAgent first, then pass it to DraftAgent\n"
            "- When all agents have completed their work, use summarize_findings to create a comprehensive response\n"
            "- Always be thorough and ensure user needs are fully addressed\n\n"
            "Available agents:\n"
            "- CalendarAgent: READ calendar events, find ID of existing event, check availability\n"
            "- EmailAgent: READ emails, search email history, retrieve messages\n"
            "- DocumentAgent: SEARCH documents, notes, and files\n"
            "- DraftAgent: CREATE drafts for emails, calendar events, calendar changes, or any composition task"
        )

        return base_prompt + draft_context + routing_rules + workflow_instructions

    def __init__(
        self,
        thread_id: int,
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
            tools=tools,
            can_handoff_to=[
                "CalendarAgent",
                "EmailAgent",
                "DocumentAgent",
                "DraftAgent",
            ],
        )

        # Store thread_id using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, "_thread_id", str(thread_id))

        logger.info(
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
    **llm_kwargs,
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
