"""
DraftAgent - Specialized agent for drafting operations.

This agent handles all drafting operations including:
- Creating draft emails
- Creating draft calendar events
- Managing drafts (delete, update)

Part of the multi-agent workflow system.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import (
    clear_all_drafts,
    create_draft_calendar_change,
    create_draft_calendar_event,
    create_draft_email,
    delete_draft_calendar_edit,
    delete_draft_calendar_event,
    delete_draft_email,
    get_draft_calendar_event,
    get_draft_email,
    has_draft_calendar_edit,
    has_draft_calendar_event,
    has_draft_email,
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
    - Record draft information for other agents
    - Enforce one active draft per conversation

    Thread ID is managed programmatically - no complex context lookups required.
    """

    @staticmethod
    def _get_existing_drafts(thread_id: str) -> Dict[str, bool]:
        """Get information about existing drafts for the thread."""
        return {
            "email": has_draft_email(thread_id),
            "calendar_event": has_draft_calendar_event(thread_id),
            "calendar_edit": has_draft_calendar_edit(thread_id),
        }

    @staticmethod
    def _get_other_drafts(thread_id: str, besides: str) -> List[str]:
        """Get list of existing draft types other than the specified one.

        Args:
            thread_id: The thread ID to check
            besides: The draft type to exclude (e.g., "email", "calendar_event", "calendar_edit")

        Returns:
            List of draft type names that exist (excluding the 'besides' type)
        """
        existing_drafts = DraftAgent._get_existing_drafts(thread_id)
        other_drafts = []

        for draft_type, exists in existing_drafts.items():
            if draft_type != besides and exists:
                other_drafts.append(draft_type)

        return other_drafts

    @staticmethod
    def _has_any_draft(thread_id: str) -> bool:
        """Check if there are any existing drafts for this thread."""
        return len(DraftAgent._get_existing_drafts(thread_id)) > 0

    @staticmethod
    def _create_context_aware_prompt(thread_id: str) -> str:
        """Create a context-aware system prompt based on existing drafts."""
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Common prefix that can be cached
        base_prompt = (
            "You are the DraftAgent, responsible for creating and managing drafts of emails and calendar events. "
            "Your role is to help users create, edit, and finalize drafts before they are sent or scheduled.\n\n"
            f"CURRENT DATE AND TIME: {current_datetime}\n"
            f"Today's date is {current_date}. When users mention relative dates like 'tomorrow', 'next week', "
            f"'in 3 days', etc., convert them to absolute dates based on today's date.\n\n"
        )

        capabilities = (
            "CAPABILITIES:\n"
            "- Create and edit email drafts\n"
            "- Create and edit calendar event drafts\n"
            "- Modify existing calendar events (with event_id)\n"
            "- Delete current active draft upon request\n"
            "WORKFLOW:\n"
            "- Always ask for clarification if draft requirements are unclear\n"
            "- Provide helpful suggestions for improving drafts\n"
        )

        # Draft-specific context at the end (varies based on state)
        existing_drafts = DraftAgent._get_existing_drafts(thread_id)
        draft_descriptions = []

        if existing_drafts.get("email", False):
            # Get the actual email draft data
            draft_data = get_draft_email(thread_id)
            if draft_data:
                desc = f"Email draft (To: {draft_data.get('to', 'Not set')}, Subject: {draft_data.get('subject', 'Not set')})"
                draft_descriptions.append(desc)

        if existing_drafts.get("calendar_event", False):
            # Get the actual calendar draft data
            draft_data = get_draft_calendar_event(thread_id)
            if draft_data:
                desc = f"Calendar event draft (Title: {draft_data.get('title', 'Not set')}, Start: {draft_data.get('start_time', 'Not set')})"
                draft_descriptions.append(desc)

        if existing_drafts.get("calendar_edit", False):
            # Calendar edit drafts don't have a get function, so just note their existence
            draft_descriptions.append("Calendar edit draft (modifying existing event)")

        if draft_descriptions:
            draft_context = (
                "CURRENT DRAFTS:\n"
                + "\n".join(f"- {desc}" for desc in draft_descriptions)
                + "\n\nYou can edit these existing drafts or help the user finalize them."
            )
        else:
            draft_context = "CLEAN STATE: No active drafts - ready to create new drafts as requested."

        return base_prompt + capabilities + draft_context

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

        # Create draft-specific tools - create them first before we store thread_id
        # We'll pass the thread_id to the tool creation method
        thread_id_str = str(thread_id)
        tools: Sequence[Callable[..., Any]] = self._create_draft_tools(thread_id_str)

        # Create context-aware system prompt based on existing drafts
        context_aware_prompt = self._create_context_aware_prompt(thread_id_str)

        # Initialize FunctionAgent first
        super().__init__(
            name="DraftAgent",
            description=(
                "Specialized agent for creating and managing drafts. Can create draft emails "
                "and calendar events. Enforces one active draft per conversation. "
                "Use this agent when users need to compose, draft, or modify emails and calendar items."
            ),
            system_prompt=context_aware_prompt,
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=["CoordinatorAgent"],
        )
        self._thread_id = str(thread_id)
        logger.debug(f"DraftAgent initialized with thread_id={self._thread_id}")

    @property
    def thread_id(self) -> str:
        """Get the thread_id for this agent."""
        return getattr(self, "_thread_id")

    def _create_draft_tools(self, thread_id: str) -> List[FunctionTool]:
        """Create draft-specific tools that use the stored thread_id directly."""
        tools = []

        # Email drafting tools
        def create_email_draft(
            ctx: Context,
            to: str | None = None,
            subject: str | None = None,
            body: str | None = None,
        ) -> str:  # type: ignore[no-untyped-def]
            """Create or update a draft email using the agent's thread_id."""
            logger.info(
                f"📧 DraftAgent: Creating email draft - To: {to}, Subject: {subject}, Thread: {thread_id}"
            )

            # Check for conflicting draft types and return error instead of auto-deleting
            other_drafts = DraftAgent._get_other_drafts(thread_id, besides="email")
            if other_drafts:
                draft_types = ", ".join(other_drafts)
                return f"Error: Cannot create email draft - {draft_types} draft(s) already exist. Please complete, delete, or cancel the existing draft(s) first."

            result = create_draft_email(thread_id, to, subject, body)

            # Record the draft info and log the result
            if result.get("success"):
                draft_info = (
                    f"Email draft created/updated - To: {to}, Subject: {subject}"
                )
                logger.info(f"📝 DraftAgent: {draft_info}")
                logger.info("✅ DraftAgent: Email draft created successfully")
                # Log the draft content for visibility
                logger.info(
                    f"📝 Draft Email Content:\n  To: {to}\n  Subject: {subject}\n  Body: {body}"
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
                "Create or update a draft email in the current conversation. Provide to, cc, bcc, subject, and body. "
                "The conversation context is automatically handled by the agent."
            ),
        )
        tools.append(create_email_draft_tool)

        def delete_email_draft(ctx: Context) -> str:
            """Delete the draft email for this conversation."""
            logger.info(f"🗑️ DraftAgent: Deleting email draft for thread {thread_id}")
            result = delete_draft_email(thread_id)
            return str(result)

        delete_email_draft_tool = FunctionTool.from_defaults(
            fn=delete_email_draft,
            name="delete_draft_email",
            description="Delete the draft email in the current conversation.",
        )
        tools.append(delete_email_draft_tool)

        # Calendar event drafting tools
        def create_calendar_event_draft(
            ctx: Context,
            title: str | None = None,
            start_time: str | None = None,
            end_time: str | None = None,
            attendees: str | None = None,
            location: str | None = None,
            description: str | None = None,
        ) -> str:  # type: ignore[no-untyped-def]
            """Create or update a draft calendar event using the agent's thread_id."""
            logger.info(
                f"📅 DraftAgent: Creating calendar event draft - Title: {title}, Start: {start_time}, Thread: {thread_id}"
            )

            # Check for conflicting draft types and return error instead of auto-deleting
            other_drafts = DraftAgent._get_other_drafts(
                thread_id, besides="calendar_event"
            )
            if other_drafts:
                draft_types = ", ".join(other_drafts)
                return f"Error: Cannot create calendar event draft - {draft_types} draft(s) already exist. Please complete, delete, or cancel the existing draft(s) first."

            result = create_draft_calendar_event(
                thread_id,
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
                logger.info(f"📝 DraftAgent: {draft_info}")
                logger.info(
                    "✅ DraftAgent: Calendar event draft created/updated successfully"
                )
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
                "Create or update a draft calendar event in the current conversation. Use this for both creating new calendar events AND updating existing calendar event drafts (e.g., changing time, location, attendees). "
                "Provide title, start_time, end_time, attendees, location, and description. The conversation context is automatically handled by the agent."
            ),
        )
        tools.append(create_calendar_event_draft_tool)

        def delete_calendar_event_draft(ctx: Context) -> str:
            """Delete the draft calendar event for this conversation."""
            logger.info(
                f"🗑️ DraftAgent: Deleting calendar event draft for thread {thread_id}"
            )
            result = delete_draft_calendar_event(thread_id)
            return str(result)

        delete_calendar_event_draft_tool = FunctionTool.from_defaults(
            fn=delete_calendar_event_draft,
            name="delete_draft_calendar_event",
            description="Delete the draft calendar event in the current conversation.",
        )
        tools.append(delete_calendar_event_draft_tool)

        # Calendar event editing tool (for existing events in user's calendar)
        def edit_existing_calendar_event(
            ctx: Context,
            event_id: str,
            title: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            attendees: Optional[str] = None,
            location: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create a draft edit for an existing calendar event in the user's actual calendar."""
            logger.info(
                f"📅 DraftAgent: Creating draft edit for calendar event {event_id} - Thread: {thread_id}"
            )

            # Create a draft edit using the llm_tools function
            result = create_draft_calendar_change(
                thread_id=thread_id,
                event_id=event_id,
                change_type="update",
                new_title=title,
                new_start_time=start_time,
                new_end_time=end_time,
                new_attendees=attendees,
                new_location=location,
                new_description=description,
            )

            # Record the draft info and log the result
            if result.get("success"):
                draft_info = f"Calendar event edit draft created for event {event_id}"
                logger.info(f"📝 DraftAgent: {draft_info}")
                logger.info(
                    "✅ DraftAgent: Calendar event edit draft created successfully"
                )
            else:
                logger.warning(
                    f"❌ DraftAgent: Failed to create calendar event edit draft - {result}"
                )

            return str(result)

        edit_calendar_event_tool = FunctionTool.from_defaults(
            fn=edit_existing_calendar_event,
            name="edit_existing_calendar_event",
            description=(
                "Edit an existing calendar event in the user's actual calendar. "
                "Requires event_id and the fields to update (title, start_time, end_time, attendees, location, description). "
                "Use this for events that are already created in the user's calendar, "
                "not for drafts (use create_draft_calendar_event for drafts)."
            ),
        )
        tools.append(edit_calendar_event_tool)

        def delete_calendar_edit_draft(ctx: Context) -> str:
            """Delete the draft calendar event edit for this conversation."""
            logger.info(
                f"🗑️ DraftAgent: Deleting calendar edit draft for thread {thread_id}"
            )
            result = delete_draft_calendar_edit(thread_id)
            return str(result)

        delete_calendar_edit_draft_tool = FunctionTool.from_defaults(
            fn=delete_calendar_edit_draft,
            name="delete_draft_calendar_edit",
            description="Delete the draft calendar event edit in the current conversation.",
        )
        tools.append(delete_calendar_edit_draft_tool)

        # Draft management tools

        def clear_all_conversation_drafts(ctx: Context) -> str:
            """Clear all drafts in the current conversation."""
            logger.info(f"🗑️ DraftAgent: Clearing all drafts for thread {thread_id}")
            result = clear_all_drafts(thread_id)
            return str(result)

        clear_drafts_tool = FunctionTool.from_defaults(
            fn=clear_all_conversation_drafts,
            name="clear_all_drafts",
            description="Clear all drafts (email and calendar) in the current conversation.",
        )
        tools.append(clear_drafts_tool)

        return tools


def create_draft_agent(
    thread_id: int,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs: Any,
) -> DraftAgent:
    """
    Factory function to create a DraftAgent instance.

    Args:
        thread_id: Thread ID for draft operations (required)
        llm_model: LLM model to use
        llm_provider: LLM provider to use
        **llm_kwargs: Additional LLM arguments

    Returns:
        DraftAgent instance
    """
    return DraftAgent(
        thread_id=thread_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
