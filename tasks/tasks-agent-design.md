# Task List: Agent Design Implementation

## Relevant Files

- `services/chat/workflow_agent.py` - New LlamaIndex Workflow-based agent implementation replacing current architecture.
- `services/chat/tests/test_workflow_agent.py` - Unit tests for the workflow agent.
- `services/chat/events.py` - Event definitions for the workflow system (UserInput, PlanGenerated, ToolExecuted, etc.).
- `services/chat/tests/test_events.py` - Unit tests for event definitions.
- `services/chat/steps/` - Directory containing workflow step implementations.
- `services/chat/steps/planner_step.py` - Planner workflow step that converts user intent into execution plans.
- `services/chat/tests/test_planner_step.py` - Unit tests for planner step.
- `services/chat/steps/tool_executor_step.py` - Tool execution workflow step with parallel execution support.
- `services/chat/tests/test_tool_executor_step.py` - Unit tests for tool executor step.
- `services/chat/steps/clarifier_step.py` - Clarification workflow step for handling missing information.
- `services/chat/tests/test_clarifier_step.py` - Unit tests for clarifier step.
- `services/chat/steps/draft_builder_step.py` - Draft creation workflow step.
- `services/chat/tests/test_draft_builder_step.py` - Unit tests for draft builder step.
- `services/chat/streaming.py` - Streaming progress updates and status messages to users.
- `services/chat/tests/test_streaming.py` - Unit tests for streaming functionality.
- `services/chat/context_manager.py` - Context accumulation and state management across workflow steps.
- `services/chat/tests/test_context_manager.py` - Unit tests for context manager.
- `services/chat/tool_integration.py` - Enhanced tool registry integration with workflow system.
- `services/chat/tests/test_tool_integration.py` - Unit tests for tool integration.
- `services/chat/legacy_adapter.py` - Adapter to maintain compatibility with existing ChatAgentManager interface.
- `services/chat/tests/test_legacy_adapter.py` - Unit tests for legacy adapter.

### Notes

- Unit tests should be placed alongside the test subfolder of the service they are testing.
- Use `pytest services/chat/tests/` to run all chat service tests.
- The workflow system should maintain backward compatibility with existing APIs during transition.
- Streaming functionality needs integration testing with services/demos/chat.py.

## Tasks

- [ ] 1. Design and Implement LlamaIndex Workflow Event System
  - [x] 1.1 Create event definitions in `services/chat/events.py` with base Event classes
  - [x] 1.2 Define UserInputEvent for incoming user messages with thread_id, user_id, message, and metadata
  - [x] 1.3 Define PlanGeneratedEvent containing execution plan with task groups and confidence levels
  - [ ] 1.4 Define ToolExecutionStartedEvent and ToolExecutionCompletedEvent for tool lifecycle tracking
  - [ ] 1.5 Define ClarificationNeededEvent for routing questions to users
  - [ ] 1.6 Define ClarificationReceivedEvent for routing user answers back to clarifier
  - [ ] 1.7 Define DraftCreatedEvent and DraftUpdatedEvent for draft lifecycle management
  - [ ] 1.8 Define StreamingStatusEvent for progress updates ("Retrieving calendar availability", etc.)
  - [ ] 1.9 Create event validation and serialization methods for persistence and debugging
  - [ ] 1.10 Write comprehensive unit tests for all event classes in `services/chat/tests/test_events.py`

- [ ] 2. Create Core Workflow Steps Architecture
  - [ ] 2.1 Create base workflow step class with common functionality and error handling
  - [ ] 2.2 Implement PlannerStep in `services/chat/steps/planner_step.py`
    - [ ] 2.2.1 Create LLM-based planner that converts user intent into structured execution plans
    - [ ] 2.2.2 Implement confidence assessment and parallel execution strategy analysis
    - [ ] 2.2.3 Add assumption tracking and clarification requirement detection
    - [ ] 2.2.4 Integrate with user preference learning from chat history
  - [ ] 2.3 Implement ToolExecutorStep in `services/chat/steps/tool_executor_step.py`
    - [ ] 2.3.1 Create parallel tool execution engine with asyncio support
    - [ ] 2.3.2 Implement tool result aggregation and error handling
    - [ ] 2.3.3 Add progress streaming during long-running tool operations
    - [ ] 2.3.4 Create tool dependency resolution for sequential vs parallel execution
  - [ ] 2.4 Implement ClarifierStep in `services/chat/steps/clarifier_step.py`
    - [ ] 2.4.1 Create LLM-based question generation from missing information context
    - [ ] 2.4.2 Implement user response routing back to workflow (not planner)
    - [ ] 2.4.3 Add clarification context accumulation and response validation
    - [ ] 2.4.4 Create timeout handling and fallback strategies for unanswered questions
  - [ ] 2.5 Implement DraftBuilderStep in `services/chat/steps/draft_builder_step.py`
    - [ ] 2.5.1 Create draft generation logic using accumulated context and tool results
    - [ ] 2.5.2 Implement draft templating system for emails, calendar events, and changes
    - [ ] 2.5.3 Add draft versioning and update tracking
    - [ ] 2.5.4 Create draft validation and completeness checking
  - [ ] 2.6 Write unit tests for all workflow steps in `services/chat/tests/`

