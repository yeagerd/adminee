# 🧠 Briefly Agent System Design

## Overview


---

## 🏗️ Architecture


### Key Roles in the Loop

🧭 Planner
Converts user intent + context into a plan: sequence of actions (tool calls + clarifications)

⚙️ ToolExecutor
Executes planner’s actions
Hands off to:
Query tools (query_calendar, etc.)
Clarifier when clarify(...) is returned in the plan
Aggregates responses

💬 Clarifier
A lightweight LLM call that generates human-readable questions based on missing info
Sends to user, collects answer, and passes it back to the planner or context
🧺 Context Accumulator
Tracks all relevant knowledge gathered: query results, user clarifications, prior drafts, etc.

🧱 Draft Builder
When the agent has enough info, this module (usually an LLM call) generates a structured or partial draft
Optionally uses templating or reasoning

🔁 Loop Behavior

The Planner may be called repeatedly, especially if:
New clarifications change the context
Tool results invalidate prior assumptions (e.g. no available time slots)
You can:

Replan after every tool step (step-by-step, ReAct-style)
Batch plan (multi-step upfront), then loop only if a step fails or context updates


                   ┌────────────────────────────┐
                   │        User Request        │
                   └────────────┬───────────────┘
                                │
                        ┌───────▼────────┐
                        │    Planner     │◀───┐
                        └──────┬─────────┘    │ (Replan if needed)
         (Plan = actions)     │              │
         e.g.,                ▼              │
     - query_calendar        [Step N]        │
     - clarify            ┌────────────┐     │
     - create_draft/edit  │ ToolExecutor│────┘
                          └────┬───────┬┘
          ┌────────────────────┘       │
     ┌────▼────┐           ┌───────────▼────────────┐
     │ Query   │           │     Clarifier LLM      │
     │ Tools   │           └───────────┬────────────┘
     └────┬────┘                       │
          │                      ┌────▼────┐
          └─────────────────────▶│  User   │◀────┐
                                 │         │     │
                                 └────┬─────┘     │
                                      │           │
                        (Clarified input/data)    │
                                      ▼           │
                          ┌────────────────────┐  │
                          │   Context Accumulator│◀┘
                          └─────────┬────────────┘
                                    │
                            ┌───────▼────────┐
                            │  Draft Builder │
                            │ (LLM or Logic) │
                            └───────┬────────┘
                                    │
                         ┌──────────▼────────────┐
                         │ create/edit_draft(...)│
                         └──────────┬────────────┘
                                    │
                         ┌──────────▼────────┐
                         │ Draft Shown in UI │
                         └───────────────────┘

### 🔁 Summary of Flow

User Input → "Schedule meeting with Arjun"

Planner → plan: [query_calendar, clarify_missing_info, create_draft]

ToolExecutor → calls query_calendar

→ Result not enough → calls clarify(missing_time)

→ User responds: "Thursday at 3 works"

Context updated, Draft Builder generates meeting draft

ToolExecutor → calls create_draft(...)

Draft appears in UI ✅


## 🦙 LlamaIndex Integration Strategy

LlamaIndex's tool calling agent can **significantly simplify** our architecture while maintaining the sophisticated behaviors we need. Here's where we can leverage LlamaIndex vs where we need custom components:

### What LlamaIndex Handles Well (Use Built-in)

#### 1. Tool Orchestration & Execution
```python
from llama_index.agent import FunctionCallingLLM
from llama_index.tools import FunctionTool

# LlamaIndex handles this automatically
tools = [
    calendar_tools,
    email_tools, 
    document_tools
]
agent = FunctionCallingLLM(
    llm=OpenAI(model="gpt-4o-mini"), tools=tools, timeout=120, verbose=False
)

# Built-in parallel execution, error handling, retries
response = await agent.achat("Schedule follow-up with client team")
```


## 🧠 Natural Language Prompt Strategy

### Enhanced Executor Prompt

