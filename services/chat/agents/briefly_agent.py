"""
BrieflyAgent - Single-agent design for Briefly that uses tools directly.

This agent serves as the central intelligence that:
- Receives user requests
- Uses specialized tools directly (no subagents)
- Provides comprehensive responses using Vespa search, web search, and API tools
- Maintains user context and authentication

Part of the single-agent workflow system.
"""

import logging
from typing import Any, Callable, List, Optional, Sequence, Tuple

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.tools import DraftTools, GetTools, UserDataSearchTool, WebTools

logger = logging.getLogger(__name__)


async def analyze_user_request(ctx: Context, user_request: str, analysis: str) -> str:
    """Analyze and record the user's request for tracking and coordination."""
    logger.info(f"🧠 Briefly: Analyzing request - '{user_request}'")
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
    """Summarize findings from all tools for the final response."""
    logger.info("📊 Briefly: Summarizing findings from all tools")

    current_state = await ctx.get("state", {})

    # Collect information from all tool findings
    search_info = current_state.get("search_info", {})
    web_info = current_state.get("web_info", {})
    api_info = current_state.get("api_info", {})
    draft_info = current_state.get("draft_info", {})

    # Log what information was gathered
    if search_info:
        logger.info(f"🔍 Search findings: {len(search_info)} items")
    if web_info:
        logger.info(f"🌐 Web findings: {len(web_info)} items")
    if api_info:
        logger.info(f"🔌 API findings: {len(api_info)} items")
    if draft_info:
        logger.info(f"✏️ Draft actions: {list(draft_info.keys())}")

    findings = {
        "search_findings": search_info,
        "web_findings": web_info,
        "api_findings": api_info,
        "draft_actions": draft_info,
        "briefly_summary": summary,
    }

    current_state["final_summary"] = findings
    current_state["request_analysis"]["status"] = "completed"
    await ctx.set("state", current_state)

    logger.info(f"✅ Briefly: Final summary prepared - {summary}")
    return f"Findings summarized and recorded: {summary}"


