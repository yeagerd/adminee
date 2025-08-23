# Tool Discovery Implementation Guide

## Overview

The Tool Discovery System provides a dynamic way for AI agents to discover, understand, and execute tools at runtime. This system replaces the previous hardcoded tool approach with a flexible, extensible registry that allows agents to query available tools and their specifications dynamically.

## Architecture

### Core Components

#### 1. ToolMetadata
A dataclass that defines the complete API specification for any tool:

```python
@dataclass
class ToolMetadata:
    tool_id: str                    # Unique identifier (e.g., "get_calendar_events")
    description: str                # Human-readable description
    category: str                   # Tool category (e.g., "data_retrieval", "draft_management")
    parameters: Dict[str, Any]     # Parameter specifications with types and descriptions
    examples: List[Dict[str, Any]] # Example usage patterns
    return_format: Dict[str, Any]  # Return value structure
    requires_auth: bool             # Whether tool requires user authentication
    service_dependency: Optional[str] # Which service this tool depends on
    version: str = "1.0"           # Tool version for compatibility
```

#### 2. EnhancedToolRegistry
The central registry that manages all tools:

```python
class EnhancedToolRegistry(ToolRegistry):
    def register_tool(self, metadata: ToolMetadata, func: callable) -> None
    def list_tools(self) -> List[Tuple[str, str]]
    def get_tool_info(self, tool_id: str) -> Optional[ToolMetadata]
    def execute_tool(self, tool_id: str, **kwargs) -> Any
    def search_tools(self, query: str) -> List[Tuple[str, str]]
    def get_tool_count(self) -> int
    def get_categories(self) -> List[str]
    def export_registry(self) -> Dict[str, Any]
```

#### 3. GetTools Class
The main interface that initializes and provides access to all tools:

```python
class GetTools:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.registry = EnhancedToolRegistry()
        self.get_tool = GetTool(registry=self.registry, default_user_id=user_id)
        
        # Initialize all tool classes with pre-bound user context
        self.data_tools = DataTools(user_id)
        self.draft_tools = DraftTools(user_id)
        self.search_tools = SearchTools("", user_id)
        self.web_tools = WebTools()
        self.utility_tools = UtilityTools()
        
        self._register_all_tools()
```

## Security Model

### User Context Pre-binding

**Critical Security Feature**: All tools that require user authentication are pre-bound with the user context during initialization. This prevents the agent from tampering with user IDs.

```python
# SECURE: user_id is baked into the tool instance
data_tools = DataTools(user_id="user123")
registry.register_tool(metadata, data_tools.get_calendar_events)

# The agent CANNOT pass a different user_id - it's already bound
result = registry.execute_tool("get_calendar_events", start_date="2024-01-01")
```

### Authentication Requirements

Tools are marked with `requires_auth: bool` in their metadata to indicate if they need user authentication. The registry ensures proper access control during execution.

## Tool Categories

### 1. Data Retrieval (`data_retrieval`)
Tools for accessing user data from various services:
- `get_calendar_events` - Retrieve calendar events from office service
- `get_emails` - Get emails from office service  
- `get_notes` - Access notes from office service
- `get_documents` - Retrieve documents from office service

### 2. Draft Management (`draft_management`)
Tools for creating and managing draft content:
- `create_draft_email` - Create/update email drafts
- `create_draft_calendar_event` - Create/update calendar event drafts
- `create_draft_calendar_change` - Create calendar change drafts
- `delete_draft_email` - Delete email drafts
- `delete_draft_calendar_event` - Delete calendar event drafts
- `delete_draft_calendar_edit` - Delete calendar edit drafts
- `clear_all_drafts` - Clear all drafts for a thread

### 3. Search (`search`)
Tools for searching and discovering information:
- `semantic_search` - Semantic search across user data
- `user_data_search` - Search user-specific data
- `vespa_search` - Advanced Vespa-based search

### 4. Web Search (`web_search`)
Tools for external web searching:
- `web_search` - Search the web for information

### 5. Utility (`utility`)
Helper tools for data processing and formatting:
- `validate_email_format` - Validate email address format
- `sanitize_string` - Clean and sanitize text strings
- `parse_date_range` - Parse date range strings
- `format_file_size` - Format file sizes for display
- `extract_phone_number` - Extract phone numbers from text
- `generate_summary` - Generate text summaries
- `format_event_time_for_display` - Format event times for display

