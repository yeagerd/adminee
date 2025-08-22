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
from typing import Any, Callable, List, Optional, Sequence

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.tools import DraftTools, GetTools, SearchTools, WebTools

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

    def __init__(
        self,
        thread_id: int,
        user_id: str,
        vespa_endpoint: str,
        tools: List[FunctionTool],
        llm_model: str = "gpt-5-nano",
        llm_provider: str = "openai",
        **llm_kwargs: Any,
    ) -> None:
        # Ensure we have max_tokens set to handle large tool outputs
        if "max_tokens" not in llm_kwargs:
            llm_kwargs["max_tokens"] = 10000  # Increased from default 2000

        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        system_prompt = (
            "You are Briefly, a single-agent assistant with comprehensive tools.\n\n"
            "CORE TOOLS (always available):\n"
            "- user_data_search: INTELLIGENT search across all your personal data (emails, calendar, contacts, files) - USE THIS FOR ALL SEARCHING EXISTING DATA\n"
            "- web_search: Search the public web for current information - USE THIS FOR EXTERNAL KNOWLEDGE\n"
            "- create_draft_*: Create and manage drafts for emails and calendar events\n\n"
            "DISCOVERABLE TOOLS (use tool discovery workflow):\n"
            "- list_get_tools: Discover available service API tools\n"
            "- get_tool_info: Get complete API specification for any tool\n"
            "- get_tool: Execute discovered tools with proper parameters\n\n"
            "TOOL DISCOVERY WORKFLOW:\n"
            "1. Use list_get_tools to see what tools are available\n"
            "2. Use get_tool_info(tool_id) to get complete API documentation\n"
            "3. Use get_tool(tool_id, params) to execute with proper parameters\n\n"
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
            "The user_data_search tool automatically chooses the best search method:\n"
            "- General search for most queries\n"
            "- Semantic search for conceptual queries\n"
            "- Vespa search when source types are specified\n"
            "- You can override with search_type parameter: 'general', 'semantic', 'vespa', or 'auto'\n\n"
            "Keep responses concise, helpful, and actionable.\n"
        )

        # Call parent constructor with FunctionAgent pattern
        super().__init__(
            name="BrieflyAgent",
            description=(
                "Single-agent Briefly assistant using organized tools: Vespa-backed search, "
                "web search, service APIs, and draft management - all with pre-authenticated user context."
            ),
            system_prompt=system_prompt,
            llm=llm,
            tools=tools,  # type: ignore[arg-type]
            can_handoff_to=[],  # No handoffs in single-agent design
        )

        # Store additional components we need
        self._system_prompt = system_prompt
        self._thread_id = str(thread_id)
        self._user_id = user_id
        self._vespa_endpoint = vespa_endpoint

        # Initialize context for conversation history
        self._context = Context(self)

        # Store tools and system prompt for the worker functions
        self._tools = tools
        self._system_prompt = system_prompt

        logger.debug(
            f"BrieflyAgent initialized with thread_id={self._thread_id}, user_id={self._user_id}"
        )

    @property
    def thread_id(self) -> str:
        """Get the thread ID for API compatibility."""
        return self._thread_id

    async def _load_conversation_history(self) -> None:
        """Load conversation history from database into agent context."""
        try:
            from services.chat import history_manager

            # Get messages from database
            db_messages = await history_manager.get_thread_history(
                int(self._thread_id), limit=100
            )

            # Reverse to chronological order (oldest to newest)
            db_messages = list(reversed(db_messages))

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

            # Store in context state
            if self._context and hasattr(self._context, "store"):
                state = await self._context.store.get("state", {})
                if not isinstance(state, dict):
                    state = {}
                state["conversation_history"] = chat_history
                await self._context.store.set("state", state)

                logger.debug(
                    f"Loaded {len(chat_history)} conversation messages into context"
                )

        except Exception as e:
            logger.error(f"Failed to load conversation history: {e}")

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

    async def astream_chat(self, message: str):
        """Async streaming chat method for compatibility with API usage."""
        try:
            # Load conversation history before streaming chat
            await self._load_conversation_history()

            # Use the FunctionAgent's run method with streaming following the correct pattern
            logger.info(f"BrieflyAgent: Starting streaming chat for message: {message}")

            # Create a context for the agent to maintain state
            ctx = Context(self)

            # Get the handler (don't await yet)
            handler = self.run(user_msg=message, ctx=ctx)

            # Import the event types we need to check
            from llama_index.core.agent.workflow import AgentStream, ToolCallResult

            async for event in handler.stream_events():
                if isinstance(event, AgentStream) and event.delta:
                    yield event.delta

            # The final response will be streamed through AgentStream events
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


