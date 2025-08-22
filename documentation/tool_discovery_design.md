# Tool Discovery Architecture Design

## Overview
The current system has a misunderstanding about the purpose of `get_tools.py`. It was implemented to return only get* tools when the goal was to create a dynamic tool discovery system.

## Current State Analysis
- **BrieflyAgent** receives a fixed list of tools at initialization
- **GetTools** class only handles 4 specific get_* functions
- **ToolRegistry** is hardcoded with specific tool names
- No dynamic tool discovery or API specification retrieval

## Target Architecture

### 1. Tool Metadata Interface
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
```

### 2. Tool Registry Design
```python
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register_tool(self, tool_metadata: ToolMetadata) -> None:
        """Register a tool with full metadata"""
    
    def list_tools(self) -> List[Tuple[str, str]]:
        """Return [(tool_id, description)] for discovery"""
    
    def get_tool_info(self, tool_id: str) -> Optional[ToolMetadata]:
        """Return full API specification for a tool"""
    
    def list_tools_by_category(self, category: str) -> List[Tuple[str, str]]:
        """Return tools filtered by category"""
    
    def execute_tool(self, tool_id: str, **kwargs) -> Any:
        """Execute a tool by ID with parameters"""
```

### 3. Dynamic Tool Discovery Flow
1. **Agent Initialization**: Agent receives core tools + discoverable tools list
2. **Tool Discovery**: Agent calls `list_tools()` to see available tools
3. **API Specification**: Agent calls `get_tool_info(tool_id)` for specific tool details
4. **Tool Execution**: Agent calls `execute_tool(tool_id, **params)` with proper parameters

### 4. Integration Points
- **BrieflyAgent**: Modified to support both immediate and discoverable tools
- **GetTools**: Enhanced to use the new registry system
- **Tool Categories**: Organized by functionality (data, search, drafts, etc.)

## Benefits
- **Dynamic Discovery**: Agents can discover new tools without code changes
- **Self-Documenting**: Each tool provides its own API specification
- **Extensible**: New tools can be registered at runtime
- **Organized**: Tools are categorized by functionality
- **Backward Compatible**: Existing workflows continue to work

## Migration Strategy
1. Create new registry infrastructure alongside existing system
2. Gradually migrate tools to new registry
3. Update agent to use new discovery system
4. Remove old hardcoded implementations
5. Maintain backward compatibility throughout
