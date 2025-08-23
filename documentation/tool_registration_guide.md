# Tool Registration Guide

This guide provides step-by-step instructions for registering new tools in the Briefly platform's tool discovery system.

## Quick Start

1. **Define your tool function** with proper typing
2. **Create ToolMetadata** with complete specifications
3. **Register the tool** in the appropriate tool class
4. **Add to GetTools registration** in `get_tools.py`
5. **Write tests** for your new tool

## Step-by-Step Registration

### 1. Define Your Tool Function

Create a well-typed function that implements your tool's functionality:

```python
from typing import Dict, Any, Optional

def my_data_processing_tool(
    input_data: str,
    processing_mode: str = "standard",
    max_items: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process data according to specified mode.
    
    Args:
        input_data: The data to process
        processing_mode: Mode of processing (standard, advanced, minimal)
        max_items: Maximum number of items to process
        
    Returns:
        Dict containing processed results and metadata
    """
    try:
        # Your tool implementation here
        processed_data = f"Processed: {input_data}"
        
        return {
            "status": "success",
            "processed_data": processed_data,
            "items_processed": len(input_data.split()),
            "mode_used": processing_mode
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 2. Create ToolMetadata

Define complete metadata for your tool:

```python
from services.chat.tools.tool_registry import ToolMetadata

metadata = ToolMetadata(
    tool_id="my_data_processing_tool",
    description="Process data according to specified mode with various options",
    category="utility",  # Choose appropriate category
    parameters={
        "input_data": {
            "type": "str",
            "description": "The data to process",
            "required": True
        },
        "processing_mode": {
            "type": "str", 
            "description": "Mode of processing",
            "required": False,
            "default": "standard",
            "enum": ["standard", "advanced", "minimal"]
        },
        "max_items": {
            "type": "int",
            "description": "Maximum number of items to process",
            "required": False
        }
    },
    examples=[
        {
            "description": "Basic processing",
            "params": {
                "input_data": "hello world test"
            }
        },
        {
            "description": "Advanced processing with limit",
            "params": {
                "input_data": "data to process",
                "processing_mode": "advanced",
                "max_items": 5
            }
        }
    ],
    return_format={
        "status": "success/error",
        "processed_data": "The processed result",
        "items_processed": "Number of items processed",
        "mode_used": "Processing mode that was used",
        "error": "Error message if status is error"
    },
    requires_auth=False,  # Set to True if tool needs user authentication
    service_dependency="none",  # Or specify service like "office_service"
    version="1.0"
)
```

### 3. Add to Appropriate Tool Class

#### For Utility Tools (services/chat/tools/utility_tools.py)

```python
class UtilityTools:
    def __init__(self):
        pass
    
    # Add your tool method
    def my_data_processing_tool(
        self,
        input_data: str,
        processing_mode: str = "standard", 
        max_items: Optional[int] = None
    ) -> Dict[str, Any]:
        # Implementation (can call standalone function)
        return my_data_processing_tool(input_data, processing_mode, max_items)
