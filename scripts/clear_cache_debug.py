#!/usr/bin/env python3
"""
Debug script to clear cached calendar events and test fresh API calls.
"""

import asyncio
import redis.asyncio as redis
import os

async def clear_demo_user_cache() -> None:
    """Clear all cached data for demo_user to force fresh API calls."""
    
    # Connect to Redis using the same URL pattern as the office service
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8", 
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
        )
        
        # Test connection
        await redis_client.ping()
        print("✅ Connected to Redis successfully")
        
        # Find all cache keys for demo_user
        pattern = "office:demo_user:*"
        keys = await redis_client.keys(pattern)
        
        print(f"Found {len(keys)} cache keys for demo_user:")
        for key in keys:
            ttl = await redis_client.ttl(key)
            ttl_info = f"(TTL: {ttl}s)" if ttl > 0 else "(no expiry)" if ttl == -1 else "(expired)"
            print(f"  - {key} {ttl_info}")
        
        if keys:
            # Delete all keys
            deleted_count = await redis_client.delete(*keys)
            print(f"🗑️  Deleted {deleted_count} cache keys")
        else:
            print("No cache keys found to delete")
            
        # Show unified events cache pattern specifically
        unified_pattern = "office:demo_user:unified:events:*"
        unified_keys = await redis_client.keys(unified_pattern)
        print(f"\nSpecifically for unified calendar events: {len(unified_keys)} keys")
        
        await redis_client.close()
        print("✅ Redis connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def inspect_cache_contents() -> None:
    """Inspect what's actually in the cache for debugging."""
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8", 
            decode_responses=True,
        )
        
        await redis_client.ping()
        print("🔍 Inspecting cache contents for demo_user...")
        
        # Look at calendar event cache keys
        pattern = "office:demo_user:unified:events:*"
        keys = await redis_client.keys(pattern)
        
        for key in keys:
            data = await redis_client.get(key)
            ttl = await redis_client.ttl(key)
            print(f"\n📝 Key: {key}")
            print(f"⏰ TTL: {ttl}s")
            print(f"📄 Data preview: {data[:200] if data else 'None'}...")
            
        if not keys:
            print("No calendar event cache keys found")
            
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ Error inspecting cache: {e}")

if __name__ == "__main__":
    print("=== Office Service Cache Debug Tool ===\n")
    
    print("1. Inspecting current cache contents...")
    asyncio.run(inspect_cache_contents())
    
    print("\n" + "="*50 + "\n")
    
    print("2. Clearing demo_user cache...")
    asyncio.run(clear_demo_user_cache())
    
    print("\n✨ Cache cleared! Now try your calendar request again.")
    print("The office service should make fresh API calls instead of returning cached results.") 