class BrieflyAgent(FunctionAgent):
    """
    Single-agent design for Briefly that uses tools directly (no subagents).

    Provides:
    - SearchTools (Vespa-based user data search)
    - WebTools (public web search)
    - GetTools (gateway to service APIs)
    - DraftTools (draft management)
    - Simple analyze/summarize helpers
    """

    def _create_context_aware_prompt(self) -> str:
        """Create a context-aware system prompt with current date/time and thread-specific draft context."""
        from datetime import datetime

        # Generate fresh date/time each time for current context
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get thread-specific draft context
        draft_context = self._get_thread_draft_context()

        base_prompt = (
            f"CURRENT DATE AND TIME: {current_datetime}\n"
            f"Today's date is {current_date}. Use this for any date-related queries or calculations.\n\n"
        )

        # Add draft context if available
        if draft_context:
            base_prompt += f"THREAD CONTEXT:\n{draft_context}\n\n"
        return base_prompt

    def _get_thread_draft_context(self) -> str:
        """Get thread-specific draft context for enhanced awareness."""
        try:
            # Create DraftTools instance to access draft data
            from services.chat.tools import DraftTools

            draft_tools = DraftTools(self._user_id)

            # Get existing drafts for this thread
            drafts = draft_tools.get_draft_data(self._thread_id)

            if not drafts:
                return ""

            context_parts = []
            for draft in drafts:
                draft_type = draft.get("type", "unknown")
                if draft_type == "email":
                    subject = draft.get("subject", "")
                    to = draft.get("to", "")
                    if subject or to:
                        context_parts.append(
                            f"- Email draft: {f'To: {to}' if to else ''}{f' Subject: {subject}' if subject else ''}"
                        )
                elif draft_type == "calendar_event":
                    title = draft.get("title", "")
                    start_time = draft.get("start_time", "")
                    if title or start_time:
                        context_parts.append(
                            f"- Calendar event draft: {f'Title: {title}' if title else ''}{f' Start: {start_time}' if start_time else ''}"
                        )
                elif draft_type == "calendar_edit":
                    change_type = draft.get("change_type", "")
                    if change_type:
                        context_parts.append(f"- Calendar edit draft: {change_type}")

            if context_parts:
                return "Existing drafts in this conversation:\n" + "\n".join(
                    context_parts
                )

            return ""
        except Exception as e:
            logger.debug(f"Could not retrieve draft context: {e}")
            return ""

    def __init__(
        self,
        thread_id: int,
        user_id: str,
        vespa_endpoint: str,
        tools: List[FunctionTool],
        tool_catalog: str,
        llm_model: str = "gpt-5-nano",
        llm_provider: str = "openai",
        search_tools: Optional[UserDataSearchTool] = None,
        **llm_kwargs: Any,
    ) -> None:
        # Ensure we have max_tokens set to handle large tool outputs
        if "max_tokens" not in llm_kwargs:
            llm_kwargs["max_tokens"] = 10000  # Increased from default 2000

        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create base system prompt without dynamic context (will be added dynamically)
        base_system_prompt = (
            "You are Briefly, a single-agent assistant with comprehensive tools.\n\n"
            "CORE TOOLS (always available):\n"
            "- user_data_search: INTELLIGENT search across all your personal data (emails, calendar, contacts, files) - USE THIS FOR ALL SEARCHING EXISTING DATA\n"
            "- web_search: Search the public web for current information - USE THIS FOR EXTERNAL KNOWLEDGE\n"
            "- create_draft_*: Create and manage drafts for emails and calendar events\n\n"
            "SERVICE API TOOLS (invoked via get_tool):\n"
            "- Use get_tool(tool_id, params) to execute.\n"
            "- Use get_tool_info(tool_id) if you need parameter details.\n\n"
            "AVAILABLE get_tool IDS AND DESCRIPTIONS:\n"
            f"{tool_catalog}\n\n"
            "CRITICAL TOOL SELECTION RULES - FOLLOW THESE EXACTLY:\n"
            "1. ANY request to FIND, SEARCH, or GET existing data MUST use user_data_search\n"
            "2. NEVER use get_tool('get_emails') or get_tool('get_calendar_events') for searching\n"
            "3. The get_emails tool does NOT work - emails are in Vespa, use user_data_search instead\n"
            "4. Examples of SEARCH requests (use user_data_search):\n"
            "   - 'find my emails from lulu' → user_data_search('find my emails from lulu')\n"
            "   - 'search my calendar', 'get my documents'\n"
            "   - 'what emails do I have', 'show my meetings', 'find my notes'\n"
            "   - 'search for emails from today', 'look for calendar events'\n"
            "5. Examples of MODIFICATION requests (use get_tool):\n"
            "   - 'create an email', 'update calendar event', 'delete note'\n"
            "   - 'send email', 'book meeting', 'remove appointment'\n\n"
            "The user_data_search tool performs a unified hybrid search across your data.\n\n"
            "Keep responses concise, helpful, and actionable.\n"
        )

        # Call parent constructor with FunctionAgent pattern
        super().__init__(
            name="BrieflyAgent",
            description=(
                "Single-agent Briefly assistant using organized tools: Vespa-backed search, "
                "web search, service APIs, and draft management - all with pre-authenticated user context."
            ),
            system_prompt=base_system_prompt,
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=[],  # No handoffs in single-agent design
        )

        # Store additional components we need
        self._base_system_prompt = base_system_prompt

        # Keep a reference to tools that manage external resources
        self._search_tools: Optional[UserDataSearchTool] = search_tools
        self._thread_id = str(thread_id)
        self._user_id = user_id
        self._vespa_endpoint = vespa_endpoint
        self._tool_catalog = tool_catalog

        # Initialize simple state management instead of problematic Context
        self._state: dict[str, Any] = {}

        # Store tools and base system prompt for the worker functions
        self._tools = tools

        logger.debug(
            f"BrieflyAgent initialized with thread_id={self._thread_id}, user_id={self._user_id}"
        )

    async def cleanup(self) -> None:
        """Release any external resources held by the agent/tools."""
        try:
            if self._search_tools is not None:
                await self._search_tools.cleanup()
                self._search_tools = None
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    @property
    def thread_id(self) -> str:
        """Get the thread ID for API compatibility."""
        return self._thread_id

    def get_current_system_prompt(self) -> str:
        """Get the current system prompt with fresh context."""
        return self._create_context_aware_prompt() + self._base_system_prompt

    def run(
        self,
        user_msg: str | ChatMessage | None = None,
        chat_history: list[ChatMessage] | None = None,
        memory: Any = None,
        ctx: Any = None,
        stepwise: bool = False,
        checkpoint_callback: Any = None,
        max_iterations: int | None = None,
        start_event: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Override run method to inject dynamic system prompt before execution."""
        # Update the agent's system prompt with fresh context
        dynamic_prompt = self.get_current_system_prompt()

        # Set the dynamic prompt on the parent FunctionAgent
        self._system_prompt = dynamic_prompt

        # For now, use a simple approach that doesn't rely on complex workflow
        # This avoids the max_iterations parameter issue
        try:
            # Try to call parent with minimal parameters
            return super().run(user_msg=user_msg, **kwargs)
        except Exception as e:
            logger.warning(f"Parent run method failed, using fallback: {e}")
            # Fallback: return a simple response object
            return type(
                "Response",
                (),
                {"stream_events": lambda: self._fallback_stream_events(user_msg)},
            )()

    async def _load_conversation_history(self, exclude_latest: bool = True) -> None:
        """Load conversation history from database into agent context."""
        try:
            from services.chat import history_manager

            # Get messages from database (get extra to account for exclusion)
            db_messages = await history_manager.get_thread_history(
                int(self._thread_id), limit=101 if exclude_latest else 100
            )

            # Reverse to chronological order (oldest to newest)
            db_messages = list(reversed(db_messages))

            # Exclude the most recent message if requested (it's likely the current user input)
            if (
                exclude_latest
                and db_messages
                and db_messages[-1].user_id == self._user_id
            ):
                db_messages = db_messages[:-1]

            # Convert to context format
            chat_history = []
            for msg in db_messages:
                role = "user" if msg.user_id == self._user_id else "assistant"
                chat_history.append(
                    {
                        "role": role,
                        "content": msg.content,
                    }
                )

            # Store in context state (ensure state dict exists even if initially empty)
            state = self._state.get("state", {})
            if not isinstance(state, dict):
                state = {}
            state["conversation_history"] = chat_history
            self._state["state"] = state

            # Logging to help diagnose history loading behavior
            if chat_history:
                logger.info(
                    f"Loaded {len(chat_history)} conversation messages for thread {self._thread_id}"
                )
                try:
                    logger.debug(
                        "First message: role=%s, content=%s",
                        chat_history[0]["role"],
                        str(chat_history[0]["content"])[:200],
                    )
                    logger.debug(
                        "Last message: role=%s, content=%s",
                        chat_history[-1]["role"],
                        str(chat_history[-1]["content"])[:200],
                    )
                except Exception:
                    # Never let logging break execution
                    pass
            else:
                logger.info(
                    f"No prior conversation history found for thread {self._thread_id}"
                )

        except Exception as e:
            logger.error(f"Failed to load conversation history: {e}")

    async def _fallback_stream_events(self, user_msg: str | ChatMessage | None) -> Any:
        """Fallback streaming method when parent run method fails."""
        try:
            # Handle the case where user_msg might be None or a ChatMessage
            if user_msg is None:
                message_content = (
                    "I understand your request. Let me process that for you."
                )
            elif isinstance(user_msg, str):
                message_content = user_msg
            else:
                # It's a ChatMessage, extract the content
                message_content = (
                    str(user_msg.content)
                    if hasattr(user_msg, "content")
                    else str(user_msg)
                )

            # Simple fallback that yields a basic response
            yield {
                "type": "text",
                "delta": f"I understand you said: {message_content}. Let me process that for you.",
            }
        except Exception as e:
            logger.error(f"Fallback streaming failed: {e}")
            yield {
                "type": "error",
                "delta": f"I apologize, but I encountered an error: {str(e)}",
            }

    def _format_history_for_prompt(self, max_messages: int = 20) -> str:
        """Format recent conversation history into a textual prefix for the LLM."""
        try:
            state = (
                self._state.get("state", {}) if isinstance(self._state, dict) else {}
            )
            history = state.get("conversation_history", [])
            if not isinstance(history, list) or not history:
                logger.info(
                    f"No conversation history found for thread {self._thread_id}"
                )
                return ""

            # Take last N messages for brevity
            recent_history = history[-max_messages:]
            lines: List[str] = ["Conversation so far (most recent last):"]
            for entry in recent_history:
                role = str(entry.get("role", "user")).capitalize()
                content = str(entry.get("content", ""))
                lines.append(f"{role}: {content}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting history for prompt: {e}")
            return ""

    async def achat(self, message: str) -> str:
        """Async chat method for compatibility with API usage."""
        try:
            # Collect all streaming chunks and combine them
            response_chunks = []
            async for chunk in self.astream_chat(message):
                if isinstance(chunk, dict) and "error" in chunk:
                    return chunk["message"]
                response_chunks.append(str(chunk))

            # Combine all chunks into a single response
            full_response = "".join(response_chunks)
            return (
                full_response
                if full_response
                else "I'm sorry, I couldn't process that request."
            )
        except Exception as e:
            logger.error(f"Error in BrieflyAgent chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    async def astream_chat(self, message: str) -> Any:
        """Async streaming chat method for compatibility with API usage."""
        try:
            # Load conversation history before streaming chat (exclude latest to avoid duplication)
            await self._load_conversation_history(exclude_latest=True)

            try:
                history_len = len(
                    (self._state.get("state", {}) or {}).get("conversation_history", [])
                )
            except Exception:
                history_len = 0
            logger.info(
                f"BrieflyAgent: Starting streaming chat (history_messages={history_len}) for message: {message}"
            )

            # Include formatted history as prefix to the user message
            history_prefix = self._format_history_for_prompt()
            combined_message = (
                f"{history_prefix}\n\nUser: {message}" if history_prefix else message
            )
            logger.debug(
                "Including history prefix: %s",
                "yes" if bool(history_prefix) else "no",
            )

            # Try to use the FunctionAgent's run method, but with fallback
            try:
                handler = self.run(user_msg=combined_message)

                # Check if handler has stream_events method
                if hasattr(handler, "stream_events"):
                    async for event in handler.stream_events():
                        if hasattr(event, "delta") and event.delta:
                            yield event.delta
                        elif isinstance(event, dict) and "delta" in event:
                            yield event["delta"]
                        else:
                            # Convert event to string if possible
                            yield str(event)
                else:
                    # Fallback: yield the handler response directly
                    yield str(handler)

            except Exception as run_error:
                logger.warning(f"Run method failed, using fallback: {run_error}")
                # Use fallback streaming
                async for event in self._fallback_stream_events(combined_message):
                    yield event

        except Exception as e:
            logger.error(f"Error in BrieflyAgent streaming chat: {e}")
            yield {
                "error": str(e),
                "message": f"I apologize, but I encountered an error: {str(e)}",
            }

    async def get_draft_data(self) -> list[dict[str, Any]]:
        """Get draft data from the draft tools."""
        try:
            from services.chat.tools.draft_tools import _draft_storage

            drafts = []
            thread_prefix = f"{self._thread_id}_"

            for draft_key, draft_data in _draft_storage.items():
                if draft_key.startswith(thread_prefix):
                    draft_copy = draft_data.copy()
                    draft_copy["thread_id"] = self._thread_id
                    drafts.append(draft_copy)

            return drafts
        except Exception as e:
            logger.error(f"Error getting draft data: {e}")
            return []


def create_briefly_agent_tools(
    vespa_endpoint: str, user_id: str
) -> Tuple[List[FunctionTool], str, UserDataSearchTool]:
    """Create and return tools, tool catalog string, and the SearchTools instance."""
    # Initialize pre-authenticated tools with user context
    search_tools = UserDataSearchTool(vespa_endpoint, user_id)
    web_tools = WebTools()
    get_tools = GetTools(user_id)
    draft_tools = DraftTools(user_id)

    # Create wrapper functions for the tools to make them compatible with FunctionTool
    async def combined_user_data_search_wrapper(
        query: str, max_results: int = 20
    ) -> Any:
        """Delegate user data search to the unified search tool (hybrid)."""
        try:
            return await search_tools.search_all_data(
                query=query, max_results=max_results
            )
        except Exception as e:
            logger.error(f"Error in user data search: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "grouped_results": {},
            }

    async def web_search_wrapper(query: str, max_results: int = 5) -> Any:
        return await web_tools.web_search.search(query=query, max_results=max_results)

    def get_tool_info_wrapper(tool_id: str) -> Any:
        """Get complete API specification for a tool."""
        return get_tools.get_tool.get_tool_info(tool_id)

    def get_tool_execute_wrapper(tool_name: str, params: Optional[dict] = None) -> Any:
        """Execute a named tool with parameters."""
        return get_tools.get_tool.execute(tool_name=tool_name, params=params)

    def create_draft_email_wrapper(
        thread_id: str,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        return draft_tools.create_draft_email(
            thread_id=thread_id, to=to, subject=subject, body=body, **kwargs
        )

    def create_draft_calendar_event_wrapper(
        thread_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        attendees: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        return draft_tools.create_draft_calendar_event(
            thread_id=thread_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            location=location,
            description=description,
            **kwargs,
        )

    def create_draft_calendar_change_wrapper(
        thread_id: str,
        event_id: Optional[str] = None,
        change_type: Optional[str] = None,
        new_title: Optional[str] = None,
        new_start_time: Optional[str] = None,
        new_end_time: Optional[str] = None,
        new_attendees: Optional[str] = None,
        new_location: Optional[str] = None,
        new_description: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        return draft_tools.create_draft_calendar_change(
            thread_id=thread_id,
            event_id=event_id,
            change_type=change_type,
            new_title=new_title,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            new_attendees=new_attendees,
            new_location=new_location,
            new_description=new_description,
            **kwargs,
        )

    # Build tool catalog (only categories intended for get_tool execution)
    catalog_entries: List[tuple[str, str]] = []
    for cat in ["data_retrieval", "draft_management", "utility"]:
        try:
            catalog_entries.extend(get_tools.registry.list_tools_by_category(cat))
        except Exception:
            continue
    tool_catalog = "\n".join(
        [f"- {tool_id}: {desc}" for tool_id, desc in catalog_entries]
    )

    tools: List[FunctionTool] = [
        FunctionTool.from_defaults(
            fn=analyze_user_request,
            name="analyze_user_request",
            description="Analyze the user's request and record the analysis.",
        ),
        FunctionTool.from_defaults(
            fn=summarize_findings,
            name="summarize_findings",
            description="Summarize findings and prepare a final response.",
        ),
        FunctionTool.from_defaults(
            fn=combined_user_data_search_wrapper,
            name="user_data_search",
            description=(
                "Hybrid search across user emails, calendar events, contacts, and files. "
                "Returns grouped results and a concise summary."
            ),
        ),
        FunctionTool.from_defaults(
            fn=web_search_wrapper,
            name="web_search",
            description="Search the public web for general information and current events.",
        ),
        FunctionTool.from_defaults(
            fn=get_tool_info_wrapper,
            name="get_tool_info",
            description="Get complete API specification for a named tool including parameters, examples, and return format.",
        ),
        FunctionTool.from_defaults(
            fn=get_tool_execute_wrapper,
            name="get_tool",
            description=(
                "Execute a named tool (e.g., get_calendar_events, get_notes, get_documents) with parameters.\n"
                "Available tool_ids (via get_tool):\n"
                f"{tool_catalog}\n\n"
                "Do NOT use for searching. For any find/search/get queries over existing data, use user_data_search."
            ),
        ),
        FunctionTool.from_defaults(
            fn=create_draft_email_wrapper,
            name="create_draft_email",
            description="Create or update an email draft for the current thread.",
        ),
        FunctionTool.from_defaults(
            fn=create_draft_calendar_event_wrapper,
            name="create_draft_calendar_event",
            description="Create or update a calendar event draft for the current thread.",
        ),
        FunctionTool.from_defaults(
            fn=create_draft_calendar_change_wrapper,
            name="create_draft_calendar_change",
            description="Create a draft calendar change/edit for an existing event.",
        ),
    ]

    return tools, tool_catalog, search_tools


def create_briefly_agent(
    thread_id: int,
    user_id: str,
    vespa_endpoint: str,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs: Any,
) -> BrieflyAgent:
    """Create a new BrieflyAgent instance with pre-authenticated tools."""
    tools, tool_catalog, search_tools = create_briefly_agent_tools(
        vespa_endpoint, user_id
    )
    agent = BrieflyAgent(
        thread_id=thread_id,
        user_id=user_id,
        vespa_endpoint=vespa_endpoint,
        tools=tools,
        tool_catalog=tool_catalog,
        llm_model=llm_model,
        llm_provider=llm_provider,
        search_tools=search_tools,
        **llm_kwargs,
    )
    return agent