```text
You are Briefly, an AI administrative assistant that works efficiently and transparently.

Core Operating Principles:
- Execute tasks in parallel whenever possible
- Show confidence levels and reasoning clearly  
- Provide concise progress updates without overwhelming detail
- Ask for clarification only when genuinely uncertain
- Learn from user feedback and adapt behavior
- Handle interruptions gracefully
- Default to action rather than endless planning

Communication Style:
- Be direct and action-oriented
- Use confidence indicators: "I'm confident this is correct" vs "I need to verify this"
- Explain what you're doing, not just what you're thinking
- Provide time estimates when possible
- Offer alternatives when confidence is low

Response Format:
**Current Action:** [what you're doing now - be specific]
**Confidence:** [High/Medium/Low + brief explanation if not High]
**Progress:** [X/Y tasks complete, estimated Z minutes remaining]

[Natural explanation of what you found/did/need]

**Next:** [what happens next, any user input needed]

Tool calls: [if any - execute in parallel when possible]

Remember: Your job is to make progress efficiently while keeping the user informed and in control.
```

### Planner Agent Prompt

```text
You are a planning specialist for Briefly. Convert user requests into efficient, parallelizable execution plans.

Your output should optimize for:
- Parallel execution wherever possible
- Clear confidence assessment
- Minimal clarification needs
- User preference awareness

Output Format:
{
  "goal": "specific, measurable objective",
  "confidence": 0.0-1.0,
  "execution_strategy": "parallel_preferred|sequential_required", 
  "task_groups": [
    {
      "can_run_parallel": true,
      "tasks": [...],
      "estimated_duration": "2-3 minutes"
    }
  ],
  "assumptions": ["what I'm assuming to be true"],
  "clarifications": [
    {
      "question": "specific question",
      "blocking": false,
      "confidence_impact": 0.2
    }
  ]
}

Be decisive. Default to reasonable assumptions rather than asking obvious questions.
```

---

## 💾 State Management & Recovery

### Persistent State Schema

```json
{
  "session_id": "s_abc123",
  "user_id": "u_xyz789",
  "state": {
    "current_goal": "...",
    "execution_checkpoints": [...],
    "draft_history": [...],
    "tool_cache": {...},
    "user_preferences": {...},
    "interruption_state": null
  },
  "recovery_data": {
    "last_checkpoint": "2024-01-15T10:30:00Z",
    "pending_tasks": [...],
    "incomplete_clarifications": [...]
  }
}
```

### Recovery Mechanisms

```python
class StateRecovery:
    async def recover_from_interruption(self, session_id: str):
        """Restore execution state after crash/interruption"""
        state = await self.load_state(session_id)
        
        if state.interruption_state:
            return await self.resume_from_interruption(state)
        
        if state.pending_tasks:
            return await self.resume_execution(state.pending_tasks)
        
        return state.current_draft
    
    async def create_checkpoint(self, execution_context):
        """Save execution state at key points"""
        checkpoint = {
            "timestamp": datetime.utcnow(),
            "completed_tasks": execution_context.completed,
            "pending_tasks": execution_context.pending,
            "draft_state": execution_context.draft,
            "user_context": execution_context.user_preferences
        }
        await self.save_checkpoint(checkpoint)
```

---

## 📊 Quality Metrics & Learning

### Performance Metrics

```yaml
efficiency_metrics:
  - task_completion_time: avg_seconds_per_task_type
  - parallel_execution_ratio: concurrent_tasks / total_tasks
  - cache_hit_rate: cached_responses / total_tool_calls
  - user_interruption_rate: interruptions / sessions

quality_metrics:
  - user_approval_rate: approved_drafts / total_drafts
  - clarification_efficiency: resolved_clarifications / total_asked
  - confidence_accuracy: predicted_confidence vs actual_success
  - user_satisfaction_score: explicit_feedback_rating
```

### Adaptive Learning

```python
class UserPreferenceLearning:
    def learn_from_interaction(self, interaction_data):
        """Update user preferences based on behavior"""
        patterns = {
            "preferred_meeting_times": self.extract_time_preferences(interaction_data),
            "communication_style": self.analyze_feedback_patterns(interaction_data),
            "approval_thresholds": self.calculate_confidence_preferences(interaction_data),
            "workflow_shortcuts": self.identify_repeated_patterns(interaction_data)
        }
        return self.update_user_model(patterns)
```