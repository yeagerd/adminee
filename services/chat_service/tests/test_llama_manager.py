from services.chat_service.llama_manager import PlanningAgent, SubAgent, Tool


def dummy_tool(context):
    return f"tool called with {context}"


def dummy_subagent(context):
    return f"subagent called with {context}"


def test_tool_registration_and_call():
    agent = PlanningAgent(model=None, memory=[], tools=[], subagents=[])
    tool = Tool("calendar", dummy_tool)
    agent.register_tool(tool)
    result = agent.plan("calendar", {"foo": "bar"})
    assert "result" in result
    assert "tool called" in result["result"]


def test_subagent_registration_and_call():
    agent = PlanningAgent(model=None, memory=[], tools=[], subagents=[])
    subagent = SubAgent("email", dummy_subagent)
    agent.register_subagent(subagent)
    result = agent.plan("email", {"baz": 123})
    assert "result" in result
    assert "subagent called" in result["result"]


def test_agent_loop_stops_on_result():
    agent = PlanningAgent(model=None, memory=[], tools=[], subagents=[])
    tool = Tool("calendar", dummy_tool)
    agent.register_tool(tool)
    loop_result = agent.agent_loop("calendar", {"foo": "bar"}, max_steps=3)
    assert "final_result" in loop_result
    assert "result" in loop_result["final_result"]
    assert len(loop_result["all_steps"]) == 1


def test_plan_no_tool_or_subagent():
    agent = PlanningAgent(model=None, memory=[], tools=[], subagents=[])
    result = agent.plan("unknown", {})
    assert "error" in result


def test_memory_update_and_retrieval():
    agent = PlanningAgent(model=None, memory=[], tools=[], subagents=[])
    agent.update_memory({"msg": "foo"})
    mem = agent.get_memory()
    assert {"msg": "foo"} in mem
