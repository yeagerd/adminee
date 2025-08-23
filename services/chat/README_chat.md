# Chat Service

The Chat Service provides AI-powered conversation capabilities with dynamic tool discovery and execution.

## API Endpoint Patterns

- **User-facing endpoints:**
  - Use header-based user extraction (X-User-Id set by gateway)
  - No user_id in path or query
  - Require user authentication (JWT/session)

- **Internal/service endpoints:**
  - Use /internal prefix
  - Require API key/service authentication
  - Used for service-to-service and background job calls

## Tool System Architecture

The Chat Service features a dynamic tool discovery system organized into the following structure:

### Tool Organization

```
services/chat/tools/
├── data_tools.py          # Data retrieval from integrated services
├── draft_tools.py         # Draft management for emails and calendar
├── search_tools.py        # Search capabilities (semantic, user data, Vespa)
├── web_tools.py          # External web search
├── utility_tools.py       # Helper functions and formatting
├── get_tools.py          # Main tool registry and discovery interface
└── tool_registry.py      # Core registry infrastructure
```

### Key Components

- **GetTools**: Main interface for tool discovery and execution
- **EnhancedToolRegistry**: Central registry managing all tools with metadata
- **ToolMetadata**: Complete API specifications for each tool
- **Tool Categories**: Organized groupings (data_retrieval, draft_management, search, web_search, utility)

### Security Model

All authenticated tools use **pre-bound user context** to prevent agent tampering:

```python
# Secure: user_id is baked into tool instance during initialization
data_tools = DataTools(user_id="user123")
registry.register_tool(metadata, data_tools.get_calendar_events)

# Agent cannot override user_id - it's already bound
result = registry.execute_tool("get_calendar_events", start_date="2024-01-01")
```

### Agent Integration

Agents interact with tools through a three-step process:

1. **Discovery**: `list_tools()` returns available tools
2. **Specification**: `get_tool_info(tool_id)` provides complete API details  
3. **Execution**: `execute(tool_id, params)` runs tools with validation

### Documentation

- **[Tool Discovery Implementation](../../documentation/tool_discovery_implementation.md)** - Complete system guide
- **[Tool Categories Reference](../../documentation/tool_categories.md)** - All available tools
- **[Tool Registration Guide](../../documentation/tool_registration_guide.md)** - Adding new tools

## Testing

```bash
# Run all chat service tests
python -m pytest services/chat/tests/ -v

# Test tool discovery specifically
python -m pytest services/chat/tests/test_tool_discovery.py -v

# Test legacy tool compatibility
python -m pytest services/chat/tests/test_llm_tools.py -v
``` 