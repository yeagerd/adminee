"""
CalendarAgent - Specialized agent for calendar operations.

This agent handles all calendar-related queries and operations including:
- Retrieving calendar events
- Searching calendar data
- Providing calendar information to other agents

Part of the multi-agent workflow system.
"""

import logging
from typing import Any, Callable, List, Sequence

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
    logger.info(
        f"📋 Calendar data: {calendar_info[:300]}{'...' if len(calendar_info) > 300 else ''}"
    )

    current_state = await ctx.get("state", {})
    if "calendar_info" not in current_state:
        current_state["calendar_info"] = {}
    current_state["calendar_info"][info_title] = calendar_info
    await ctx.set("state", current_state)

    logger.info(
        f"✅ CalendarAgent: Calendar information '{info_title}' recorded successfully"
    )

    # MANUALLY TRIGGER HANDOFF BACK TO COORDINATOR
    logger.info("🔄 CalendarAgent: Manually triggering handoff to CoordinatorAgent")
    await ctx.set("next_agent", "CoordinatorAgent")

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
        user_id: str,
        user_timezone: str = "UTC",
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        **llm_kwargs: Any,
    ):

        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create calendar-specific tools with user_id and timezone
        tools: Sequence[Callable[..., Any]] = self._create_calendar_tools(
            user_id, user_timezone
        )

        # Get current date for context
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get current date for context
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Initialize FunctionAgent
        super().__init__(
            name="CalendarAgent",
            description=(
                "Specialized agent for calendar operations. Can create, update, and delete events, "
                "search for events, and provide calendar information to other agents. Use this agent for any calendar-related queries."
            ),
            system_prompt=(
                "You are the CalendarAgent, specialized in calendar operations. "
                f"CURRENT DATE AND TIME: {current_datetime}\n"
                f"Today's date is {current_date}. Use this for any date-related queries or calculations.\n\n"
                "TIMEZONE HANDLING:\n"
                "- When displaying times to users, use the 'display_time' field from calendar events\n"
                "- This field contains properly formatted local times (e.g., '5:00 PM to 5:30 PM')\n"
                "- If display_time is not available, convert UTC times to local timezone\n"
                "- Always use 12-hour format with AM/PM for readability\n"
                "- Use the user's timezone (e.g., 'America/New_York') when calling get_calendar_events\n\n"
                "You can retrieve calendar events, search by date ranges, and filter by various criteria. "
                "When you find relevant calendar information, use the record_calendar_info tool to save it "
                "for other agents to use. Be thorough in your calendar searches and provide detailed "
                "information about events, including dates, times, attendees, and locations. "
                "Always format times in the user's local timezone for better readability. "
                "Finally, hand off to the CoordinatorAgent to take the next action."
            ),
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=["CoordinatorAgent"],
        )

        logger.debug("CalendarAgent initialized with calendar tools")

    def _create_calendar_tools(
        self, user_id: str, user_timezone: str
    ) -> List[FunctionTool]:
        """Create calendar-specific tools."""
        tools = []

        # Create a wrapper function that provides the user_id and default timezone
        def get_calendar_events_with_user_id(
            start_date: str | None = None,
            end_date: str | None = None,
            time_zone: str | None = None,
            providers: str | None = None,
        ) -> Any:
            if not user_id:
                logger.error("User ID not available in calendar agent")
                return {"error": "User ID not available in calendar agent"}

            # If no timezone specified, use the user's timezone preference
            if not time_zone:
                time_zone = user_timezone  # Use user's preferred timezone

            logger.info(f"CalendarAgent: Calling get_calendar_events - user_id: {user_id}, start_date: {start_date}, end_date: {end_date}, time_zone: {time_zone}, providers: {providers}")
            
            result = get_calendar_events(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                time_zone=time_zone,
                providers=providers,
            )
            
            logger.info(f"CalendarAgent: get_calendar_events result - user_id: {user_id}, has_error: {'error' in result}, events_count: {len(result.get('events', [])) if 'events' in result else 0}")
            
            return result

        # Calendar events retrieval tool
        get_calendar_events_tool = FunctionTool.from_defaults(
            fn=get_calendar_events_with_user_id,
            name="get_calendar_events",
            description=(
                "Retrieve calendar events from the office service. "
                "Can filter by date range, timezone, and provider type. "
                "Parameters: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), "
                "time_zone (e.g., 'America/New_York'), providers (comma-separated: 'google,microsoft')"
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
