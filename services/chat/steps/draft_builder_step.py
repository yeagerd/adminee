"""
DraftBuilderStep implementation for LlamaIndex Workflow-based chat agent.

This module implements final draft creation and assembly, taking tool results
and clarification context to generate polished responses to user requests.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from llama_index.core.workflow import Context, step
from llama_index.core.llms import LLM

from .base_step import BaseWorkflowStep
from services.chat.events import (
    ToolResultsForDrafterEvent,
    ClarificationDraftUnblockedEvent,
    DraftCreatedEvent,
    DraftUpdatedEvent,
    WorkflowMetadata
)


class DraftBuilderStep(BaseWorkflowStep):
    """
    Workflow step that creates final drafts from tool results and context.
    
    The DraftBuilderStep is responsible for:
    - Assembling tool results into coherent drafts
    - Incorporating clarification context and user preferences
    - Generating polished, professional responses
    - Handling multiple draft formats (emails, documents, summaries)
    - Quality assurance and consistency checking
    - Learning from user feedback on draft quality
    """
    
    def __init__(self, llm: LLM, **kwargs):
        """Initialize the draft builder step with LLM."""
        super().__init__(llm=llm, **kwargs)
        self._draft_templates = {}  # Template library for different draft types
        self._user_style_preferences = {}  # Learned user writing style preferences
        self._quality_metrics = {}  # Track draft quality scores
        self._draft_versions = {}  # Track draft versions per thread
        self._draft_history = {}  # Track draft update history
    
    @step
    async def run(self, ctx: Context, **kwargs) -> None:
        """Execute draft building logic based on the incoming event."""
        if "tool_results_for_drafter" in kwargs:
            await self._handle_tool_results_for_draft(ctx, kwargs["tool_results_for_drafter"])
        elif "clarification_draft_unblocked" in kwargs:
            await self._handle_clarification_draft_unblocked(ctx, kwargs["clarification_draft_unblocked"])
        else:
            self.logger.warning(f"Unexpected event types in DraftBuilderStep: {list(kwargs.keys())}")
    
    async def _handle_tool_results_for_draft(self, ctx: Context, event: ToolResultsForDrafterEvent) -> None:
        """Handle tool results ready for draft creation."""
        self.validate_required_fields(
            event, 
            ["thread_id", "user_id", "tool_results", "draft_context"]
        )
        
        self.logger.info(f"Creating draft from {len(event.tool_results)} tool results")
        
        # Update context with draft creation start
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "draft_creation_started": True,
                "tool_results_count": len(event.tool_results),
                "draft_creation_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        try:
            # Create draft from tool results
            draft_content = await self._create_draft_from_tools(
                event.tool_results,
                event.draft_context,
                event.user_id
            )
            
            # Validate draft completeness and quality
            validation_result = await self._validate_draft_completeness(
                draft_content,
                event.tool_results,
                event.draft_context
            )
            
            # Add versioning information
            version_info = self._create_draft_version(
                event.thread_id,
                draft_content,
                "tool_results"
            )
            draft_content.update(version_info)
            
            # Update context with draft completion
            await self.emit_context_update(
                ctx,
                event.thread_id,
                event.user_id,
                {
                    "draft_created_from_tools": True,
                    "draft_length": len(draft_content.get("content", "")),
                    "draft_type": draft_content.get("type", "unknown"),
                    "draft_version": draft_content.get("version", 1),
                    "validation_score": validation_result.get("score", 0.0),
                    "completion_timestamp": datetime.now().isoformat()
                }
            )
            
            # Emit draft created event
            await self._emit_draft_created(
                ctx,
                event,
                draft_content,
                "tool_results"
            )
            
        except Exception as e:
            self.logger.error(f"Draft creation from tools failed: {e}", exc_info=True)
            
            # Emit error draft
            await self._emit_error_draft(
                ctx,
                event,
                f"Failed to create draft: {str(e)}"
            )
    
    async def _handle_clarification_draft_unblocked(
        self, 
        ctx: Context, 
        event: ClarificationDraftUnblockedEvent
    ) -> None:
        """Handle draft creation after clarification unblocked drafting."""
        self.validate_required_fields(
            event, 
            ["thread_id", "user_id", "draft_context", "clarification_insights"]
        )
        
        self.logger.info("Creating draft from clarification context")
        
        # Update context with clarification-based draft start
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "draft_from_clarification_started": True,
                "clarification_insights_count": len(event.clarification_insights),
                "draft_timestamp": datetime.now().isoformat()
            }
        )
        
        try:
            # Create draft from clarification context
            draft_content = await self._create_draft_from_clarification(
                event.draft_context,
                event.clarification_insights,
                event.user_id
            )
            
            # Validate draft completeness and quality
            validation_result = await self._validate_draft_completeness(
                draft_content,
                {},  # No tool results for clarification-based drafts
                event.draft_context
            )
            
            # Add versioning information
            version_info = self._create_draft_version(
                event.thread_id,
                draft_content,
                "clarification"
            )
            draft_content.update(version_info)
            
            # Update context with draft completion
            await self.emit_context_update(
                ctx,
                event.thread_id,
                event.user_id,
                {
                    "draft_created_from_clarification": True,
                    "draft_length": len(draft_content.get("content", "")),
                    "draft_type": draft_content.get("type", "unknown"),
                    "draft_version": draft_content.get("version", 1),
                    "validation_score": validation_result.get("score", 0.0),
                    "completion_timestamp": datetime.now().isoformat()
                }
            )
            
            # Emit draft created event
            await self._emit_draft_created(
                ctx,
                event,
                draft_content,
                "clarification"
            )
            
        except Exception as e:
            self.logger.error(f"Draft creation from clarification failed: {e}", exc_info=True)
            
            # Emit error draft
            await self._emit_error_draft(
                ctx,
                event,
                f"Failed to create draft from clarification: {str(e)}"
            )
    
    async def _create_draft_from_tools(
        self,
        tool_results: Dict[str, Any],
        draft_context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Create draft content from tool results."""
        # Analyze tool results to determine draft type and content
        draft_analysis = self._analyze_draft_requirements(tool_results, draft_context)
        
        # Get user style preferences
        user_style = self._get_user_style_preferences(user_id)
        
        # Build draft prompt
        draft_prompt = self._build_draft_prompt(
            tool_results,
            draft_context,
            draft_analysis,
            user_style
        )
        
        # Generate draft using LLM
        draft_content = await self.safe_llm_call(
            draft_prompt,
            max_tokens=2000,
            temperature=0.3,  # Slightly more creative for draft generation
            operation_name="draft_generation"
        )
        
        # Parse and structure the draft
        structured_draft = self._structure_draft_content(
            draft_content,
            draft_analysis["type"],
            tool_results
        )
        
        return structured_draft
    
    async def _create_draft_from_clarification(
        self,
        draft_context: Dict[str, Any],
        clarification_insights: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Create draft content from clarification context."""
        # Merge draft context with clarification insights
        combined_context = {
            **draft_context,
            "clarification_provided": clarification_insights
        }
        
        # Get user style preferences
        user_style = self._get_user_style_preferences(user_id)
        
        # Build clarification-based draft prompt
        draft_prompt = self._build_clarification_draft_prompt(
            combined_context,
            clarification_insights,
            user_style
        )
        
        # Generate draft using LLM
        draft_content = await self.safe_llm_call(
            draft_prompt,
            max_tokens=2000,
            temperature=0.3,
            operation_name="clarification_draft_generation"
        )
        
        # Structure the draft
        structured_draft = self._structure_draft_content(
            draft_content,
            "clarification_response",
            {}
        )
        
        return structured_draft
    
    def _analyze_draft_requirements(
        self,
        tool_results: Dict[str, Any],
        draft_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze tool results to determine draft requirements."""
        analysis = {
            "type": "general_response",
            "format": "text",
            "tone": "professional",
            "length": "medium",
            "key_elements": []
        }
        
        # Analyze tool results to determine draft type
        if any("email" in tool_name.lower() for tool_name in tool_results.keys()):
            analysis["type"] = "email_draft"
            analysis["key_elements"].append("email_structure")
        
        if any("calendar" in tool_name.lower() for tool_name in tool_results.keys()):
            analysis["type"] = "meeting_summary"
            analysis["key_elements"].append("meeting_details")
        
        if any("document" in tool_name.lower() for tool_name in tool_results.keys()):
            analysis["type"] = "document_summary"
            analysis["key_elements"].append("document_analysis")
        
        # Check draft context for additional requirements
        if "urgent" in str(draft_context).lower():
            analysis["tone"] = "urgent"
        
        if "formal" in str(draft_context).lower():
            analysis["tone"] = "formal"
        
        return analysis
    
    def _build_draft_prompt(
        self,
        tool_results: Dict[str, Any],
        draft_context: Dict[str, Any],
        draft_analysis: Dict[str, Any],
        user_style: Dict[str, Any]
    ) -> str:
        """Build prompt for draft generation."""
        # Summarize tool results
        tool_summary = self._summarize_tool_results(tool_results)
        
        return f"""
Create a {draft_analysis['type']} based on the following information:

Tool Results Summary:
{tool_summary}

Draft Context:
{json.dumps(draft_context, indent=2)}

Draft Requirements:
- Type: {draft_analysis['type']}
- Format: {draft_analysis['format']}
- Tone: {draft_analysis['tone']}
- Length: {draft_analysis['length']}
- Key Elements: {', '.join(draft_analysis['key_elements'])}

User Style Preferences:
{json.dumps(user_style, indent=2)}

Create a well-structured, professional draft that:
1. Addresses the user's request clearly
2. Incorporates relevant information from tool results
3. Follows the specified tone and format
4. Is appropriate for the intended audience
5. Includes all necessary details

Draft:
"""
    
    def _build_clarification_draft_prompt(
        self,
        combined_context: Dict[str, Any],
        clarification_insights: Dict[str, Any],
        user_style: Dict[str, Any]
    ) -> str:
        """Build prompt for clarification-based draft generation."""
        return f"""
Create a response based on clarification provided by the user:

Context Information:
{json.dumps(combined_context, indent=2)}

User Clarification Insights:
{json.dumps(clarification_insights, indent=2)}

User Style Preferences:
{json.dumps(user_style, indent=2)}

Create a helpful response that:
1. Acknowledges the clarification provided
2. Addresses the user's clarified needs
3. Provides actionable next steps or information
4. Maintains appropriate tone and professionalism
5. Is clear and concise

Response:
"""
    
    def _structure_draft_content(
        self,
        raw_content: str,
        draft_type: str,
        tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure raw draft content into organized format."""
        structured_draft = {
            "type": draft_type,
            "content": raw_content,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "word_count": len(raw_content.split()),
                "character_count": len(raw_content),
                "source_tools": list(tool_results.keys())
            }
        }
        
        # Add type-specific structuring
        if draft_type == "email_draft":
            structured_draft["metadata"]["email_components"] = self._extract_email_components(raw_content)
        elif draft_type == "meeting_summary":
            structured_draft["metadata"]["meeting_elements"] = self._extract_meeting_elements(raw_content)
        elif draft_type == "document_summary":
            structured_draft["metadata"]["document_insights"] = self._extract_document_insights(raw_content)
        
        return structured_draft
    
    async def _emit_draft_created(
        self,
        ctx: Context,
        original_event,
        draft_content: Dict[str, Any],
        source: str
    ) -> None:
        """Emit draft created event."""
        event = DraftCreatedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=getattr(original_event, 'parent_request_event_id', None),
            draft_content=draft_content,
            draft_source=source,
            quality_score=self._calculate_draft_quality(draft_content),
            context_updates={
                "draft_created": True,
                "draft_type": draft_content.get("type"),
                "draft_length": draft_content.get("metadata", {}).get("word_count", 0)
            },
            metadata=self.create_metadata(
                confidence=0.9,
                priority="high"
            )
        )
        
        ctx.send_event(event)
        self.logger.info(f"Emitted draft created event: {draft_content.get('type')}")
    
    async def _emit_error_draft(
        self,
        ctx: Context,
        original_event,
        error_message: str
    ) -> None:
        """Emit error draft when creation fails."""
        error_draft = {
            "type": "error_response",
            "content": f"I apologize, but I encountered an error while creating your response: {error_message}. Please try again or provide additional details.",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "is_error": True,
                "error_message": error_message
            }
        }
        
        event = DraftCreatedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=getattr(original_event, 'parent_request_event_id', None),
            draft_content=error_draft,
            draft_source="error_handling",
            quality_score=0.3,  # Low quality score for error drafts
            context_updates={
                "draft_error": True,
                "error_message": error_message
            },
            metadata=self.create_metadata(
                confidence=0.3,
                priority="high"
            )
        )
        
        ctx.send_event(event)
        self.logger.info("Emitted error draft event")
    
    def _get_user_style_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user writing style preferences."""
        return self._user_style_preferences.get(user_id, {
            "tone": "professional",
            "formality": "standard",
            "length_preference": "concise",
            "include_details": True,
            "communication_style": "direct"
        })
    
    def _summarize_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """Create a summary of tool results for draft context."""
        summaries = []
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                if "calendar" in tool_name.lower():
                    summaries.append(f"Calendar: Retrieved scheduling information")
                elif "email" in tool_name.lower():
                    summaries.append(f"Email: Found relevant email context")
                elif "document" in tool_name.lower():
                    summaries.append(f"Documents: Analyzed relevant documents")
                else:
                    summaries.append(f"{tool_name}: Successfully retrieved information")
            else:
                summaries.append(f"{tool_name}: Unable to retrieve information")
        
        return "\\n".join(summaries)
    
    def _extract_email_components(self, content: str) -> Dict[str, Any]:
        """Extract email components from draft content."""
        # Simple extraction - in real implementation, this would be more sophisticated
        return {
            "has_subject": "subject:" in content.lower() or "re:" in content.lower(),
            "has_greeting": any(greeting in content.lower() for greeting in ["dear", "hello", "hi"]),
            "has_closing": any(closing in content.lower() for closing in ["regards", "sincerely", "best"]),
            "estimated_paragraphs": content.count("\\n\\n") + 1
        }
    
    def _extract_meeting_elements(self, content: str) -> Dict[str, Any]:
        """Extract meeting elements from draft content."""
        return {
            "has_date_time": any(word in content.lower() for word in ["date", "time", "when"]),
            "has_attendees": any(word in content.lower() for word in ["attendees", "participants", "who"]),
            "has_agenda": any(word in content.lower() for word in ["agenda", "topics", "discussion"]),
            "has_action_items": any(word in content.lower() for word in ["action", "next steps", "follow up"])
        }
    
    def _extract_document_insights(self, content: str) -> Dict[str, Any]:
        """Extract document insights from draft content."""
        return {
            "has_summary": "summary" in content.lower(),
            "has_key_points": any(word in content.lower() for word in ["key points", "highlights", "important"]),
            "has_conclusions": any(word in content.lower() for word in ["conclusion", "findings", "results"]),
            "estimated_sections": content.count("\\n#") + content.count("\\n##")
        }
    
    def _calculate_draft_quality(self, draft_content: Dict[str, Any]) -> float:
        """Calculate quality score for the draft."""
        base_score = 0.7
        
        metadata = draft_content.get("metadata", {})
        word_count = metadata.get("word_count", 0)
        
        # Adjust score based on content length
        if word_count < 10:
            base_score -= 0.3
        elif word_count > 50:
            base_score += 0.1
        
        # Adjust based on type-specific elements
        draft_type = draft_content.get("type", "")
        if draft_type == "email_draft":
            email_components = metadata.get("email_components", {})
            if email_components.get("has_greeting") and email_components.get("has_closing"):
                base_score += 0.1
        
        # Ensure score is within valid range
        return max(0.0, min(1.0, base_score))
    
    async def _validate_draft_completeness(
        self,
        draft_content: Dict[str, Any],
        tool_results: Dict[str, Any],
        draft_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate draft completeness and quality."""
        validation_result = {
            "score": 0.0,
            "issues": [],
            "suggestions": [],
            "is_complete": False
        }
        
        content = draft_content.get("content", "")
        draft_type = draft_content.get("type", "")
        
        # Basic content validation
        if len(content.strip()) < 10:
            validation_result["issues"].append("Draft content is too short")
            validation_result["suggestions"].append("Add more detail to the response")
        else:
            validation_result["score"] += 0.3
        
        # Type-specific validation
        if draft_type == "email_draft":
            validation_result.update(self._validate_email_draft(content))
        elif draft_type == "meeting_summary":
            validation_result.update(self._validate_meeting_summary(content, tool_results))
        elif draft_type == "document_summary":
            validation_result.update(self._validate_document_summary(content, tool_results))
        else:
            validation_result["score"] += 0.4  # Generic content gets base score
        
        # Check if all tool results were utilized
        if tool_results:
            utilized_tools = sum(1 for tool in tool_results.keys() 
                               if tool.lower() in content.lower())
            utilization_ratio = utilized_tools / len(tool_results)
            validation_result["score"] += utilization_ratio * 0.3
            
            if utilization_ratio < 0.5:
                validation_result["suggestions"].append("Consider incorporating more of the available information")
        
        # Determine completeness
        validation_result["is_complete"] = (
            validation_result["score"] >= 0.7 and 
            len(validation_result["issues"]) == 0
        )
        
        # Ensure score is within valid range
        validation_result["score"] = max(0.0, min(1.0, validation_result["score"]))
        
        return validation_result
    
    def _validate_email_draft(self, content: str) -> Dict[str, Any]:
        """Validate email draft specific requirements."""
        result = {"score": 0.0, "issues": [], "suggestions": []}
        
        # Check for greeting
        if any(greeting in content.lower() for greeting in ["dear", "hello", "hi"]):
            result["score"] += 0.15
        else:
            result["suggestions"].append("Consider adding a greeting")
        
        # Check for closing
        if any(closing in content.lower() for closing in ["regards", "sincerely", "best"]):
            result["score"] += 0.15
        else:
            result["suggestions"].append("Consider adding a professional closing")
        
        # Check for clear purpose
        if any(purpose in content.lower() for purpose in ["request", "inform", "follow up", "schedule"]):
            result["score"] += 0.1
        
        return result
    
    def _validate_meeting_summary(self, content: str, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate meeting summary specific requirements."""
        result = {"score": 0.0, "issues": [], "suggestions": []}
        
        # Check for key meeting elements
        has_date_time = any(word in content.lower() for word in ["date", "time", "when"])
        has_attendees = any(word in content.lower() for word in ["attendees", "participants"])
        has_agenda = any(word in content.lower() for word in ["agenda", "topics"])
        
        if has_date_time:
            result["score"] += 0.1
        else:
            result["suggestions"].append("Include meeting date and time")
        
        if has_attendees:
            result["score"] += 0.1
        else:
            result["suggestions"].append("Include meeting attendees")
        
        if has_agenda:
            result["score"] += 0.2
        else:
            result["suggestions"].append("Include meeting agenda or topics")
        
        return result
    
    def _validate_document_summary(self, content: str, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document summary specific requirements."""
        result = {"score": 0.0, "issues": [], "suggestions": []}
        
        # Check for summary elements
        has_summary = "summary" in content.lower()
        has_key_points = any(word in content.lower() for word in ["key points", "highlights"])
        has_conclusions = any(word in content.lower() for word in ["conclusion", "findings"])
        
        if has_summary:
            result["score"] += 0.15
        else:
            result["suggestions"].append("Include a clear summary section")
        
        if has_key_points:
            result["score"] += 0.15
        else:
            result["suggestions"].append("Highlight key points from the documents")
        
        if has_conclusions:
            result["score"] += 0.1
        else:
            result["suggestions"].append("Include conclusions or findings")
        
        return result
    
    def _create_draft_version(
        self,
        thread_id: str,
        draft_content: Dict[str, Any],
        source: str
    ) -> Dict[str, Any]:
        """Create version information for draft tracking."""
        # Initialize thread versioning if not exists
        if thread_id not in self._draft_versions:
            self._draft_versions[thread_id] = {
                "current_version": 0,
                "versions": []
            }
        
        # Increment version
        self._draft_versions[thread_id]["current_version"] += 1
        current_version = self._draft_versions[thread_id]["current_version"]
        
        # Create version info
        version_info = {
            "version": current_version,
            "created_at": datetime.now().isoformat(),
            "source": source,
            "parent_version": current_version - 1 if current_version > 1 else None
        }
        
        # Store version in history
        version_record = {
            "version": current_version,
            "content_hash": hash(draft_content.get("content", "")),
            "metadata": draft_content.get("metadata", {}),
            "source": source,
            "created_at": version_info["created_at"]
        }
        
        self._draft_versions[thread_id]["versions"].append(version_record)
        
        # Track in draft history
        if thread_id not in self._draft_history:
            self._draft_history[thread_id] = []
        
        self._draft_history[thread_id].append({
            "action": "created",
            "version": current_version,
            "source": source,
            "timestamp": version_info["created_at"],
            "changes": "Initial draft creation" if current_version == 1 else "Draft updated"
        })
        
        return version_info
    
    def _get_draft_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get draft history for a thread."""
        return self._draft_history.get(thread_id, [])
    
    def _get_draft_version(self, thread_id: str, version: int) -> Optional[Dict[str, Any]]:
        """Get specific draft version."""
        if thread_id not in self._draft_versions:
            return None
        
        versions = self._draft_versions[thread_id]["versions"]
        for version_record in versions:
            if version_record["version"] == version:
                return version_record
        
        return None 