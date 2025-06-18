"""
DraftAgent - Specialized agent for drafting operations.

This agent handles all drafting operations including:
- Creating draft emails
- Creating draft calendar events
- Creating draft calendar changes
- Managing drafts (delete, update)

Part of the multi-agent workflow system.
"""

import logging
from typing import List, Optional

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import (
    create_draft_calendar_change,
    create_draft_calendar_event,
    create_draft_email,
    delete_draft_calendar_change,
    delete_draft_calendar_event,
    delete_draft_email,
)

logger = logging.getLogger(__name__)


async def record_draft_info(ctx: Context, draft_info: str, draft_type: str) -> str:
    """Record draft information to the workflow state for other agents to use."""
    current_state = await ctx.get("state", {})
    if "draft_info" not in current_state:
        current_state["draft_info"] = {}
    current_state["draft_info"][draft_type] = draft_info
    await ctx.set("state", current_state)
    return f"Draft information for '{draft_type}' recorded successfully."


class DraftAgent(FunctionAgent):
    """
    Specialized agent for drafting operations.

    This agent can:
    - Create and manage draft emails
    - Create and manage draft calendar events
    - Create and manage draft calendar changes
    - Record draft information for other agents

    Thread ID is managed programmatically - no complex context lookups required.
    """

    def __init__(
        self,
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        thread_id: Optional[int] = None,
        **llm_kwargs,
    ):
        # Store thread_id directly - this is the source of truth
        self.thread_id = str(thread_id) if thread_id is not None else "default_thread"

        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create draft-specific tools
        tools = self._create_draft_tools()

        # Initialize FunctionAgent
        super().__init__(
            name="DraftAgent",
            description=(
                "Specialized agent for creating and managing drafts. Can create draft emails, "
                "calendar events, and calendar changes. Use this agent when users need to "
                "compose, draft, or modify emails and calendar items."
            ),
            system_prompt=(
                "You are the DraftAgent, specialized in creating and managing drafts. "
                "You can create draft emails, calendar events, and calendar changes. "
                "When creating drafts, be thorough and ask for all necessary details. "
                "Use the available tools to create, update, or delete drafts as needed. "
                "Record draft information for other agents to reference. "
                "Finally, hand off to the CoordinatorAgent to take the next action."
            ),
            llm=llm,
            tools=tools,
            can_handoff_to=["CoordinatorAgent"],
        )

        logger.info(f"DraftAgent initialized with thread_id={self.thread_id}")

    def _create_draft_tools(self) -> List[FunctionTool]:
        """Create draft-specific tools that use the stored thread_id directly."""
        tools = []

        # Email drafting tools
        def create_email_draft(
            ctx: Context,
            to: Optional[str] = None,
            cc: Optional[str] = None,
            bcc: Optional[str] = None,
            subject: Optional[str] = None,
            body: Optional[str] = None,
        ) -> str:
            """Create or update a draft email using the agent's thread_id."""
            logger.info(
                f"📧 DraftAgent: Creating email draft - To: {to}, Subject: {subject}, Thread: {self.thread_id}"
            )

            result = create_draft_email(self.thread_id, to, cc, bcc, subject, body)

            # Record the draft info and log the result
            if result.get("success"):
                draft_info = (
                    f"Email draft created/updated - To: {to}, Subject: {subject}"
                )
                # Use asyncio.run for the async record_draft_info call
                import asyncio

                asyncio.create_task(record_draft_info(ctx, draft_info, "email"))
                logger.info("✅ DraftAgent: Email draft created successfully")
                # Log the draft content for visibility
                if body:
                    logger.info(
                        f"📝 Draft Email Content:\n  To: {to}\n  Subject: {subject}\n  Body: {body[:200]}{'...' if len(body) > 200 else ''}"
                    )
            else:
                logger.warning(
                    f"❌ DraftAgent: Failed to create email draft - {result}"
                )

            return str(result)

        create_email_draft_tool = FunctionTool.from_defaults(
            fn=create_email_draft,
            name="create_draft_email",
            description=(
                "Create or update a draft email. Provide to, cc, bcc, subject, and body. "
                "The thread_id is automatically handled by the agent."
            ),
        )
        tools.append(create_email_draft_tool)

        def delete_email_draft(ctx: Context) -> str:
            """Delete the draft email for this thread."""
            logger.info(
                f"🗑️ DraftAgent: Deleting email draft for thread {self.thread_id}"
            )
            result = delete_draft_email(self.thread_id)
            return str(result)

        delete_email_draft_tool = FunctionTool.from_defaults(
            fn=delete_email_draft,
            name="delete_draft_email",
            description="Delete the draft email for the current thread.",
        )
        tools.append(delete_email_draft_tool)

        # Calendar event drafting tools
        def create_calendar_event_draft(
            ctx: Context,
            title: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            attendees: Optional[str] = None,
            location: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create or update a draft calendar event using the agent's thread_id."""
            logger.info(
                f"📅 DraftAgent: Creating calendar event draft - Title: {title}, Start: {start_time}, Thread: {self.thread_id}"
            )

            result = create_draft_calendar_event(
                self.thread_id,
                title,
                start_time,
                end_time,
                attendees,
                location,
                description,
            )

            # Record the draft info and log the result
            if result.get("success"):
                draft_info = f"Calendar event draft created/updated - Title: {title}, Start: {start_time}"
                import asyncio

                asyncio.create_task(
                    record_draft_info(ctx, draft_info, "calendar_event")
                )
                logger.info("✅ DraftAgent: Calendar event draft created successfully")
                # Log the draft content for visibility
                logger.info(
                    f"📝 Draft Calendar Event:\n  Title: {title}\n  Start: {start_time}\n  End: {end_time}\n  Location: {location}"
                )
            else:
                logger.warning(
                    f"❌ DraftAgent: Failed to create calendar event draft - {result}"
                )

            return str(result)

        create_calendar_event_draft_tool = FunctionTool.from_defaults(
            fn=create_calendar_event_draft,
            name="create_draft_calendar_event",
            description=(
                "Create or update a draft calendar event. Provide title, start_time, end_time, "
                "attendees, location, and description. The thread_id is automatically handled by the agent."
            ),
        )
        tools.append(create_calendar_event_draft_tool)

        def delete_calendar_event_draft(ctx: Context) -> str:
            """Delete the draft calendar event for this thread."""
            logger.info(
                f"🗑️ DraftAgent: Deleting calendar event draft for thread {self.thread_id}"
            )
            result = delete_draft_calendar_event(self.thread_id)
            return str(result)

        delete_calendar_event_draft_tool = FunctionTool.from_defaults(
            fn=delete_calendar_event_draft,
            name="delete_draft_calendar_event",
            description="Delete the draft calendar event for the current thread.",
        )
        tools.append(delete_calendar_event_draft_tool)

        # Calendar change drafting tools
        def create_calendar_change_draft(
            ctx: Context,
            event_id: Optional[str] = None,
            change_type: Optional[str] = None,
            new_title: Optional[str] = None,
            new_start_time: Optional[str] = None,
            new_end_time: Optional[str] = None,
            new_attendees: Optional[str] = None,
            new_location: Optional[str] = None,
            new_description: Optional[str] = None,
        ) -> str:
            """Create or update a draft calendar change using the agent's thread_id."""
            logger.info(
                f"📅 DraftAgent: Creating calendar change draft - Event: {event_id}, Type: {change_type}, Thread: {self.thread_id}"
            )

            result = create_draft_calendar_change(
                self.thread_id,
                event_id,
                change_type,
                new_title,
                new_start_time,
                new_end_time,
                new_attendees,
                new_location,
                new_description,
            )

            # Record the draft info
            if result.get("success"):
                draft_info = f"Calendar change draft created/updated - Event ID: {event_id}, Type: {change_type}"
                import asyncio

                asyncio.create_task(
                    record_draft_info(ctx, draft_info, "calendar_change")
                )
                logger.info("✅ DraftAgent: Calendar change draft created successfully")
            else:
                logger.warning(
                    f"❌ DraftAgent: Failed to create calendar change draft - {result}"
                )

            return str(result)

        create_calendar_change_draft_tool = FunctionTool.from_defaults(
            fn=create_calendar_change_draft,
            name="create_draft_calendar_change",
            description=(
                "Create or update a draft calendar change. Provide event_id, change_type, and any "
                "new values to change. The thread_id is automatically handled by the agent."
            ),
        )
        tools.append(create_calendar_change_draft_tool)

        def delete_calendar_change_draft(ctx: Context) -> str:
            """Delete the draft calendar change for this thread."""
            logger.info(
                f"🗑️ DraftAgent: Deleting calendar change draft for thread {self.thread_id}"
            )
            result = delete_draft_calendar_change(self.thread_id)
            return str(result)

        delete_calendar_change_draft_tool = FunctionTool.from_defaults(
            fn=delete_calendar_change_draft,
            name="delete_draft_calendar_change",
            description="Delete the draft calendar change for the current thread.",
        )
        tools.append(delete_calendar_change_draft_tool)

        return tools


def create_draft_agent(
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    thread_id: Optional[int] = None,
    **llm_kwargs,
) -> DraftAgent:
    """
    Factory function to create a DraftAgent instance.

    Args:
        llm_model: LLM model to use
        llm_provider: LLM provider to use
        thread_id: Thread ID for draft operations
        **llm_kwargs: Additional LLM arguments

    Returns:
        DraftAgent instance
    """
    return DraftAgent(
        llm_model=llm_model,
        llm_provider=llm_provider,
        thread_id=thread_id,
        **llm_kwargs,
    )
