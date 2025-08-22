#!/usr/bin/env python3
"""
Test script to verify the tool discovery system works correctly.
"""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))

from services.chat.tools.get_tools import GetTools

def test_tool_discovery():
    """Test the tool discovery functionality."""
    print("🧪 Testing Tool Discovery System")
    print("=" * 50)
    
    # Initialize GetTools
    get_tools = GetTools(user_id="test_user_123")
    
    # Test 1: List available tools
    print("\n1. Testing list_tools()...")
    try:
        tools_list = get_tools.get_tool.list_tools()
        print(f"✅ Success: {tools_list}")
        
        if tools_list.get("status") == "success":
            tools = tools_list.get("tools", [])
            print(f"   Found {len(tools)} tools:")
            for tool_id, description in tools:
                print(f"   - {tool_id}: {description}")
        else:
            print(f"   ❌ Error: {tools_list.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Get tool info for a specific tool
    print("\n2. Testing get_tool_info('get_calendar_events')...")
    try:
        tool_info = get_tools.get_tool.get_tool_info("get_calendar_events")
        print(f"✅ Success: {tool_info}")
        
        if tool_info.get("status") == "success":
            info = tool_info.get("tool_info", {})
            print(f"   Tool ID: {info.get('tool_id')}")
            print(f"   Description: {info.get('description')}")
            print(f"   Category: {info.get('category')}")
            print(f"   Parameters: {len(info.get('parameters', {}))} parameters")
            print(f"   Examples: {len(info.get('examples', []))} examples")
        else:
            print(f"   ❌ Error: {tool_info.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Get tool info for non-existent tool
    print("\n3. Testing get_tool_info('non_existent_tool')...")
    try:
        tool_info = get_tools.get_tool.get_tool_info("non_existent_tool")
        print(f"✅ Success: {tool_info}")
        
        if tool_info.get("status") == "error":
            print(f"   ✅ Correctly returned error: {tool_info.get('error')}")
        else:
            print(f"   ❌ Should have returned error for non-existent tool")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 4: Check registry statistics
    print("\n4. Testing registry statistics...")
    try:
        registry = get_tools.registry
        print(f"   Total tools: {registry.get_tool_count()}")
        print(f"   Categories: {registry.get_categories()}")
        
        for category in registry.get_categories():
            count = registry.get_category_tool_count(category)
            print(f"   - {category}: {count} tools")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Tool Discovery Test Complete!")

if __name__ == "__main__":
    test_tool_discovery()
