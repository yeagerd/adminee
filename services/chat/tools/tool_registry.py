"""
Enhanced tool registry for dynamic tool discovery and API specification.

This module provides a comprehensive tool registry system that allows:
- Dynamic tool registration with full metadata
- Tool discovery via list_tools()
- API specification retrieval via get_tool_info()
- Categorized tool organization
- Tool execution through the registry
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Complete metadata for a tool including API specification."""
    
    tool_id: str
    description: str
    category: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    return_format: Dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = True
    service_dependency: Optional[str] = None
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ToolRegistry:
    """Enhanced registry for managing tool metadata and execution."""
    
    def __init__(self) -> None:
        self._tools: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}
        self._executors: Dict[str, Any] = {}
        logger.info("ToolRegistry initialized")
    
    def register_tool(self, tool_metadata: ToolMetadata, executor: Optional[Any] = None) -> None:
        """Register a tool with full metadata and optional executor function.
        
        Args:
            tool_metadata: Complete tool metadata
            executor: Optional function/object to execute the tool
        """
        tool_id = tool_metadata.tool_id
        
        if tool_id in self._tools:
            logger.warning(f"Tool {tool_id} already registered, updating metadata")
        
        self._tools[tool_id] = tool_metadata
        
        # Add to category
        category = tool_metadata.category
        if category not in self._categories:
            self._categories[category] = []
        if tool_id not in self._categories[category]:
            self._categories[category].append(tool_id)
        
        # Store executor if provided
        if executor is not None:
            self._executors[tool_id] = executor
        
        logger.info(f"Registered tool: {tool_id} in category: {category}")
    
    def list_tools(self) -> List[Tuple[str, str]]:
        """Return list of available tools as (tool_id, description) tuples.
        
        Returns:
            List of tuples containing tool ID and description
        """
        return [(tool_id, metadata.description) for tool_id, metadata in self._tools.items()]
    
    def list_tools_by_category(self, category: str) -> List[Tuple[str, str]]:
        """Return tools filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of tuples containing tool ID and description for the category
        """
        if category not in self._categories:
            return []
        
        return [
            (tool_id, self._tools[tool_id].description)
            for tool_id in self._categories[category]
            if tool_id in self._tools
        ]
    
    def get_tool_info(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get complete API specification for a tool.
        
        Args:
            tool_id: ID of the tool to get info for
            
        Returns:
            ToolMetadata object or None if tool not found
        """
        return self._tools.get(tool_id)
    
    def get_categories(self) -> List[str]:
        """Get list of available tool categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def execute_tool(self, tool_id: str, **kwargs: Any) -> Any:
        """Execute a tool by ID with parameters.
        
        Args:
            tool_id: ID of the tool to execute
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Result of tool execution
            
        Raises:
            ValueError: If tool not found
            RuntimeError: If tool execution fails
        """
        if tool_id not in self._tools:
            raise ValueError(f"Tool not found: {tool_id}")
        
        if tool_id not in self._executors:
            raise RuntimeError(f"No executor registered for tool: {tool_id}")
        
        try:
            executor = self._executors[tool_id]
            if callable(executor):
                result = executor(**kwargs)
            else:
                # Assume it's an object with an execute method
                result = executor.execute(**kwargs)
            
            logger.info(f"Successfully executed tool: {tool_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_id}: {e}")
            raise RuntimeError(f"Tool execution failed: {str(e)}")
    
    def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool from the registry.
        
        Args:
            tool_id: ID of the tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_id not in self._tools:
            return False
        
        # Remove from tools
        metadata = self._tools.pop(tool_id)
        
        # Remove from categories
        category = metadata.category
        if category in self._categories and tool_id in self._categories[category]:
            self._categories[category].remove(tool_id)
            if not self._categories[category]:
                del self._categories[category]
        
        # Remove executor
        if tool_id in self._executors:
            del self._executors[tool_id]
        
        logger.info(f"Unregistered tool: {tool_id}")
        return True
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools.
        
        Returns:
            Number of registered tools
        """
        return len(self._tools)
    
    def get_category_tool_count(self, category: str) -> int:
        """Get number of tools in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Number of tools in the category
        """
        return len(self._categories.get(category, []))
    
    def search_tools(self, query: str) -> List[Tuple[str, str]]:
        """Search tools by description or category.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching tools as (tool_id, description) tuples
        """
        query_lower = query.lower()
        matches = []
        
        for tool_id, metadata in self._tools.items():
            if (query_lower in metadata.description.lower() or
                query_lower in metadata.category.lower() or
                query_lower in tool_id.lower()):
                matches.append((tool_id, metadata.description))
        
        return matches
    
    def export_registry(self) -> Dict[str, Any]:
        """Export the complete registry state.
        
        Returns:
            Dictionary containing all registry data
        """
        return {
            "tools": {tool_id: metadata.to_dict() for tool_id, metadata in self._tools.items()},
            "categories": self._categories.copy(),
            "total_tools": self.get_tool_count(),
            "categories_count": len(self._categories)
        }
    
    def import_registry(self, registry_data: Dict[str, Any]) -> None:
        """Import registry state from exported data.
        
        Args:
            registry_data: Registry data from export_registry()
        """
        # Clear existing registry
        self._tools.clear()
        self._categories.clear()
        self._executors.clear()
        
        # Import tools
        for tool_id, tool_data in registry_data.get("tools", {}).items():
            metadata = ToolMetadata(**tool_data)
            self.register_tool(metadata)
        
        # Import categories
        self._categories = registry_data.get("categories", {})
        
        logger.info(f"Imported registry with {self.get_tool_count()} tools")


# Global registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance.
    
    Returns:
        Global ToolRegistry instance
    """
    return _global_registry


def register_tool(metadata: ToolMetadata, executor: Optional[Any] = None) -> None:
    """Register a tool in the global registry.
    
    Args:
        metadata: Tool metadata
        executor: Optional executor function/object
    """
    _global_registry.register_tool(metadata, executor)


def list_tools() -> List[Tuple[str, str]]:
    """List all tools in the global registry.
    
    Returns:
        List of (tool_id, description) tuples
    """
    return _global_registry.list_tools()


def get_tool_info(tool_id: str) -> Optional[ToolMetadata]:
    """Get tool info from the global registry.
    
    Args:
        tool_id: Tool ID to look up
        
    Returns:
        ToolMetadata or None if not found
    """
    return _global_registry.get_tool_info(tool_id)
