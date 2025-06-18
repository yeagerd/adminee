# Multi-Agent Chat Demo

A simple command-line interface for testing and demonstrating the consolidated multi-agent WorkflowAgent system.

## Usage

### Basic Multi-Agent Chat Demo

```bash
python services/demos/chat-simple.py
```

### Streaming Demo

```bash
python services/demos/chat-simple.py --streaming
```

## Features

### Multi-Agent Architecture
- **CoordinatorAgent**: Orchestrates tasks and delegates to specialized agents
- **CalendarAgent**: Handles calendar queries and scheduling operations
- **EmailAgent**: Manages email operations and searches
- **DocumentAgent**: Finds and manages documents and notes
- **DraftAgent**: Creates drafts of emails and content

### Interactive Commands
- `help` - Show available commands, agents, and example prompts
- `clear` - Clear conversation history and start fresh
- `quit` or `exit` - Exit the demo

### Example Prompts

Try these prompts to see different agents in action:

#### Calendar Operations
- "What meetings do I have this week?"
- "Show me my calendar for tomorrow"
- "Do I have any conflicts on Friday?"
- "When is my next appointment?"

#### Email Management  
- "Show me my unread emails from today"
- "Find emails about the project planning"
- "What's in my inbox?"
- "Find emails from john@example.com"

#### Document Operations
- "Find my notes about the quarterly planning"
- "Search for documents about the budget"
- "Show me my recent notes"
- "Find documents related to the project"

#### Content Creation
- "Draft an email to john@example.com about the meeting"
- "Create a calendar event for team standup"
- "Draft a follow-up email for the board meeting"
- "Help me write a project update"

#### Complex Multi-Agent Coordination
- "Help me prepare for tomorrow's board meeting"
- "Organize my day by checking calendar and emails"
- "Find everything related to the quarterly planning project"
- "Schedule follow-up meetings and draft summary emails"

## How It Works

1. **User Input**: You provide a request or question
2. **Coordinator Analysis**: The CoordinatorAgent analyzes your request and determines which specialized agents to involve
3. **Agent Delegation**: Tasks are delegated to appropriate specialized agents
4. **Information Gathering**: Specialized agents use their tools to gather relevant information
5. **Context Sharing**: Agents record their findings for other agents to access
6. **Coordination**: The CoordinatorAgent synthesizes results from all agents
7. **Agent Handoffs**: Agents can hand off control to others as needed for complex workflows
8. **Final Response**: A comprehensive response is provided to the user

## Demo Flow

1. **Welcome Screen**: Shows introduction, available agents, and example prompts
2. **Agent Initialization**: Creates and builds the multi-agent WorkflowAgent system
3. **Interactive Chat**: Chat loop with command processing and agent coordination
4. **Graceful Exit**: Clean shutdown on quit/exit

## Sample Session

```
============================================================
🚀 Welcome to the Multi-Agent WorkflowAgent Demo!
============================================================

This demo lets you chat with the multi-agent WorkflowAgent system.
Features specialized agents for different tasks:
  • CoordinatorAgent - Orchestrates and delegates tasks
  • CalendarAgent - Manages calendar and scheduling
  • EmailAgent - Handles email operations
  • DocumentAgent - Manages documents and notes
  • DraftAgent - Creates drafts and content

📋 Example prompts to try:
  • 'What meetings do I have this week?'
  • 'Show me my unread emails'
  • 'Find my notes about the project'
  • 'Draft an email to the team about the meeting'
  • 'Help me prepare for tomorrow's board meeting'

💡 Commands:
  • 'quit' or 'exit' - Exit the demo
  • 'help' - Show this help message
  • 'clear' - Clear the conversation history

🤖 Creating Multi-Agent WorkflowAgent...
✅ Multi-Agent system ready with 5 specialized agents:
   • Coordinator
   • CalendarAgent
   • EmailAgent
   • DocumentAgent
   • DraftAgent

💬 Multi-Agent chat started!
Type 'help' for commands or start chatting!

You: Help me prepare for tomorrow's board meeting
🤖 Briefly: I'll help you prepare for tomorrow's board meeting. Let me coordinate with the specialized agents to gather everything you need.

[CoordinatorAgent delegates to CalendarAgent]
[CalendarAgent retrieves meeting details and records calendar info]
[CoordinatorAgent delegates to EmailAgent] 
[EmailAgent searches for related emails and records findings]
[CoordinatorAgent delegates to DocumentAgent]
[DocumentAgent finds relevant documents and notes]
[CoordinatorAgent synthesizes all information]

I've gathered everything for your board meeting preparation:

**Meeting Details:**
- Tomorrow at 2:00 PM - 3:30 PM
- Board Room A, attendees: CEO, CFO, and 5 board members

**Related Communications:**
- 3 emails about quarterly results
- 2 emails about budget proposals  
- 1 email with agenda items

**Relevant Documents:**
- Q3 Financial Report
- Budget Proposal 2024
- Strategic Planning Notes

Would you like me to draft talking points or create follow-up reminders?

You: clear

🧹 Clearing conversation history...
✅ Multi-Agent system ready with 5 specialized agents:
   • Coordinator
   • CalendarAgent
   • EmailAgent
   • DocumentAgent
   • DraftAgent

💬 History cleared. Continue chatting!

You: quit

👋 Thanks for using the WorkflowAgent demo! Goodbye!
```

## Configuration

### LLM Settings

Edit the `create_agent` method in `chat-simple.py` to customize:

```python
agent = WorkflowAgent(
    thread_id=self.thread_id,
    user_id=self.user_id,
    llm_model="gpt-4",  # Change model here
    llm_provider="openai",  # Change provider here
    max_tokens=2000,
    office_service_url="http://localhost:8001",
)
```

### Office Service

Make sure the office service is running on `http://localhost:8001` or update the URL in the demo.

## Error Handling

The demo includes comprehensive error handling:
- LLM errors are caught and displayed gracefully
- Keyboard interrupts (Ctrl+C) exit cleanly
- Invalid commands show helpful messages
- Agent coordination failures are handled gracefully
- Connection issues are reported clearly

## Advanced Usage

### Streaming Mode

Use `--streaming` flag to see real-time response generation:

```bash
python services/demos/chat-simple.py --streaming
```

This shows how the multi-agent system generates responses in real-time, including:
- Agent handoffs and coordination
- Tool usage by specialized agents
- Context sharing between agents
- Final response synthesis

### Testing Different Scenarios

1. **Simple single-agent queries** - Test individual agent capabilities
2. **Complex multi-agent workflows** - Test agent coordination
3. **Use 'clear'** - Test conversation memory reset across agents
4. **Try various example prompts** - Explore different agent specializations

## Agent Specializations

### CoordinatorAgent
- Analyzes user requests
- Delegates to appropriate specialized agents
- Synthesizes results from multiple agents
- Handles complex workflow orchestration

### CalendarAgent
- Retrieves calendar events and scheduling information
- Searches by date ranges and criteria
- Records calendar findings for other agents

### EmailAgent
- Manages email operations and searches
- Finds relevant communications
- Records email findings for coordination

### DocumentAgent
- Searches and manages documents and notes
- Finds relevant information across document types
- Records document findings for other agents

### DraftAgent
- Creates drafts of emails and content
- Generates various types of written content
- Integrates information from other agents

## Development

The demo showcases the consolidated multi-agent architecture:
- Single entry point with multi-agent coordination
- Context sharing and state management across agents
- Agent handoff capabilities
- Extensible architecture for additional specialized agents
- Integration with existing LLM providers and office services 