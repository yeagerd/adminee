# llama_manager.py
"""
Chat agent orchestration layer for chat_service using LiteLLM and llama-index.
Coordinates multiple agents, tool distribution, and sub-agent management.

This layer is responsible for:
- Creating and managing chat agents with modern memory blocks
- Distributing tools between main agent and sub-agents
- Orchestrating multi-agent workflows
- Managing agent lifecycles and coordination

The actual agent implementation with modern memory blocks is in chat_agent.py:
- StaticMemoryBlock: For persistent system information
- FactExtractionMemoryBlock: For extracting facts from conversations
- VectorMemoryBlock: For semantic search over conversation history

TL;DR: Common Memory Block Combinations

Static + Summary + Buffer – use cases needing system prompts, summary, and recent history.
Static + FactExtraction + ChatBuffer – long-term facts + short-term dialogue.
Static + FactExtraction + VectorMemory – combine fact-tracking with semantic retrieval.
VectorMemory Alone – typical RAG pattern.
Static Only – constant system instructions or persona background.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

# Import modules that tests expect to find here for backward compatibility
from services.chat.chat_agent import ChatAgent

logger = logging.getLogger(__name__)


class ChatAgentManager:
    """
    Orchestration layer for managing chat agents, tools, and sub-agents.

    This class coordinates:
    - Main chat agent with modern memory blocks (via ModernChatAgent)
    - Sub-agents for specialized tasks
    - Tool distribution between agents
    - Multi-agent workflow coordination
    """

    def __init__(
        self,
        thread_id: int,
        user_id: str,
        max_tokens: int = 2048,
        tools: Optional[List[Callable]] = None,
        subagents: Optional[List[Callable]] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs or {}

        # Store tools and subagents for orchestration
        self.tools = tools or []
        self.subagents = subagents or []

        # Registry of active agents
        self.active_agents: Dict[str, ChatAgent] = {}
        self.main_agent: Optional[ChatAgent] = None

        # Tool distribution strategy
        self.tool_distribution = self._analyze_tools()

        logger.info(
            f"ChatAgentManager initialized for orchestration - "
            f"user_id={self.user_id}, thread_id={self.thread_id}, "
            f"tools_count={len(self.tools)}, subagents_count={len(self.subagents)}"
        )

    def _analyze_tools(self) -> Dict[str, Any]:
        """
        Analyze tools and determine distribution strategy between main agent and sub-agents.

        Returns:
            Dict mapping agent types to their assigned tools
        """
        distribution: Dict[str, Any] = {"main_agent": [], "specialized_agents": {}}

        # For now, assign all tools to main agent
        # Future: implement sophisticated tool routing based on tool metadata
        distribution["main_agent"] = self.tools.copy()

        # Future: analyze subagents and distribute tools accordingly
        for i, subagent in enumerate(self.subagents):
            agent_name = f"subagent_{i}"
            distribution["specialized_agents"][agent_name] = []

        logger.debug(f"Tool distribution strategy: {distribution}")
        return distribution

    async def _create_main_agent(self) -> ChatAgent:
        """Create the main chat agent with assigned tools."""
        if self.main_agent is None:
            main_tools = self.tool_distribution["main_agent"]
            self.main_agent = ChatAgent(
                thread_id=self.thread_id,
                user_id=self.user_id,
                max_tokens=self.max_tokens,
                tools=main_tools,
                llm_model=self.llm_model,
                llm_provider=self.llm_provider,
                llm_kwargs=self.llm_kwargs,
                # Enable modern memory features by default
                enable_fact_extraction=True,
                enable_vector_memory=True,
            )
            self.active_agents["main"] = self.main_agent
            logger.info("Main agent created with modern memory blocks")

        return self.main_agent

    async def _create_subagents(self) -> Dict[str, ChatAgent]:
        """Create specialized sub-agents for specific tasks."""
        subagents = {}

        for i, subagent_config in enumerate(self.subagents):
            agent_name = f"subagent_{i}"
            if agent_name not in self.active_agents:
                # Create specialized agent with specific tools
                specialized_tools = self.tool_distribution["specialized_agents"].get(
                    agent_name, []
                )

                subagent = ChatAgent(
                    thread_id=self.thread_id,
                    user_id=self.user_id,
                    max_tokens=self.max_tokens,
                    tools=specialized_tools,
                    llm_model=self.llm_model,
                    llm_provider=self.llm_provider,
                    llm_kwargs=self.llm_kwargs,
                    # Sub-agents might have different memory configurations
                    enable_fact_extraction=False,  # Only main agent extracts facts
                    enable_vector_memory=True,  # But they can search history
                )

                self.active_agents[agent_name] = subagent
                subagents[agent_name] = subagent
                logger.info(f"Created {agent_name} with {len(specialized_tools)} tools")

        return subagents

    async def _route_query(self, user_input: str) -> str:
        """
        Determine which agent should handle the query.

        Future: implement sophisticated routing based on:
        - Query intent classification
        - Tool requirements analysis
        - Agent specialization matching

        For now: route everything to main agent
        """
        return "main"

    # Public API methods
    @property
    def llm(self):
        """Access to the main agent's LLM."""
        if self.main_agent:
            return self.main_agent.llm
        return None

    @property
    def agent(self):
        """Access to the main agent."""
        return self.main_agent

    @agent.setter
    def agent(self, value):
        """Set the main agent."""
        self.main_agent = value

    @property
    def memory(self):
        """Access to the main agent's memory."""
        if self.main_agent:
            return self.main_agent.memory
        return None

    async def get_memory(self, user_input: str = "") -> List[Dict[str, Any]]:
        """
        Get memory information from the orchestration layer.
        Aggregates memory from all active agents.
        """
        memory_info = []

        # Ensure main agent exists
        await self._create_main_agent()

        # Get main agent memory
        if self.main_agent:
            main_memory = await self.main_agent.get_memory_info()
            memory_info.append({"agent": "main", "memory": main_memory})

        # Get sub-agent memories
        for agent_name, agent in self.active_agents.items():
            if agent_name != "main":
                agent_memory = await agent.get_memory_info()
                memory_info.append({"agent": agent_name, "memory": agent_memory})

        return memory_info

    async def build_agent(self, user_input: str = "") -> None:
        """Build or rebuild the orchestrated agent system."""
        logger.info("Building orchestrated agent system...")

        # Create main agent
        main_agent = await self._create_main_agent()
        await main_agent.build_agent(user_input)

        # Create sub-agents
        await self._create_subagents()

        # Build all sub-agents
        for agent_name, agent in self.active_agents.items():
            if agent_name != "main":
                await agent.build_agent(user_input)

        logger.info(f"Agent system built with {len(self.active_agents)} active agents")

    async def chat(self, user_input: str) -> str:
        """
        Process a chat message through the orchestrated agent system.

        This method:
        1. Routes the query to the appropriate agent
        2. Coordinates between agents if needed
        3. Returns the final response
        """
        # Ensure agents are built
        if not self.active_agents:
            await self.build_agent(user_input)

        # Route query to appropriate agent
        target_agent = await self._route_query(user_input)

        # For now, always use main agent
        # Future: implement cross-agent coordination
        if target_agent == "main" and self.main_agent:
            response = await self.main_agent.chat(user_input)
            logger.info(f"Main agent handled query, response length: {len(response)}")
            return response
        else:
            # Fallback to main agent
            if self.main_agent:
                return await self.main_agent.chat(user_input)
            else:
                return "Error: No active agents available"


# Example usage:
# manager = ChatAgentManager(
#     thread_id=1,
#     user_id="user1",
#     tools=[calendar_tool, email_tool],
#     subagents=[specialized_agent_config]
# )
# await manager.build_agent()
# reply = await manager.chat("What's on my calendar?")
# print(reply)
