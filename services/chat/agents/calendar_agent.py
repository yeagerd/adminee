"""
CalendarAgent - Specialized agent for calendar operations.

This agent handles all calendar-related queries and operations including:
- Retrieving calendar events
- Searching calendar data
- Providing calendar information to other agents

Part of the multi-agent workflow system.
"""

import logging
from typing import List

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import get_calendar_events

logger = logging.getLogger(__name__)


async def record_calendar_info(
    ctx: Context, calendar_info: str, info_title: str
) -> str:
    """Record calendar information to the workflow state for other agents to use."""
    logger.info(f"📅 CalendarAgent: Recording calendar info - {info_title}")
    logger.info(f"📋 Calendar data: {calendar_info[:300]}{'...' if len(calendar_info) > 300 else ''}")
    
    current_state = await ctx.get("state", {})
    if "calendar_info" not in current_state:
        current_state["calendar_info"] = {}
    current_state["calendar_info"][info_title] = calendar_info
    await ctx.set("state", current_state)
    
    logger.info(f"✅ CalendarAgent: Calendar information '{info_title}' recorded successfully")
    return f"Calendar information '{info_title}' recorded successfully."


class CalendarAgent(FunctionAgent):
    """
    Specialized agent for calendar operations.

    This agent can:
    - Query calendar events
    - Search calendar data by date ranges
    - Filter events by various criteria
    - Record calendar information for other agents
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

        # Create calendar-specific tools
        tools = self._create_calendar_tools()

        # Initialize FunctionAgent
        super().__init__(
            name="CalendarAgent",
            description=(
                "Specialized agent for calendar operations. Can retrieve calendar events, "
                "search by date ranges, filter by criteria, and provide calendar information "
                "to other agents. Use this agent for any calendar-related queries."
            ),
            system_prompt=(
                "You are the CalendarAgent, specialized in calendar operations. "
                "You can retrieve calendar events, search by date ranges, and filter by various criteria. "
                "When you find relevant calendar information, use the record_calendar_info tool to save it "
                "for other agents to use. Be thorough in your calendar searches and provide detailed "
                "information about events, including dates, times, attendees, and locations. "
                "Finally, hand off to the CoordinatorAgent to take the next action."
            ),
            llm=llm,
            tools=tools,
            can_handoff_to=["CoordinatorAgent"],
        )

        logger.info("CalendarAgent initialized with calendar tools")

    def _create_calendar_tools(self) -> List[FunctionTool]:
        """Create calendar-specific tools."""
        tools = []

        # Calendar events retrieval tool
        get_calendar_events_tool = FunctionTool.from_defaults(
            fn=get_calendar_events,
            name="get_calendar_events",
            description=(
                "Retrieve calendar events from the office service. "
                "Can filter by date range, timezone, and provider type. "
                "Requires user_token for authentication."
            ),
        )
        tools.append(get_calendar_events_tool)

        # Record calendar info tool (with Context support)
        record_calendar_tool = FunctionTool.from_defaults(
            fn=record_calendar_info,
            name="record_calendar_info",
            description=(
                "Record calendar information to share with other agents. "
                "Use this to save important calendar findings for later use by other agents."
            ),
        )
        tools.append(record_calendar_tool)

        return tools


def create_calendar_agent(
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs,
) -> CalendarAgent:
    """
    Factory function to create a CalendarAgent instance.

    Args:
        llm_model: LLM model name
        llm_provider: LLM provider name
        **llm_kwargs: Additional LLM configuration

    Returns:
        Configured CalendarAgent instance
    """
    return CalendarAgent(
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
