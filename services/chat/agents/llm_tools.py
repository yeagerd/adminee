#!/usr/bin/env python3
"""
LLM Tools for chat workflows - LEGACY FILE BEING PHASED OUT

This file contains only the remaining functions that haven't been moved to the new tool classes yet.
Most functionality has been moved to:
- services.chat.tools.draft_tools.DraftTools
- services.chat.tools.data_tools.DataTools  
- services.chat.tools.utility_tools.UtilityTools
- services.chat.tools.search_tools.SearchTools
- services.chat.tools.web_tools.WebTools
- services.chat.tools.get_tools.GetTools

DEPRECATION WARNING: This file will be removed in a future version.
Use the new tool classes instead.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote

import requests

from services.chat.service_client import ServiceClient
from services.vespa_query.search_engine import SearchEngine

logger = logging.getLogger(__name__)

# Note: Most functions have been moved to organized tool classes
# This file contains only legacy functions that are still being used

# Generic tool execution function for the workflow system
def execute_tool(tool_name: str, **kwargs: Any) -> Any:
    """
    Execute a tool by name with the given parameters.
    
    This is a legacy function that routes tool calls to the appropriate service.
    New code should use the tool registry directly.
    """
    try:
        if tool_name == "get_calendar_events":
            user_id = kwargs.get("user_id")
            if not user_id:
                return type(
                    "ToolOutput",
                    (),
                    {"raw_output": {"error": "user_id is required"}},
                )()

            # Use DataTools instead of circular import
            from services.chat.tools.data_tools import DataTools

            data_tools = DataTools(user_id)
            result = data_tools.get_calendar_events(
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                time_zone=kwargs.get("time_zone", "UTC"),
                providers=kwargs.get("providers"),
                limit=kwargs.get("limit", 50),
            )

            return type("ToolOutput", (), {"raw_output": result})()

        elif tool_name == "get_emails":
            user_id = kwargs.get("user_id")
            if not user_id:
                return type(
                    "ToolOutput",
                    (),
                    {"raw_output": {"error": "user_id is required"}},
                )()

            # Use DataTools instead of circular import
            from services.chat.tools.data_tools import DataTools

            data_tools = DataTools(user_id)
            result = data_tools.get_emails(
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                folder=kwargs.get("folder"),
                unread_only=kwargs.get("unread_only"),
                search_query=kwargs.get("search_query"),
                max_results=kwargs.get("max_results"),
            )

            return type("ToolOutput", (), {"raw_output": result})()

        elif tool_name == "get_notes":
            user_id = kwargs.get("user_id")
            if not user_id:
                return type(
                    "ToolOutput",
                    (),
                    {"raw_output": {"error": "user_id is required"}},
                )()

            # Use DataTools instead of circular import
            from services.chat.tools.data_tools import DataTools

            data_tools = DataTools(user_id)
            result = data_tools.get_notes(
                search_query=kwargs.get("search_query"),
                max_results=kwargs.get("max_results"),
            )

            return type("ToolOutput", (), {"raw_output": result})()

        elif tool_name == "get_documents":
            user_id = kwargs.get("user_id")
            if not user_id:
                return type(
                    "ToolOutput",
                    (),
                    {"raw_output": {"error": "user_id is required"}},
                )()

            # Use DataTools instead of circular import
            from services.chat.tools.data_tools import DataTools

            data_tools = DataTools(user_id)
            result = data_tools.get_documents(
                document_type=kwargs.get("document_type"),
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                search_query=kwargs.get("search_query"),
                max_results=kwargs.get("max_results"),
            )

            return type("ToolOutput", (), {"raw_output": result})()

        else:
            return type(
                "ToolOutput",
                (),
                {"raw_output": {"error": f"Unknown tool: {tool_name}"}},
            )()

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return type("ToolOutput", (), {"raw_output": {"error": str(e)}})()


# Note: format_event_time_for_display has been moved to UtilityTools.format_event_time_for_display
# Note: ToolRegistry has been moved to services.chat.tools.get_tools

# DEPRECATION WARNING: This file is being phased out
# Use the new tool classes in services.chat.tools.* instead
