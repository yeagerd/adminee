"""
DraftAgent - Specialized agent for drafting operations.

This agent handles all drafting operations including:
- Creating draft emails
- Creating draft calendar events
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
    _draft_storage,
    clear_all_drafts,
    create_draft_calendar_change,
    create_draft_calendar_event,
    create_draft_email,
    delete_draft_calendar_edit,
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
    - Record draft information for other agents
    - Enforce one active draft per conversation

    Thread ID is managed programmatically - no complex context lookups required.
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
    def _has_any_draft(thread_id: str) -> bool:
        """Check if there are any existing drafts for this thread."""
        return len(DraftAgent._get_existing_drafts(thread_id)) > 0

    @staticmethod
    def _create_context_aware_prompt(thread_id: str) -> str:
        """Create a context-aware system prompt based on existing drafts."""
        base_prompt = (
            "You are the DraftAgent, an internal agent specialized in creating and managing drafts. "
            "You work behind the scenes and communicate through the CoordinatorAgent, never directly with users. "
            "You can create draft emails and calendar events, and edit existing calendar events. "
        )

        existing_drafts = DraftAgent._get_existing_drafts(thread_id)

        if existing_drafts:
            # There are existing drafts - provide context for internal decision making
            draft_descriptions = []
            for draft_type, draft_data in existing_drafts.items():
                if draft_type == "email":
                    desc = f"Email draft (To: {draft_data.get('to', 'Not set')}, Subject: {draft_data.get('subject', 'Not set')})"
                elif draft_type == "calendar_event":
                    desc = f"Calendar event draft ('{draft_data.get('title', 'Untitled')}' at {draft_data.get('start_time', 'No time set')})"
                elif draft_type == "calendar_edit":
                    desc = f"Calendar edit draft (Event ID: {draft_data.get('event_id', 'Unknown')})"
                draft_descriptions.append(desc)

            context_prompt = (
                f"EXISTING DRAFT CONTEXT:\n"
                f"Current active draft(s) in this conversation ({len(existing_drafts)}):\n"
                f"{''.join([f'- {desc}' for desc in draft_descriptions])}\n\n"
                f"INTERNAL DRAFT POLICY:\n"
                f"- You can modify/update existing drafts using appropriate tools\n"
                f"- If asked to create a new draft of a different type, you should note potential conflicts\n"
                f"- The CoordinatorAgent will handle one-draft policy enforcement with users\n"
                f"- Focus on executing draft operations as requested\n\n"
            )
        else:
            # No existing drafts - clean state for operations
            context_prompt = (
                "CLEAN SLATE CONTEXT:\n"
                "No active drafts in this conversation.\n"
                "You can create any type of draft as requested.\n\n"
                "DRAFT CREATION:\n"
                "- Execute draft creation operations as requested\n"
                "- Gather all necessary details for complete drafts\n"
                "- Pass results to CoordinatorAgent for user communication\n\n"
            )

        common_rules = (
            "OPERATIONAL GUIDELINES:\n"
            "- For calendar draft updates: Use 'create_draft_calendar_event' (it updates existing drafts)\n"
            "- For existing calendar events in user's calendar: Use 'edit_existing_calendar_event'\n"
            "- Execute requested operations and return results to CoordinatorAgent\n"
            "- Do not communicate directly with users - hand off to CoordinatorAgent\n"
            "- Provide clear status information about draft operations"
        )

        return base_prompt + context_prompt + common_rules

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
        tools = self._create_draft_tools(thread_id_str)

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
            tools=tools,
            can_handoff_to=["CoordinatorAgent"],
        )

        # Store thread_id using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, "_thread_id", thread_id_str)

        logger.info(f"DraftAgent initialized with thread_id={self._thread_id}")

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
            to: Optional[str] = None,
            cc: Optional[str] = None,
            bcc: Optional[str] = None,
            subject: Optional[str] = None,
            body: Optional[str] = None,
        ) -> str:
            """Create or update a draft email using the agent's thread_id."""
            logger.info(
                f"📧 DraftAgent: Creating email draft - To: {to}, Subject: {subject}, Thread: {thread_id}"
            )

            result = create_draft_email(thread_id, to, cc, bcc, subject, body)

            # Record the draft info and log the result
            if result.get("success"):
                draft_info = (
                    f"Email draft created/updated - To: {to}, Subject: {subject}"
                )
                logger.info(f"📝 DraftAgent: {draft_info}")
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
            title: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            attendees: Optional[str] = None,
            location: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create or update a draft calendar event using the agent's thread_id."""
            logger.info(
                f"📅 DraftAgent: Creating calendar event draft - Title: {title}, Start: {start_time}, Thread: {thread_id}"
            )

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
    **llm_kwargs,
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
