# Briefly Agent Migration Tasks

## Overview
The current implementation has a misunderstanding about the purpose of `get_tools.py`. It was implemented to return only get* tools when the goal was to create a dynamic tool discovery system. The FunctionAgent should be provided with some tools initially, plus a list of more tools [(tool_id, tool_description)] and can request the API for how to call a tool via `get_tool`, which will return the instructions for how to invoke that tool to the Agent.

Additionally, `llm_tools.py` has become a monolithic file that needs to be broken down into organized tool categories.

## Phase 1: Fix Tool Discovery Architecture

### [x] Task 1.1: Understand Current Architecture
- [x] Read and document how `BrieflyAgent` currently works in `services/chat/agents/briefly_agent.py`
- [x] Document how tools are currently registered and used (lines 269-389)
- [x] Understand the difference between immediate tools vs discoverable tools
- [x] Document the current `GetTools` class implementation in `services/chat/tools/get_tools.py`

### [x] Task 1.2: Design New Tool Discovery System
- [x] Create a design document for the new tool discovery architecture
- [x] Define the interface for tool metadata: `(tool_id, tool_description)`
- [x] Design the `get_tool` function that returns API instructions for a named tool
- [x] Design how tools will be registered in a discoverable registry
- [x] Plan backward compatibility during migration

### [x] Task 1.3: Create Tool Registry Infrastructure
- [x] Create `services/chat/tools/tool_registry.py` with:
  - [x] `ToolMetadata` dataclass for (id, description, parameters, examples)
  - [x] `ToolRegistry` class to store and manage tool metadata
  - [x] `register_tool()` method to add tools to registry
  - [x] `list_tools()` method to return available tools list
  - [x] `get_tool_info(tool_id)` method to return full API specification
- [x] Add JSON schema generation for tool parameters
- [x] Add example usage generation for each tool

### [x] Task 1.4: Implement Dynamic Tool Discovery
- [x] Modify `GetTools` class to use the new registry system
- [x] Implement `get_tool(tool_id: str)` that returns:
  - [x] Tool description and purpose
  - [x] Parameter specifications with types and descriptions
  - [x] Example usage patterns
  - [x] Return value format
- [x] Update `list_tools()` to return `[(tool_id, description)]` format
- [x] Ensure `execute_tool()` works with the registry

### [x] Task 1.5: Update BrieflyAgent Integration
- [x] Modify `create_briefly_agent_tools()` to provide initial core tools
- [x] Add discoverable tools list to agent initialization
- [x] Update agent system prompt to explain tool discovery workflow
- [x] Test that agent can discover and use tools dynamically

## Phase 2: Reorganize llm_tools.py by Category

### [ ] Task 2.1: Audit Current llm_tools.py Content
- [ ] Create inventory of all functions/classes in `services/chat/agents/llm_tools.py`:
  - [ ] Draft management functions (lines 25-348)
  - [ ] Document retrieval functions (lines 351-500) 
  - [ ] Note retrieval functions (lines 503-648)
  - [ ] Vespa search tools (lines 651-928)
  - [ ] User data search tools (lines 930-1044)
  - [ ] Semantic search tools (lines 1047-1137)
  - [ ] Web search tools (lines 1140-1208)
  - [ ] Generic tool classes (lines 1211-1242)
  - [ ] Calendar event functions (lines 1262-1516)
  - [ ] Email functions (lines 1520-1679)
  - [ ] Tool registry (lines 1683-1795)
  - [ ] Utility functions (lines 1799-1882)

### [ ] Task 2.2: Create Draft Management Tools
- [ ] Create `services/chat/tools/draft_tools.py` with comprehensive draft management:
  - [ ] Move all `create_draft_*` functions from llm_tools.py
  - [ ] Move all `get_draft_*` functions from llm_tools.py  
  - [ ] Move all `has_draft_*` functions from llm_tools.py
  - [ ] Move all `delete_draft_*` functions from llm_tools.py
  - [ ] Move `clear_all_drafts` function from llm_tools.py
  - [ ] Ensure `DraftTools` class integrates all functions properly
  - [ ] Add proper error handling and logging
  - [ ] Register all draft tools in the tool registry

### [ ] Task 2.3: Create Data Retrieval Tools  
- [ ] Create `services/chat/tools/data_tools.py` for data access:
  - [ ] Move `get_documents` function from llm_tools.py
  - [ ] Move `get_notes` function from llm_tools.py
  - [ ] Move `get_calendar_events` function from llm_tools.py  
  - [ ] Move `get_emails` function from llm_tools.py
  - [ ] Create `DataTools` class to organize these functions
  - [ ] Add integration checking logic for user permissions
  - [ ] Register all data tools in the tool registry
  - [ ] Update imports in existing files