```

#### For User-Authenticated Tools (services/chat/tools/data_tools.py)

```python
class DataTools:
    def __init__(self, user_id: str):
        self.user_id = user_id  # Pre-bind user context for security
    
    def my_user_data_tool(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Tool that needs user context - user_id is pre-bound."""
        try:
            # Use self.user_id in your implementation
            results = some_service.query_user_data(
                user_id=self.user_id,  # Pre-bound, cannot be tampered with
                query=query,
                max_results=max_results
            )
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

### 4. Register in GetTools

In `services/chat/tools/get_tools.py`, add registration to the appropriate registration method:

#### For Utility Tools

```python
def _register_utility_tools(self):
    """Register utility tools."""
    # ... existing registrations ...
    
    # Add your new tool registration
    my_tool_metadata = ToolMetadata(
        tool_id="my_data_processing_tool",
        description="Process data according to specified mode with various options",
        category="utility",
        parameters={
            "input_data": {"type": "str", "description": "The data to process", "required": True},
            "processing_mode": {"type": "str", "description": "Mode of processing", "required": False, "default": "standard"},
            "max_items": {"type": "int", "description": "Maximum number of items to process", "required": False}
        },
        examples=[
            {"description": "Basic processing", "params": {"input_data": "hello world"}},
            {"description": "Advanced mode", "params": {"input_data": "test data", "processing_mode": "advanced"}}
        ],
        return_format={
            "status": "success/error",
            "processed_data": "The processed result",
            "items_processed": "Number of items processed",
            "error": "Error message if failed"
        },
        requires_auth=False,
        service_dependency="none"
    )
    self.registry.register_tool(my_tool_metadata, self.utility_tools.my_data_processing_tool)
```

#### For Data Tools (with authentication)

```python
def _register_data_tools(self):
    """Register data retrieval tools."""
    # ... existing registrations ...
    
    # Register user data tool (note: no user_id in parameters!)
    my_user_tool_metadata = ToolMetadata(
        tool_id="my_user_data_tool",
        description="Query user-specific data with authentication",
        category="data_retrieval",
        parameters={
            # NO user_id parameter - it's pre-bound in the class constructor
            "query": {"type": "str", "description": "Search query", "required": True},
            "max_results": {"type": "int", "description": "Maximum results", "required": False, "default": 10}
        },
        examples=[
            {"description": "Search user data", "params": {"query": "meetings next week"}}
        ],
        return_format={
            "status": "success/error",
            "results": "Query results",
            "error": "Error message if failed"
        },
        requires_auth=True,  # Important: mark as requiring auth
        service_dependency="user_data_service"
    )
    self.registry.register_tool(my_user_tool_metadata, self.data_tools.my_user_data_tool)
```

### 5. Write Tests

Create tests for your tool in `services/chat/tests/`:

```python
import pytest
from services.chat.tools.get_tools import GetTools

class TestMyNewTool:
    @pytest.fixture
    def get_tools(self):
        return GetTools(user_id="test_user")
    
    def test_my_data_processing_tool_basic(self, get_tools):
        """Test basic functionality of the new tool."""
        result = get_tools.get_tool.execute("my_data_processing_tool", {
            "input_data": "test data"
        })
        
        assert result["status"] == "success"
        assert "processed_data" in result["result"]
        assert result["result"]["mode_used"] == "standard"  # default value
    
    def test_my_data_processing_tool_advanced(self, get_tools):
        """Test advanced mode."""
        result = get_tools.get_tool.execute("my_data_processing_tool", {
            "input_data": "test data",
            "processing_mode": "advanced",
            "max_items": 5
        })
        
        assert result["status"] == "success"
        assert result["result"]["mode_used"] == "advanced"
    
    def test_tool_metadata_available(self, get_tools):
        """Test that tool metadata is properly registered."""
        tool_info = get_tools.get_tool.get_tool_info("my_data_processing_tool")
        
        assert tool_info["status"] == "success"
        metadata = tool_info["tool_info"]
        assert metadata["tool_id"] == "my_data_processing_tool"
        assert metadata["category"] == "utility"
        assert "input_data" in metadata["parameters"]
    
    def test_tool_appears_in_listing(self, get_tools):
        """Test that tool appears in tool listings."""
        tools = get_tools.get_tool.list_tools()
        tool_ids = [tool[0] for tool in tools]
        assert "my_data_processing_tool" in tool_ids
```

## Registration Patterns by Category

### Data Retrieval Tools

**Key Points**:
- Always require authentication (`requires_auth=True`)
- Pre-bind user context in class constructor
- Never include `user_id` in tool parameters
- Specify service dependencies

```python
# In DataTools class
def __init__(self, user_id: str):
    self.user_id = user_id  # Pre-bound for security

def my_secure_tool(self, param1: str) -> Dict[str, Any]:
    # Use self.user_id - cannot be overridden by agent
    return service.get_data(user_id=self.user_id, param1=param1)

# Registration
metadata = ToolMetadata(
    requires_auth=True,
    service_dependency="data_service",
    parameters={
        # NO user_id parameter!
        "param1": {"type": "str", "required": True}
    }
)
```

### Draft Management Tools

**Key Points**:
- Require authentication
- Work with thread context
- Include `thread_id` parameter

```python
def create_my_draft(self, thread_id: str, content: str) -> Dict[str, Any]:
    # Implementation with thread context
    pass

# Registration includes thread_id parameter
parameters={
    "thread_id": {"type": "str", "description": "Thread ID", "required": True},
    "content": {"type": "str", "description": "Draft content", "required": True}
}
```

### Search Tools

**Key Points**:
- May or may not require authentication
- Include query parameters
- Specify search scope and filters

```python
def my_search_tool(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
    # Search implementation
    pass
```

### Utility Tools

**Key Points**:
- Usually no authentication required
- Pure functions when possible
- Clear input/output specifications

```python
def my_utility_function(self, input_data: str, options: Dict = None) -> Dict[str, Any]:
    # Stateless processing
    pass
```

## Common Patterns

### Error Handling

```python
def my_tool(self, param: str) -> Dict[str, Any]:
    try:
        result = process_data(param)
        return {
            "status": "success", 
            "data": result
        }
    except ValueError as e:
        return {
            "status": "error",
            "error": f"Invalid input: {e}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in my_tool: {e}")
        return {
            "status": "error", 
            "error": "An unexpected error occurred"
        }
```

### Optional Parameters with Defaults

```python
parameters={
    "required_param": {
        "type": "str",
        "description": "This parameter is required",
        "required": True
    },
    "optional_param": {
        "type": "int",
        "description": "This parameter is optional",
        "required": False,
        "default": 10
    },
    "enum_param": {
        "type": "str",
        "description": "Choose from predefined values",
        "required": False,
        "default": "auto",
        "enum": ["auto", "manual", "advanced"]
    }
}
```

### Complex Return Formats

```python
return_format={
    "status": "success/error",
    "data": {
        "items": "List of processed items",
        "metadata": {
            "total_count": "Number of items",
            "processing_time": "Time taken in seconds"
        }
    },
    "pagination": {
        "has_next": "Whether more results available",
        "next_token": "Token for next page"
    },
    "error": "Error message if status is error"
}
```

## Validation and Testing

Before registering your tool:

1. **Run the tests**: Ensure all existing tests still pass
2. **Test tool discovery**: Verify your tool appears in `list_tools()`
3. **Test metadata retrieval**: Check `get_tool_info()` returns correct data
4. **Test execution**: Verify `execute()` works with various parameters
5. **Test error cases**: Ensure proper error handling and messages
6. **Validate security**: Confirm user context cannot be tampered with

```bash
# Run specific tests
python -m pytest services/chat/tests/test_tool_discovery.py -v

# Run all chat service tests
python -m pytest services/chat/tests/ -v
```

## Troubleshooting

### Tool Not Appearing in List

1. Check registration call is included in `_register_all_tools()`
2. Verify ToolMetadata is correctly formatted
3. Ensure no exceptions during registration

### Execution Errors

1. Check function signature matches metadata parameters
2. Verify return format matches specification
3. Test with simple parameters first

### Authentication Issues

1. For user tools, ensure `requires_auth=True`
2. Verify user context is pre-bound in class constructor
3. Don't include `user_id` in parameters dictionary

### Import Errors

1. Check all imports are correct
2. Verify tool class is properly initialized in GetTools
3. Ensure circular imports are avoided
