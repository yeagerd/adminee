"""
DocumentAgent - Specialized agent for document and note operations.

This agent handles all document-related queries and operations including:
- Retrieving documents
- Searching notes and documents
- Filtering by various criteria
- Providing document information to other agents

Part of the multi-agent workflow system.
"""

import logging
from typing import List

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import get_documents, get_notes

logger = logging.getLogger(__name__)


async def record_document_info(
    ctx: Context, document_info: str, info_title: str
) -> str:
    """Record document information to the workflow state for other agents to use."""
    logger.info(f"📄 DocumentAgent: Recording document info - {info_title}")
    logger.info(
        f"📋 Document data: {document_info[:300]}{'...' if len(document_info) > 300 else ''}"
    )

    current_state = await ctx.get("state", {})
    if "document_info" not in current_state:
        current_state["document_info"] = {}
    current_state["document_info"][info_title] = document_info
    await ctx.set("state", current_state)

    logger.info(
        f"✅ DocumentAgent: Document information '{info_title}' recorded successfully"
    )

    # MANUALLY TRIGGER HANDOFF BACK TO COORDINATOR
    logger.info("🔄 DocumentAgent: Manually triggering handoff to CoordinatorAgent")
    await ctx.set("next_agent", "CoordinatorAgent")

    return f"Document information '{info_title}' recorded successfully."


class DocumentAgent(FunctionAgent):
    """
    Specialized agent for document and note operations.

    This agent can:
    - Query documents
    - Search notes and documents by various criteria
    - Filter by document type, date ranges, search queries
    - Record document information for other agents
    """

    def __init__(
        self,
        user_id: str,
        llm_model: str = "gpt-4.1-nano",
        llm_provider: str = "openai",
        **llm_kwargs,
    ):
        # Get LLM instance
        llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **llm_kwargs
        )

        # Create document-specific tools with user_id
        tools = self._create_document_tools(user_id)

        # Get current date for context
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Initialize FunctionAgent
        super().__init__(
            name="DocumentAgent",
            description=(
                "Specialized agent for document and note operations. Can retrieve documents, "
                "search notes, filter by document type and criteria, and provide document "
                "information to other agents. Use this agent for any document or note-related queries."
            ),
            system_prompt=(
                "You are the DocumentAgent, specialized in document and note operations. "
                f"CURRENT DATE AND TIME: {current_datetime}\n"
                f"Today's date is {current_date}. Use this for any date-related queries or calculations.\n\n"
                "You can retrieve documents, search notes, and filter by various criteria "
                "like document type, date ranges, search queries, notebooks, and tags. "
                "When you find relevant document or note information, use the record_document_info tool "
                "to save it for other agents to use. Be thorough in your searches and provide detailed "
                "information about documents and notes, including content summaries, dates, and metadata. "
                "Finally, hand off to the CoordinatorAgent to take the next action."
            ),
            llm=llm,
            tools=tools,
            can_handoff_to=["CoordinatorAgent"],
        )

        logger.debug("DocumentAgent initialized with document and note tools")

    def _create_document_tools(self, user_id: str) -> List[FunctionTool]:
        """Create document-specific tools with user_id pre-filled."""
        tools = []

        # Document retrieval tool with user_id pre-filled
        def get_documents_wrapper(**kwargs):
            return get_documents(user_id=user_id, **kwargs)

        get_documents_tool = FunctionTool.from_defaults(
            fn=get_documents_wrapper,
            name="get_documents",
            description=(
                "Retrieve documents from the office service. "
                "Can filter by document type, date range, search query, and maximum results. "
                "The user_id is automatically included in the request."
            ),
        )
        tools.append(get_documents_tool)

        # Note retrieval tool with user_id pre-filled
        def get_notes_wrapper(**kwargs):
            return get_notes(user_id=user_id, **kwargs)

        get_notes_tool = FunctionTool.from_defaults(
            fn=get_notes_wrapper,
            name="get_notes",
            description=(
                "Retrieve notes from the office service. "
                "Can filter by notebook, tag, date range, search query, and maximum results. "
                "The user_id is automatically included in the request."
            ),
        )
        tools.append(get_notes_tool)

        # Record document info tool (with Context support)
        record_document_tool = FunctionTool.from_defaults(
            fn=record_document_info,
            name="record_document_info",
            description=(
                "Record document or note information to share with other agents. "
                "Use this to save important document findings for later use by other agents."
            ),
        )
        tools.append(record_document_tool)

        return tools


def create_document_agent(
    user_id: str,
    llm_model: str = "gpt-4.1-nano",
    llm_provider: str = "openai",
    **llm_kwargs,
) -> DocumentAgent:
    """
    Factory function to create a DocumentAgent instance.

    Args:
        user_id: The ID of the user to fetch documents for
        llm_model: LLM model name
        llm_provider: LLM provider name
        **llm_kwargs: Additional LLM configuration

    Returns:
        Configured DocumentAgent instance
    """
    return DocumentAgent(
        user_id=user_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        **llm_kwargs,
    )
