# Multi-Agent Workflow System

This directory contains a comprehensive multi-agent workflow system built on LlamaIndex's AgentWorkflow architecture. The system provides both single-agent and multi-agent modes for handling complex user requests that span multiple domains (calendar, email, documents, drafting).

## Architecture Overview

The multi-agent system follows the pattern described in the [LlamaIndex multi-agent tutorial](https://docs.llamaindex.ai/en/stable/understanding/agent/multi_agent/), with specialized agents for different domains:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  CoordinatorAgent │◄──►│  CalendarAgent  │    │   EmailAgent    │
│   (Orchestrator)  │    │   (Calendar)    │    │    (Email)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    
│ DocumentAgent   │    │   DraftAgent    │    
│ (Docs/Notes)    │    │   (Drafting)    │    
└─────────────────┘    └─────────────────┘    
```

## Agent Responsibilities

### CoordinatorAgent (`coordinator_agent.py`)
- **Role**: Main orchestrator and entry point
- **Responsibilities**:
  - Analyze user requests
  - Determine which specialized agents to use
  - Coordinate between agents
  - Synthesize final responses
- **Tools**: `analyze_user_request`, `summarize_findings`
- **Handoffs**: Can hand off to any specialized agent

### CalendarAgent (`calendar_agent.py`)
- **Role**: Calendar operations specialist
- **Responsibilities**:
  - Retrieve calendar events
  - Search by date ranges and criteria
  - Provide calendar information to other agents
- **Tools**: `get_calendar_events`, `record_calendar_info`
- **Handoffs**: DraftAgent, EmailAgent, DocumentAgent

### EmailAgent (`email_agent.py`)
- **Role**: Email operations specialist
- **Responsibilities**:
  - Retrieve emails
  - Filter by criteria (unread, folder, date)
  - Provide email information to other agents
- **Tools**: `get_emails`, `record_email_info`
- **Handoffs**: DraftAgent, CalendarAgent, DocumentAgent

### DocumentAgent (`document_agent.py`)
- **Role**: Document and note operations specialist
- **Responsibilities**:
  - Search documents and notes
  - Filter by type, date, tags, notebooks
  - Provide document information to other agents
- **Tools**: `get_documents`, `get_notes`, `record_document_info`
- **Handoffs**: DraftAgent, CalendarAgent, EmailAgent

### DraftAgent (`draft_agent.py`)
- **Role**: Content creation specialist
- **Responsibilities**:
  - Create draft emails
  - Create draft calendar events
  - Create draft calendar changes
  - Manage draft lifecycle
- **Tools**: `create_draft_email`, `create_draft_calendar_event`, `create_draft_calendar_change`, `delete_*` variants
- **Handoffs**: Other agents for information gathering

## Usage

### Basic Multi-Agent Usage

```python
from services.chat.agents.workflow_agent import WorkflowAgent

# Create multi-agent workflow
agent = WorkflowAgent(
    thread_id=123,
    user_id="user123",
    llm_model="gpt-3.5-turbo",
    llm_provider="openai",
    use_multi_agent=True,  # Enable multi-agent mode
)

# Complex request that uses multiple agents
response = await agent.chat(
    "I need to prepare for tomorrow's meeting. Check my calendar, "
    "find related emails, and draft a follow-up email."
)
```

### Single-Agent Mode (Default)

```python
# Create single-agent workflow (traditional mode)
agent = WorkflowAgent(
    thread_id=123,
    user_id="user123",
    llm_model="gpt-3.5-turbo",
    llm_provider="openai",
    use_multi_agent=False,  # Single-agent mode
)

response = await agent.chat("Help me organize my day")
```

### Creating Individual Agents

```python
from services.chat.agents.calendar_agent import CalendarAgent
from services.chat.agents.email_agent import EmailAgent
from services.chat.agents.document_agent import DocumentAgent
from services.chat.agents.draft_agent import DraftAgent
from services.chat.agents.coordinator_agent import CoordinatorAgent

# Create individual specialized agents
calendar_agent = CalendarAgent(
    llm_model="gpt-3.5-turbo",
    llm_provider="openai",
    office_service_url="http://localhost:8001"
)

email_agent = EmailAgent(
    llm_model="gpt-3.5-turbo", 
    llm_provider="openai",
    office_service_url="http://localhost:8001"
)

document_agent = DocumentAgent(
    llm_model="gpt-3.5-turbo",
    llm_provider="openai", 
    office_service_url="http://localhost:8001"
)

draft_agent = DraftAgent(
    llm_model="gpt-3.5-turbo",
    llm_provider="openai"
)

coordinator = CoordinatorAgent(
    llm_model="gpt-3.5-turbo",
    llm_provider="openai"
)
```

## State Management

The multi-agent system uses shared state to coordinate between agents:

```python
# Initial state structure
initial_state = {
    "thread_id": str(thread_id),
    "user_id": user_id,
    "conversation_history": [],
    "calendar_info": {},      # CalendarAgent findings
    "email_info": {},         # EmailAgent findings  
    "document_info": {},      # DocumentAgent findings
    "draft_info": {},         # DraftAgent actions
    "request_analysis": {},   # Coordinator analysis
    "final_summary": {}       # Final response summary
}
```

### Context-Aware Tools

Each agent uses context-aware tools that automatically save findings to shared state:

```python
# CalendarAgent saves findings
await record_calendar_info(ctx, "Found 3 meetings tomorrow", "Tomorrow's Schedule")

# EmailAgent saves findings
await record_email_info(ctx, "5 unread emails about project", "Project Emails")

# DraftAgent saves actions
await record_draft_info(ctx, "Email draft created", "email")
```

## Agent Handoffs

Agents can hand off control to other agents using the `handoff` tool:

```python
# CalendarAgent hands off to DraftAgent
await handoff(to_agent="DraftAgent", reason="Need to create calendar event")

# DraftAgent hands off to EmailAgent for information
await handoff(to_agent="EmailAgent", reason="Need email context for draft")
```

## Example Workflows

### Complex Multi-Step Request

1. **User**: "Prepare me for tomorrow's board meeting"
2. **Coordinator**: Analyzes request → hands off to CalendarAgent
3. **CalendarAgent**: Finds meeting details → records info → hands off to EmailAgent
4. **EmailAgent**: Finds related emails → records info → hands off to DocumentAgent  
5. **DocumentAgent**: Finds relevant docs → records info → hands off to DraftAgent
6. **DraftAgent**: Creates meeting prep summary → hands back to Coordinator
7. **Coordinator**: Synthesizes all findings → provides comprehensive response

### Calendar-Focused Request

1. **User**: "What meetings do I have this week?"
2. **Coordinator**: Recognizes calendar query → hands off to CalendarAgent
3. **CalendarAgent**: Retrieves events → provides formatted response
4. **Coordinator**: Returns calendar information

### Drafting Request

1. **User**: "Draft an email to the team about the project update"
2. **Coordinator**: Recognizes drafting need → hands off to DraftAgent
3. **DraftAgent**: May hand off to EmailAgent/DocumentAgent for context
4. **DraftAgent**: Creates draft → records action
5. **Coordinator**: Confirms draft creation

## Configuration

### Multi-Agent vs Single-Agent

```python
# Multi-agent mode: specialized agents with coordination
WorkflowAgent(use_multi_agent=True)

# Single-agent mode: one agent with all tools
WorkflowAgent(use_multi_agent=False)
```

### Office Service Integration

```python
# Configure office service URL for calendar/email/document tools
WorkflowAgent(
    office_service_url="http://localhost:8001",
    use_multi_agent=True
)
```

### LLM Configuration

```python
# Each agent uses the same LLM configuration
WorkflowAgent(
    llm_model="gpt-4",
    llm_provider="openai",
    llm_kwargs={"temperature": 0.7},
    use_multi_agent=True
)
```

## Testing

Run the multi-agent tests:

```bash
# Test the multi-agent system
pytest services/chat/tests/test_multi_agent.py -v

# Test original workflow agent (includes single-agent mode)
pytest services/chat/tests/test_workflow_agent.py -v
```

## Demos

Run the multi-agent demo:

```bash
# Comprehensive multi-agent demo
python services/demos/multi_agent_demo.py

# Original workflow agent demo
python services/demos/workflow_agent_demo.py
```

## Benefits of Multi-Agent Architecture

### Specialization
- Each agent focuses on one domain (calendar, email, documents, drafting)
- Specialized system prompts and tools for each domain
- Better performance on domain-specific tasks

### Modularity
- Easy to add new specialized agents
- Clear separation of concerns
- Independent testing and development

### Coordination
- Intelligent handoffs between agents
- Shared state for information coordination
- Comprehensive responses that combine multiple domains

### Scalability
- Can handle complex multi-step workflows
- Parallel agent execution potential
- Clear workflow orchestration

## Migration from Single-Agent

Existing code using `WorkflowAgent` continues to work:

```python
# This still works (single-agent mode by default)
agent = WorkflowAgent(thread_id=123, user_id="user", ...)

# Enable multi-agent mode with one parameter
agent = WorkflowAgent(thread_id=123, user_id="user", use_multi_agent=True, ...)
```

## Files Structure

```
services/chat/agents/
├── workflow_agent.py          # Main WorkflowAgent with multi-agent support
├── coordinator_agent.py       # CoordinatorAgent (orchestrator)  
├── calendar_agent.py          # CalendarAgent (calendar operations)
├── email_agent.py             # EmailAgent (email operations)
├── document_agent.py          # DocumentAgent (document/note operations)
├── draft_agent.py             # DraftAgent (drafting operations)
├── llm_tools.py               # Shared tools and registry
├── llm_manager.py             # LLM management
├── chat_agent.py              # Original ChatAgent (used for memory)
└── README_multi_agent.md      # This documentation
```

## Future Enhancements

- **Parallel Agent Execution**: Run compatible agents in parallel
- **Agent Communication**: Direct agent-to-agent communication
- **Workflow Templates**: Pre-defined workflows for common patterns
- **Agent Performance Metrics**: Track agent efficiency and handoff patterns
- **Dynamic Agent Selection**: AI-driven agent selection based on request analysis 