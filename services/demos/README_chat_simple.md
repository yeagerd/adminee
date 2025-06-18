# Multi-Agent WorkflowAgent Chat Demo

This demo provides an interactive command-line interface to chat with the WorkflowAgent multi-agent system. The system features specialized agents for calendar, email, documents, and drafting operations.

## Quick Start

```bash
# Interactive multi-agent chat
python services/demos/chat.py

# Send a single message
python services/demos/chat.py --message "Draft an email to john@example.com about the meeting"

# Streaming demo (shows real-time response generation)
python services/demos/chat.py --streaming

# API mode (requires chat service running)
python services/demos/chat.py --api
```

## Features

### Multi-Agent System
- **CoordinatorAgent**: Main orchestrator that routes requests to specialized agents
- **CalendarAgent**: Handles calendar queries and scheduling information
- **EmailAgent**: Manages email operations and searches
- **DocumentAgent**: Finds and manages documents and notes
- **DraftAgent**: Creates drafts for emails, calendar events, and content

### Intelligent Routing
The system automatically routes requests to the appropriate agent:
- "What's on my calendar?" → CalendarAgent
- "Show me my emails" → EmailAgent
- "Find my notes about the project" → DocumentAgent
- "Create a calendar event" → DraftAgent
- "Draft an email" → DraftAgent

### Logging and Visibility
- Clean, informative logging showing agent interactions
- Draft content displayed to the user
- Agent handoffs and coordination visible in logs
- HTTP request logs suppressed for clean output

## Usage Examples

### Calendar Operations
```bash
# View calendar events
python services/demos/chat.py --message "What meetings do I have this week?"

# Create calendar events
python services/demos/chat.py --message "Create a calendar event at 2pm tomorrow with the team"
```

### Email Operations
```bash
# View emails
python services/demos/chat.py --message "Show me my unread emails from today"

# Draft emails
python services/demos/chat.py --message "Draft an email to alice@company.com about the quarterly review"
```

### Document Operations
```bash
# Find documents
python services/demos/chat.py --message "Find my notes about the project planning"

# Search content
python services/demos/chat.py --message "Look for documents mentioning budget"
```

### Interactive Commands
When running in interactive mode, you can use these commands:
- `help` - Show available commands
- `clear` - Clear conversation history (starts new thread)
- `quit` or `exit` - Exit the demo

## Configuration

### LLM Model
Edit the `create_agent` method in `chat.py` to customize:
```python
agent = WorkflowAgent(
    thread_id=self.thread_id,
    user_id=self.user_id,
    llm_model="gpt-4.1-nano",  # Change this to your preferred model
    llm_provider="openai",
    max_tokens=2000,
    office_service_url="http://localhost:8001",
)
```

### Logging
The demo includes clean logging configuration:
- Agent operations logged at INFO level
- HTTP requests suppressed
- Database operations suppressed
- Clean output focused on multi-agent workflow

## Architecture

### Multi-Agent Workflow
1. **User Input** → CoordinatorAgent analyzes request
2. **Routing** → Coordinator hands off to appropriate specialized agent
3. **Processing** → Specialized agent handles the request
4. **Response** → Results returned to user with draft content if applicable

### Agent Specialization
- **Read Operations**: CalendarAgent, EmailAgent, DocumentAgent
- **Create Operations**: DraftAgent (for all creation/drafting tasks)
- **Coordination**: CoordinatorAgent (orchestrates the workflow)

## Troubleshooting

### Common Issues
1. **"object NoneType can't be used in 'await' expression"**
   - This has been resolved with enhanced error handling
   - The system now properly handles Context operations

2. **Agent routing issues**
   - The Coordinator has been enhanced with explicit routing rules
   - Creation requests properly route to DraftAgent

3. **HTTP request spam in logs**
   - HTTP logging has been suppressed for clean output
   - Only relevant multi-agent operations are logged

### Development Mode
For more verbose logging during development:
```python
logging.getLogger("services.chat.agents.workflow_agent").setLevel(logging.DEBUG)
```

## Streaming Demo

The streaming demo shows real-time response generation:

```bash
python services/demos/chat.py --streaming
```

This demonstrates how the multi-agent system generates responses progressively, useful for understanding the workflow timing and agent interactions.

## API Mode

The demo also supports API mode for testing the chat service:

```bash
# Start the chat service first
python services/chat/main.py

# Then use API mode
python services/demos/chat.py --api
```

In API mode, you get additional commands:
- `list` - List all conversation threads
- `new` - Start a new thread
- `switch <thread_id>` - Switch to existing thread

## Integration

This demo serves as a reference implementation for integrating the WorkflowAgent into other applications. Key integration points:

1. **WorkflowAgent Creation**: How to initialize the multi-agent system
2. **Message Processing**: How to send messages and receive responses
3. **Draft Handling**: How to extract and display draft content
4. **Error Handling**: How to handle and recover from errors
5. **Logging Configuration**: How to set up clean, informative logging 