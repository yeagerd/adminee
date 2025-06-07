# llama_manager.py
"""
Planning agent for chat_service using LiteLLM and llama-index.
Implements agent loop, tool/subagent registration, and token-constrained memory.
"""

from typing import Any, Callable, Dict, List, Optional


class SubAgent:
    def __init__(self, name: str, run: Callable):
        self.name = name
        self.run = run

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


class Tool:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class PlanningAgent:
    def __init__(
        self,
        model: Any,
        memory: Any,
        tools: Optional[List[Tool]] = None,
        subagents: Optional[List[SubAgent]] = None,
    ):
        self.model = model
        self.memory = memory
        self.tools = {tool.name: tool for tool in (tools or [])}
        self.subagents = {agent.name: agent for agent in (subagents or [])}
        self.state: dict = {}

    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def register_subagent(self, agent: SubAgent):
        self.subagents[agent.name] = agent

    def plan(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: integrate llama-index for planning and reasoning
        # For now, just call a tool or subagent if goal matches
        if goal in self.tools:
            result = self.tools[goal](context)
            return {"result": result, "steps": [f"Tool {goal} called"]}
        elif goal in self.subagents:
            result = self.subagents[goal](context)
            return {"result": result, "steps": [f"Subagent {goal} called"]}
        else:
            return {"error": "No tool or subagent found for goal", "steps": []}

    def agent_loop(
        self, goal: str, context: Dict[str, Any], max_steps: int = 5
    ) -> Dict[str, Any]:
        steps = []
        for _ in range(max_steps):
            plan_result = self.plan(goal, context)
            steps.append(plan_result)
            if "result" in plan_result:
                break
        return {"final_result": steps[-1], "all_steps": steps}

    def update_memory(self, new_info: Any):
        # Placeholder: integrate with context module for summarization
        self.memory.append(new_info)

    def get_memory(self):
        # Placeholder: token-constrained memory
        return self.memory
