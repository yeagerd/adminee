"""
EmailAgent - Specialized agent for email operations.

This agent handles all email-related queries and operations including:
- Retrieving emails
- Searching email data
- Filtering emails by various criteria
- Providing email information to other agents

Part of the multi-agent workflow system.
"""

import logging
from typing import Any, Callable, List, Sequence

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import get_emails

logger = logging.getLogger(__name__)


async def record_email_info(ctx: Context, email_info: str, info_title: str) -> str:
    """Record email information to the workflow state for other agents to use."""
    logger.info(f"📧 EmailAgent: Recording email info - {info_title}")
    logger.info(
        f"📋 Email data: {email_info[:300]}{'...' if len(email_info) > 300 else ''}"
    )

    current_state = await ctx.get("state", {})
    if "email_info" not in current_state:
        current_state["email_info"] = {}
    current_state["email_info"][info_title] = email_info
    await ctx.set("state", current_state)

    logger.info(
        f"✅ EmailAgent: Email information '{info_title}' recorded successfully"
    )

    # MANUALLY TRIGGER HANDOFF BACK TO COORDINATOR
    logger.info("🔄 EmailAgent: Manually triggering handoff to CoordinatorAgent")
    await ctx.set("next_agent", "CoordinatorAgent")

    return f"Email information '{info_title}' recorded successfully."


class EmailAgent(FunctionAgent):
    """
    Specialized agent for email operations.

    This agent can:
    - Query emails
    - Search email data by date ranges
    - Filter emails by various criteria (unread, folder, etc.)
    - Record email information for other agents
    """

    def __init__(
        self,
        user_id: str,
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        **llm_kwargs: Any,
    ):
        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create email-specific tools with user_id
        tools: Sequence[Callable[..., Any]] = self._create_email_tools(user_id)

        # Get current date for context
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Initialize FunctionAgent
        super().__init__(
            name="EmailAgent",
            description=(
                "Specialized agent for email retrieval. Can retrieve emails, "
                "search by date ranges, filter by criteria (unread, folder), and provide email "
                "information to other agents. Use this agent for any email-related queries."
            ),
            system_prompt=(
                "You are the EmailAgent, specialized in email retrieval. "
                f"CURRENT DATE AND TIME: {current_datetime}\n"
                f"Today's date is {current_date}. Use this for any date-related queries or calculations.\n\n"
                "You can retrieve emails, search by date ranges, and filter by various criteria "
                "like unread status, folders, and maximum results. "
                "When you find relevant email information, use the record_email_info tool to save it "
                "for other agents to use. Be thorough in your email searches and provide detailed "
                "information about emails, including sender, subject, date, and content summaries. "
                "Finally, hand off to the CoordinatorAgent to take the next action."
            ),
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=["CoordinatorAgent"],
        )

        logger.debug("EmailAgent initialized with email tools")

    def _create_email_tools(self, user_id: str) -> List[FunctionTool]:
        """Create email-specific tools with user_id pre-filled."""
        tools = []

        # Create a wrapper function that includes the user_id
        def get_emails_wrapper(*args: Any, **kwargs: Any) -> Any:
            return get_emails(user_id=user_id, **kwargs)

        get_emails_tool = FunctionTool.from_defaults(
            fn=get_emails_wrapper,
            name="get_emails",
            description=(
                "Retrieve emails from the office service. "
                "Can filter by date range, unread status, folder, and maximum results. "
                "The user_id is automatically included in the request."
            ),
        )
        tools.append(get_emails_tool)

        # Record email info tool (with Context support)
        record_email_tool = FunctionTool.from_defaults(
            fn=record_email_info,
            name="record_email_info",
            description=(
                "Record email information to share with other agents. "
                "Use this to save important email findings for later use by other agents."
            ),
        )
        tools.append(record_email_tool)

        return tools


def create_email_agent(
    user_id: str,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs: Any,
) -> EmailAgent:
    """
    Factory function to create an EmailAgent instance.

    Args:
        user_id: The ID of the user to fetch emails for
        llm_model: LLM model name
        llm_provider: LLM provider name
        **llm_kwargs: Additional LLM configuration

    Returns:
        Configured EmailAgent instance
    """
    return EmailAgent(
        user_id=user_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