def create_briefly_agent_tools(vespa_endpoint: str, user_id: str) -> List[FunctionTool]:
    """Create and return all tools for the BrieflyAgent."""
    # Initialize pre-authenticated tools with user context
    search_tools = SearchTools(vespa_endpoint, user_id)
    web_tools = WebTools()
    get_tools = GetTools(user_id)
    draft_tools = DraftTools(user_id)

    # Create wrapper functions for the tools to make them compatible with FunctionTool
    async def combined_user_data_search_wrapper(
        query: str,
        max_results: int = 20,
        search_type: Optional[str] = None,
        source_types: Optional[List[str]] = None,
    ) -> Any:
        """
        Intelligent user data search that combines all search methods.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_type: Optional search type ('general', 'semantic', 'vespa', 'auto')
            source_types: Optional list of source types to filter by (for Vespa search)

        Returns:
            Search results from the appropriate search method
        """
        try:
            # If search_type is specified, use that method
            if search_type == "semantic":
                return await search_tools.semantic_search.semantic_search(
                    query=query, max_results=max_results
                )
            elif search_type == "vespa":
                return await search_tools.vespa_search.search(
                    query=query, max_results=max_results, source_types=source_types
                )
            elif search_type == "general":
                return await search_tools.user_data_search.search_all_data(
                    query=query, max_results=max_results
                )

            # Auto-detect best search method based on query characteristics
            query_lower = query.lower()

            # If source types are specified, prefer Vespa search
            if source_types:
                return await search_tools.vespa_search.search(
                    query=query, max_results=max_results, source_types=source_types
                )

            # If query contains specific data types, use general search
            if any(
                term in query_lower
                for term in ["email", "calendar", "contact", "file", "document"]
            ):
                return await search_tools.user_data_search.search_all_data(
                    query=query, max_results=max_results
                )

            # If query is conceptual/abstract, use semantic search
            if any(
                term in query_lower
                for term in ["about", "related to", "similar to", "like", "concept"]
            ):
                return await search_tools.semantic_search.semantic_search(
                    query=query, max_results=max_results
                )

            # Default to general search for most queries
            return await search_tools.user_data_search.search_all_data(
                query=query, max_results=max_results
            )

        except Exception as e:
            logger.error(f"Error in combined user data search: {e}")
            # Fallback to general search
            return await search_tools.user_data_search.search_all_data(
                query=query, max_results=max_results
            )

    async def web_search_wrapper(query: str, max_results: int = 5) -> Any:
        return await web_tools.web_search.search(query=query, max_results=max_results)

    def get_tool_list_wrapper() -> Any:
        """List available tools for discovery."""
        return get_tools.get_tool.list_tools()

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
                "Intelligent search across all user data types (email, calendar, contacts, files). "
                "Automatically chooses the best search method (general, semantic, or Vespa) based on the query. "
                "Use search_type parameter to specify: 'general', 'semantic', 'vespa', or 'auto' for automatic selection. "
                "Use source_types parameter to filter by specific data sources when using Vespa search."
            ),
        ),
        FunctionTool.from_defaults(
            fn=web_search_wrapper,
            name="web_search",
            description="Search the public web for general information and current events.",
        ),
        FunctionTool.from_defaults(
            fn=get_tool_list_wrapper,
            name="list_get_tools",
            description="List available tools that can be executed via get_tool.",
        ),
        FunctionTool.from_defaults(
            fn=get_tool_list_wrapper,
            name="list_get_tools",
            description="List available tools that can be executed via get_tool.",
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
                "Execute a named tool (e.g., get_calendar_events, get_emails, get_notes, get_documents) with parameters."
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

    return tools


def create_briefly_agent(
    thread_id: int,
    user_id: str,
    vespa_endpoint: str,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs: Any,
) -> BrieflyAgent:
    """Create a new BrieflyAgent instance with pre-authenticated tools."""
    tools = create_briefly_agent_tools(vespa_endpoint, user_id)
    return BrieflyAgent(
        thread_id=thread_id,
        user_id=user_id,
        vespa_endpoint=vespa_endpoint,
        tools=tools,
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
