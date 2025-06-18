# Interactive Chat Demo

A simple command-line interface for testing and demonstrating the WorkflowAgent system.

## Usage

### Basic Chat Demo

```bash
python services/demos/chat-simple.py
```

### Streaming Demo

```bash
python services/demos/chat-simple.py --streaming
```

## Features

### Mode Selection
- **Multi-Agent Mode**: Uses specialized agents (CoordinatorAgent, CalendarAgent, EmailAgent, DocumentAgent, DraftAgent)
- **Single-Agent Mode**: Uses one agent with all tools combined

### Interactive Commands
- `help` - Show available commands and example prompts
- `switch` - Switch between single-agent and multi-agent modes
- `clear` - Clear conversation history and start fresh
- `quit` or `exit` - Exit the demo

### Example Prompts

Try these prompts to see the multi-agent system in action:

#### Calendar Queries
- "What meetings do I have this week?"
- "Show me my calendar for tomorrow"
- "Do I have any conflicts on Friday?"

#### Email Queries  
- "Show me my unread emails from today"
- "Find emails about the project planning"
- "What's in my inbox?"

#### Document Queries
- "Find my notes about the quarterly planning"
- "Search for documents about the budget"
- "Show me my recent notes"

#### Drafting Tasks
- "Draft an email to john@example.com about the meeting"
- "Create a calendar event for team standup"
- "Draft a follow-up email for the board meeting"

#### Complex Multi-Agent Tasks
- "Help me prepare for tomorrow's board meeting"
- "Organize my day by checking calendar and emails"
- "Find everything related to the quarterly planning project"

## Demo Flow

1. **Welcome Screen**: Shows introduction and commands
2. **Mode Selection**: Choose between multi-agent (default) or single-agent
3. **Agent Initialization**: Creates and builds the WorkflowAgent
4. **Interactive Chat**: Chat loop with command processing
5. **Graceful Exit**: Clean shutdown on quit/exit

## Sample Session

```
============================================================
🚀 Welcome to the Interactive WorkflowAgent Demo!
============================================================

This demo lets you chat with the WorkflowAgent system.
You can test both single-agent and multi-agent modes.

📋 Example prompts to try:
  • 'What meetings do I have this week?'
  • 'Show me my unread emails'
  • 'Find my notes about the project'
  • 'Draft an email to the team about the meeting'
  • 'Help me prepare for tomorrow's board meeting'

💡 Commands:
  • 'quit' or 'exit' - Exit the demo
  • 'switch' - Switch between single and multi-agent modes
  • 'help' - Show this help message
  • 'clear' - Clear the conversation history

Choose mode (1=Multi-Agent, 2=Single-Agent, default=1): 

🤖 Creating Multi-Agent WorkflowAgent...
✅ Multi-Agent system ready with 5 specialized agents:
   • Coordinator
   • CalendarAgent
   • EmailAgent
   • DocumentAgent
   • DraftAgent

💬 Chat started! (Current mode: Multi-Agent)
Type 'help' for commands or start chatting!

You: What meetings do I have today?
🤖 Briefly: Let me check your calendar for today's meetings...

[CalendarAgent searches calendar events]
[Coordinator synthesizes response]

I found 3 meetings scheduled for today:
1. Team Standup at 9:00 AM
2. Project Review at 2:00 PM  
3. One-on-one with Sarah at 4:30 PM

You: switch

🔄 Switching from Multi-Agent to Single-Agent mode...

🤖 Creating Single-Agent WorkflowAgent...
✅ Single-Agent system ready

💬 Switched to Single-Agent mode. Continue chatting!

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
    use_multi_agent=use_multi_agent,
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
- Connection issues are reported clearly

## Advanced Usage

### Streaming Mode

Use `--streaming` flag to see real-time response generation:

```bash
python services/demos/chat-simple.py --streaming
```

This shows how the agent generates responses token by token, which is useful for understanding the workflow progression in multi-agent mode.

### Testing Different Scenarios

1. **Start in Multi-Agent mode** - Test complex workflows
2. **Switch to Single-Agent mode** - Compare performance
3. **Use 'clear'** - Test conversation memory reset
4. **Try example prompts** - Explore different agent capabilities

## Development

The demo is designed to be easily extensible:
- Add new commands by extending the command handling logic
- Customize the welcome message and examples
- Add new agent configurations or testing scenarios
- Integrate with different LLM providers 