## Usage Examples

### Agent Tool Discovery Flow

```python
# 1. Initialize the tool system
get_tools = GetTools(user_id="user123")

# 2. Agent discovers available tools
tools_list = get_tools.get_tool.list_tools()
# Returns: [("get_calendar_events", "Get calendar events for a user"), ...]

# 3. Agent gets detailed API specification for a specific tool
tool_spec = get_tools.get_tool.get_tool_info("get_calendar_events")
# Returns: {
#   "status": "success",
#   "tool_info": {
#     "tool_id": "get_calendar_events",
#     "description": "Get calendar events for a user from the office service",
#     "category": "data_retrieval",
#     "parameters": {
#       "start_date": {"type": "str", "description": "Start date in YYYY-MM-DD format", "required": False},
#       "end_date": {"type": "str", "description": "End date in YYYY-MM-DD format", "required": False},
#       ...
#     },
#     "examples": [...],
#     "return_format": {...},
#     "requires_auth": True,
#     "service_dependency": "office_service"
#   }
# }

# 4. Agent executes the tool with appropriate parameters
result = get_tools.get_tool.execute("get_calendar_events", {
    "start_date": "2024-01-15",
    "end_date": "2024-01-20"
})
```

### Registering a New Tool

```python
# 1. Define the tool metadata
metadata = ToolMetadata(
    tool_id="my_custom_tool",
    description="Description of what this tool does",
    category="utility",
    parameters={
        "input_text": {"type": "str", "description": "Text to process", "required": True},
        "format": {"type": "str", "description": "Output format", "required": False, "default": "json"}
    },
    examples=[
        {"description": "Basic usage", "params": {"input_text": "Hello world"}}
    ],
    return_format={
        "status": "success/error",
        "result": "Processed output",
        "error": "Error message if failed"
    },
    requires_auth=False,
    service_dependency="none"
)

# 2. Create the tool function (with user context pre-bound if needed)
def my_custom_tool(input_text: str, format: str = "json") -> Dict[str, Any]:
    # Tool implementation
    return {"status": "success", "result": f"Processed: {input_text}"}

# 3. Register with the registry
registry.register_tool(metadata, my_custom_tool)
```

## Migration from llm_tools.py

The migration involved moving functions from the monolithic `llm_tools.py` into categorized modules:

### Before (llm_tools.py)
```python
# All tools in one file
def get_calendar_events(user_id, start_date=None, ...):
    # Implementation

def create_draft_email(user_id, thread_id, to=None, ...):
    # Implementation

def format_event_time_for_display(event_time, timezone=None):
    # Implementation
```

### After (Categorized Structure)
```python
# services/chat/tools/data_tools.py
class DataTools:
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def get_calendar_events(self, start_date=None, ...):
        # Implementation using self.user_id

# services/chat/tools/draft_tools.py  
class DraftTools:
    def __init__(self, user_id: str):
        self.user_id = user_id
        
    def create_draft_email(self, thread_id, to=None, ...):
        # Implementation using self.user_id

# services/chat/tools/utility_tools.py
class UtilityTools:
    def format_event_time_for_display(self, event_time, timezone=None):
        # Implementation (no user context needed)
```

## Testing

Comprehensive tests are provided in `services/chat/tests/test_tool_discovery.py`:

- Tool listing and discovery
- API specification retrieval
- Tool execution through registry
- User ID security (ensuring it cannot be tampered with)
- Registry statistics and search functionality
- Metadata completeness validation

## Benefits

1. **Security**: User context is pre-bound, preventing tampering
2. **Dynamic Discovery**: Agents can discover tools at runtime
3. **Self-Documenting**: Each tool provides its own API specification
4. **Extensible**: New tools can be added without code changes to the agent
5. **Organized**: Tools are categorized by functionality
6. **Backward Compatible**: Existing workflows continue to work
7. **Type Safe**: Full type hints and validation

## Best Practices

1. **Always pre-bind user context** for authenticated tools
2. **Use descriptive tool IDs** that clearly indicate functionality
3. **Provide comprehensive examples** in tool metadata
4. **Categorize tools appropriately** for easy discovery
5. **Include proper error handling** in tool implementations
6. **Test tool discovery and execution** thoroughly
7. **Document parameter types and requirements** clearly