### [ ] Task 2.4: Consolidate Search Tools
- [ ] Move remaining search classes from llm_tools.py to `services/chat/tools/search_tools.py`:
  - [ ] Move `VespaSearchTool` class (if not already moved)
  - [ ] Move `UserDataSearchTool` class (if not already moved) 
  - [ ] Move `SemanticSearchTool` class (if not already moved)
  - [ ] Ensure all search tools are integrated in `SearchTools` class
  - [ ] Register all search variants in the tool registry
  - [ ] Add comprehensive search documentation

### [ ] Task 2.5: Enhance Web Tools
- [ ] Move `WebSearchTool` from llm_tools.py to `services/chat/tools/web_tools.py` (if not already moved)
- [ ] Enhance `WebTools` class with additional web capabilities
- [ ] Register web tools in the tool registry
- [ ] Add error handling for network issues

### [ ] Task 2.6: Create Utility Tools
- [ ] Create `services/chat/tools/utility_tools.py` for helper functions:
  - [ ] Move `format_event_time_for_display` function from llm_tools.py
  - [ ] Move any other utility/formatting functions
  - [ ] Create `UtilityTools` class to organize utilities
  - [ ] Register utility tools in the tool registry

### [ ] Task 2.7: Update Tool Registry in get_tools.py
- [ ] Move the enhanced `ToolRegistry` class from llm_tools.py to `services/chat/tools/get_tools.py`
- [ ] Remove duplicate `ToolRegistry` implementation
- [ ] Ensure all tool categories are properly registered
- [ ] Update `GetTools` class to use the consolidated registry

## Phase 3: Integration and Testing

### [ ] Task 3.1: Update Import Structure
- [ ] Update `services/chat/tools/__init__.py` to include all new tool classes:
  - [ ] Add `DataTools` export
  - [ ] Add `UtilityTools` export  
  - [ ] Add `ToolRegistry` export
- [ ] Update all files that import from llm_tools.py:
  - [ ] Update imports in `services/chat/agents/briefly_agent.py`
  - [ ] Update imports in test files
  - [ ] Search for any other references to llm_tools functions

### [ ] Task 3.2: Clean Up llm_tools.py
- [ ] Remove all functions that have been moved to other files
- [ ] Add deprecation warnings for any remaining functions
- [ ] Update docstring to indicate the file is being phased out
- [ ] Consider renaming to `legacy_tools.py` or removing entirely

### [ ] Task 3.3: Update Agent Registration
- [ ] Modify `create_briefly_agent_tools()` in `services/chat/agents/briefly_agent.py`:
  - [ ] Initialize all new tool classes (`DataTools`, `UtilityTools`, etc.)
  - [ ] Register all tools in the central registry
  - [ ] Provide discoverable tools list to the agent
  - [ ] Update tool wrapper functions to use new classes

### [ ] Task 3.4: Update Tests
- [ ] Update existing tests to use new tool structure:
  - [ ] Update imports in test files
  - [ ] Modify test setup to use new tool classes
  - [ ] Update mocking to work with tool registry
- [ ] Create new tests for tool discovery functionality:
  - [ ] Test `get_tool()` returns proper API specifications
  - [ ] Test `list_tools()` returns correct tool metadata
  - [ ] Test dynamic tool execution through registry

### [ ] Task 3.5: Documentation Updates
- [ ] Update README files to reflect new tool organization
- [ ] Create documentation for the tool discovery system
- [ ] Document each tool category and its purpose
- [ ] Add examples of how to register new tools
- [ ] Update API documentation

## Phase 4: Validation and Deployment

### [ ] Task 4.1: End-to-End Testing
- [ ] Test agent can discover tools using `list_tools()`
- [ ] Test agent can get tool specifications using `get_tool(tool_id)`
- [ ] Test agent can execute discovered tools successfully
- [ ] Test all existing workflows still function correctly
- [ ] Test error handling for unknown/invalid tools

### [ ] Task 4.2: Performance Validation
- [ ] Ensure tool discovery doesn't add significant latency
- [ ] Verify memory usage is reasonable with tool registry
- [ ] Test with multiple concurrent agent instances

### [ ] Task 4.3: Backward Compatibility
- [ ] Ensure existing API calls continue to work
- [ ] Test that current agent workflows are unaffected
- [ ] Verify all tests pass with new architecture

### [ ] Task 4.4: Code Review and Refinement
- [ ] Review all new code for quality and consistency
- [ ] Ensure proper error handling throughout
- [ ] Verify logging is comprehensive and useful
- [ ] Check that type hints are complete and correct

## Notes for Implementation

- **Priority**: Phase 1 is highest priority as it fixes the core architectural misunderstanding
- **Testing**: Each phase should include unit tests and integration tests
- **Documentation**: Update docstrings and type hints as you go
- **Error Handling**: Ensure robust error handling throughout the migration
- **Logging**: Add appropriate logging for debugging and monitoring
- **Type Safety**: Maintain strong typing throughout the new architecture