- [ ] 3. Implement Tool Integration and Execution Engine
  - [ ] 3.1 Create enhanced ToolRegistry in `services/chat/tool_integration.py`
    - [ ] 3.1.1 Extend existing ToolRegistry from `llm_tools.py` with workflow-specific features
    - [ ] 3.1.2 Add tool metadata for parallel execution hints and dependencies
    - [ ] 3.1.3 Implement tool result caching and invalidation strategies
    - [ ] 3.1.4 Create tool execution timeout and retry logic
  - [ ] 3.2 Integrate existing tools with workflow system
    - [ ] 3.2.1 Wrap `get_calendar_events`, `get_emails`, `get_notes`, `get_documents` for workflow
    - [ ] 3.2.2 Wrap draft creation tools (`create_draft_email`, `create_draft_calendar_event`, etc.)
    - [ ] 3.2.3 Add progress streaming hooks to each tool execution
    - [ ] 3.2.4 Implement user token passing and service authentication in workflow context
  - [ ] 3.3 Create tool execution monitoring and metrics
    - [ ] 3.3.1 Add execution time tracking and performance metrics
    - [ ] 3.3.2 Implement error rate monitoring and alerting
    - [ ] 3.3.3 Create tool usage analytics for optimization
  - [ ] 3.4 Write unit tests for tool integration in `services/chat/tests/test_tool_integration.py`

- [ ] 4. Build Streaming Progress and Communication Layer
  - [ ] 4.1 Create streaming infrastructure in `services/chat/streaming.py`
    - [ ] 4.1.1 Implement WebSocket or SSE connection management for real-time updates
    - [ ] 4.1.2 Create message routing system for progress updates vs clarification questions
    - [ ] 4.1.3 Add message queuing and delivery confirmation
    - [ ] 4.1.4 Implement connection recovery and message replay on reconnect
  - [ ] 4.2 Create progress update system
    - [ ] 4.2.1 Define standard progress messages ("Retrieving calendar availability", "Looking up emails", etc.)
    - [ ] 4.2.2 Implement progress percentage tracking for multi-step operations
    - [ ] 4.2.3 Add estimated time remaining calculations
    - [ ] 4.2.4 Create progress update aggregation for parallel operations
  - [ ] 4.3 Implement bidirectional clarification routing
    - [ ] 4.3.1 Route clarification questions to user interface without interrupting workflow
    - [ ] 4.3.2 Route user clarification responses back to ClarifierStep (not PlannerStep)
    - [ ] 4.3.3 Add question context preservation and response validation
    - [ ] 4.3.4 Implement multi-turn clarification conversations
  - [ ] 4.4 Create context manager in `services/chat/context_manager.py`
    - [ ] 4.4.1 Implement conversation context accumulation across workflow steps
    - [ ] 4.4.2 Add user preference tracking and learning
    - [ ] 4.4.3 Create context persistence and recovery mechanisms
    - [ ] 4.4.4 Implement context cleanup and memory management
  - [ ] 4.5 Integration test streaming with `services/demos/chat.py`
  - [ ] 4.6 Write unit tests for streaming and context management

- [ ] 5. Create Legacy Compatibility and Migration Path
  - [ ] 5.1 Create legacy adapter in `services/chat/legacy_adapter.py`
    - [ ] 5.1.1 Implement ChatAgentManager interface compatibility
    - [ ] 5.1.2 Create workflow orchestration behind existing API methods
    - [ ] 5.1.3 Add seamless migration from current chat_agent.py and llama_manager.py
    - [ ] 5.1.4 Preserve existing memory management and tool distribution logic
  - [ ] 5.2 Create main workflow orchestrator in `services/chat/workflow_agent.py`
    - [ ] 5.2.1 Implement main LlamaIndex Workflow class coordinating all steps
    - [ ] 5.2.2 Add workflow state management and persistence
    - [ ] 5.2.3 Create workflow recovery and error handling
    - [ ] 5.2.4 Implement workflow metrics and monitoring
  - [ ] 5.3 Update existing integration points
    - [ ] 5.3.1 Update `services/chat/api.py` to support both legacy and new workflow systems
    - [ ] 5.3.2 Update `services/chat/main.py` to initialize workflow system
    - [ ] 5.3.3 Create feature flags for gradual rollout of workflow system
    - [ ] 5.3.4 Add backward compatibility tests ensuring existing functionality works
  - [ ] 5.4 Create migration documentation and examples
    - [ ] 5.4.1 Document API differences between legacy and workflow systems
    - [ ] 5.4.2 Create example usage patterns for new workflow system
    - [ ] 5.4.3 Add troubleshooting guide for common migration issues
  - [ ] 5.5 Write comprehensive integration tests in `services/chat/tests/test_legacy_adapter.py` and `services/chat/tests/test_workflow_agent.py` 