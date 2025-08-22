#!/usr/bin/env python3
"""Script to update imports in test_timezone_functionality.py"""

import re

def update_imports():
    # Read the file
    with open('services/chat/tests/test_timezone_functionality.py', 'r') as f:
        content = f.read()
    
    # Update imports
    content = re.sub(
        r'from services\.chat\.agents\.llm_tools import format_event_time_for_display',
        'from services.chat.tools.utility_tools import UtilityTools',
        content
    )
    
    # Update function calls
    content = re.sub(
        r'format_event_time_for_display\(',
        'UtilityTools().format_event_time_for_display(',
        content
    )
    
    # Write the updated content
    with open('services/chat/tests/test_timezone_functionality.py', 'w') as f:
        f.write(content)
    
    print("Updated imports in test_timezone_functionality.py")

if __name__ == "__main__":
    update_imports()
