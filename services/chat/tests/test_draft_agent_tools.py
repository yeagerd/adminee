"""
Test DraftAgent tool configuration.

This test verifies that the DraftAgent has the correct tools and doesn't
expose the problematic calendar change tools that cause LLM confusion.
"""


from services.chat.agents.draft_agent import DraftAgent


class TestDraftAgentTools:
    """Test DraftAgent tool configuration."""

    def test_draft_agent_has_correct_tools(self):
        """Test that DraftAgent has the expected tools and not the problematic ones."""
        agent = DraftAgent(
            thread_id=123,
            llm_model="fake-model",
            llm_provider="fake",
        )

        # Get tool names
        tool_names = [tool.metadata.name for tool in agent.tools]

        # Should have these tools
        expected_tools = {
            "create_draft_email",
            "delete_draft_email",
            "create_draft_calendar_event",
            "delete_draft_calendar_event",
        }

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing expected tool: {tool_name}"

        # Should NOT have these problematic tools
        problematic_tools = {
            "create_draft_calendar_change",
            "delete_draft_calendar_change",
        }

        for tool_name in problematic_tools:
            assert (
                tool_name not in tool_names
            ), f"Found problematic tool that should be removed: {tool_name}"

    def test_draft_agent_calendar_event_tool_description(self):
        """Test that the calendar event tool has clear description for updates."""
        agent = DraftAgent(
            thread_id=123,
            llm_model="fake-model",
            llm_provider="fake",
        )

        # Find the calendar event tool
        calendar_tool = None
        for tool in agent.tools:
            if tool.metadata.name == "create_draft_calendar_event":
                calendar_tool = tool
                break

        assert calendar_tool is not None, "create_draft_calendar_event tool not found"

        # Check that description emphasizes both creating AND updating
        description = calendar_tool.metadata.description.lower()
        assert "create" in description
        assert "update" in description
        assert "current conversation" in description
        assert "existing calendar event drafts" in description

    def test_draft_agent_thread_id_storage(self):
        """Test that DraftAgent properly stores thread_id."""
        test_thread_id = 999
        agent = DraftAgent(
            thread_id=test_thread_id,
            llm_model="fake-model",
            llm_provider="fake",
        )

        assert agent.thread_id == str(test_thread_id)
        assert hasattr(agent, "_thread_id")
        assert agent._thread_id == str(test_thread_id)
