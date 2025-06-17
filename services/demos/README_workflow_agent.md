# WorkflowAgent Demo

This demo shows how to use the new `WorkflowAgent` implementation that integrates LlamaIndex's AgentWorkflow with the existing chat service infrastructure.

## Features

- **LlamaIndex AgentWorkflow Integration**: Uses FunctionAgent and AgentWorkflow
- **Existing Infrastructure**: Leverages ChatAgent, LLM manager, and office tools
- **Streaming Support**: Async streaming responses
- **Context Management**: Serializable context for persistence
- **Memory Management**: Integrates with existing memory blocks

## Usage

### Basic Usage

```python
from services.chat.agents.workflow_agent import WorkflowAgent

# Create agent with direct constructor
agent = WorkflowAgent(
    thread_id=123,
    user_id="user123",
    llm_model="gpt-3.5-turbo",
    llm_provider="openai",
    max_tokens=2000,
)

# Chat
response = await agent.chat("Hello!")
print(response)
```

### With Custom Tools

```python
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: sunny, 72°F"

agent = WorkflowAgent(
    thread_id=123,
    user_id="user123",
    llm_model="fake-model",
    llm_provider="fake",
    tools=[get_weather],
)

response = await agent.chat("What's the weather in Paris?")
```

### Streaming Responses

```python
async for event in agent.stream_chat("Tell me a story"):
    if hasattr(event, 'delta') and event.delta:
        print(event.delta, end="", flush=True)
```

### Context Management

```python
# Save context
context_data = await agent.save_context()

# Load context in new agent
new_agent = WorkflowAgent(
    thread_id=123,
    user_id="user123",
    llm_model="gpt-3.5-turbo",
    llm_provider="openai",
)
await new_agent.load_context(context_data)
```

## Running the Demo

```bash
python services/demos/workflow_agent_demo.py
```

## Key Differences from Factory Function

Previously, we had a `create_workflow_agent()` factory function, but it was removed because:

1. It was just a pass-through wrapper to the constructor
2. The constructor already had the same defaults
3. It added unnecessary complexity without benefits

Now you can use the `WorkflowAgent` constructor directly, which is cleaner and more Pythonic.

## Constructor Parameters

- `thread_id`: Thread identifier
- `user_id`: User identifier
- `llm_model`: LLM model name
- `llm_provider`: LLM provider name
- `max_tokens`: Maximum tokens (default: 30000)
- `tools`: List of custom tools (optional)
- `llm_kwargs`: Additional LLM configuration (optional)
- `office_service_url`: Office service URL (default: "http://localhost:8001")
- Other parameters for memory configuration, token management, etc. 