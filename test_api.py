#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the services directory to the path
sys.path.insert(0, 'services')

from services.chat_service.llama_manager import ChatAgentManager
from services.chat_service import history_manager

async def test_chat_agent():
    """Test the chat agent functionality directly."""
    print("=== Testing Chat Agent Directly ===")
    
    # Create a thread
    thread = await history_manager.create_thread('test_user_direct', 'Test thread')
    print(f'Created thread: {thread.id}')
    
    # Create agent  
    agent = ChatAgentManager(
        thread_id=thread.id,
        user_id='test_user_direct',
        tools=[],
        subagents=[]
    )
    
    # Send a message
    response = await agent.chat('Hello there!')
    print(f'Agent response: {response}')
    
    # Check database messages
    messages = await history_manager.get_thread_history(thread.id, limit=2)
    print(f'Latest 2 messages in DB:')
    for msg in messages:
        print(f'  {msg.user_id}: {msg.content}')
    
    return thread.id, messages

async def test_api_logic():
    """Test the API logic directly without HTTP."""
    print("\n=== Testing API Logic ===")
    
    from services.chat_service.api import chat_endpoint
    from services.chat_service.models import ChatRequest
    
    # Create a request
    request = ChatRequest(
        user_id="test_api_user",
        message="Hi there!",
        thread_id=None  # Will create a new thread
    )
    
    # Call the endpoint
    response = await chat_endpoint(request)
    print(f'API Response:')
    print(f'  Thread ID: {response.thread_id}')
    print(f'  Number of messages: {len(response.messages)}')
    for msg in response.messages:
        print(f'  {msg.user_id} (LLM: {msg.llm_generated}): {msg.content}')

if __name__ == "__main__":
    asyncio.run(test_chat_agent())
    asyncio.run(test_api_logic()) 