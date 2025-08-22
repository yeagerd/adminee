# Briefly Agent Migration Tasks

This document tracks the migration from the multi-agent `CoordinatorAgent` system to a single `BrieflyAgent` design.

## Core Agent Changes

- [x] Rename `CoordinatorAgent` to `BrieflyAgent` in `services/chat/agents/coordinator_agent.py`
- [x] Remove multi-agent handoff logic and subagent coordination
- [x] Update agent description and system prompt for single-agent design
- [x] Move `BrieflyAgent` to its own file `services/chat/agents/briefly_agent.py`
- [x] Update agent to use new organized tools with pre-authenticated user context
- [x] Fix conversation context persistence between API calls

## Tooling Changes

- [x] Create `services/chat/tools/` package structure
- [x] Move web search tools to `services/chat/tools/web_tools.py`
- [x] Move Vespa-based search tools to `services/chat/tools/search_tools.py`
- [x] Move get tools and tool registry to `services/chat/tools/get_tools.py`
- [x] Move draft management tools to `services/chat/tools/draft_tools.py`
- [x] Create wrapper classes (`WebTools`, `SearchTools`, `GetTools`, `DraftTools`) with pre-authenticated user context
- [x] Update `BrieflyAgent` to use organized tools instead of importing from `llm_tools.py`
- [x] Ensure all tools have user_id injected at initialization for security

## Documentation Updates

- [x] Update `documentation/agent-design.md` to reflect single-agent architecture
- [x] Remove multi-agent coordination principles
- [x] Update architectural diagrams and flow descriptions
- [x] Document new tool organization and pre-authenticated context

## API Integration

- [x] Update `services/chat/agents/workflow_agent.py` to work with `BrieflyAgent` instead of multi-agent system
- [x] Update `services/chat/api.py` to instantiate `BrieflyAgent` instead of `WorkflowAgent`
- [x] Pass `vespa_endpoint` and `user_id` from `get_settings()` to the `BrieflyAgent` instantiation
- [x] Ensure streaming functionality works with the new `BrieflyAgent`
- [x] Update any remaining references to `CoordinatorAgent` or `WorkflowAgent`
- [x] Remove `services/chat/agents/workflow_agent.py` file
- [x] Restore critical database saving functionality (user messages and assistant responses)

## Testing

- [ ] Add/adjust unit tests for `BrieflyAgent` to cover its new tool calls
- [ ] Test tool initialization with pre-authenticated user context
- [ ] Verify streaming functionality with the new `BrieflyAgent`
- [ ] Update existing tests that directly instantiate `CoordinatorAgent` or rely on the multi-agent structure

## Cleanup

- [x] Remove `WorkflowAgent` and its related imports/logic from `services/chat/api.py`
- [x] Delete `services/chat/agents/workflow_agent.py`
- [x] Delete `services/demos/multi_agent_demo.py`
- [x] Delete `services/demos/workflow_agent_demo.py`
- [x] Delete `services/demos/README_chat_simple.md`
- [x] Delete `services/demos/README_workflow_agent.md`
- [x] Delete `services/chat/tests/test_workflow_agent.py`
- [x] Delete `services/chat/tests/test_multi_agent.py`
- [x] Update `services/demos/chat.py` to use `BrieflyAgent`
- [x] Delete `services/chat/agents/README_multi_agent.md`
- [x] Delete `services/chat/agents/calendar_agent.py`, `email_agent.py`, `document_agent.py`, `draft_agent.py`
- [x] Clean up any remaining multi-agent imports and references

## Code Quality

- [ ] Run `pytest`, `mypy services/`, `./fix`, and `tox` before commit
- [ ] Ensure all linter errors are resolved
- [ ] Verify type annotations are correct for new tool classes
- [ ] Test tool initialization and execution paths

## Current Status

✅ **Completed**: Tool organization, pre-authenticated user context, `BrieflyAgent` refactoring, `workflow_agent.py` update, API integration refactoring, demo and test file cleanup, multi-agent file cleanup
🔄 **In Progress**: Final validation and testing
⏳ **Pending**: Code quality checks and testing

## Notes

- Tools are now organized by functionality with pre-authenticated user context
- `BrieflyAgent` uses wrapper classes that inject user_id at initialization
- All legacy functions are maintained for backward compatibility
- The new design eliminates the need for subagents and handoffs
- `workflow_agent.py` has been completely removed
- The refactoring maintains the same functionality while providing a much cleaner, more secure, and better-organized architecture