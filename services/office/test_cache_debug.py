#!/usr/bin/env python3
"""
Simple test script to debug cache key generation and cache behavior.
"""

import asyncio
import json
from datetime import datetime, timezone

from services.office.core.cache_manager import cache_manager, generate_cache_key


async def test_cache_key_generation():
    """Test cache key generation with sample parameters."""

    # Sample parameters similar to what the calendar endpoint uses
    user_id = "AAAAAAAAAAAAAAAAAAAAAG_WiRzTkk4vuAr97CA2Dc4"
    start_dt = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_dt = start_dt.replace(hour=23, minute=59, second=59)

    cache_params = {
        "providers": ["microsoft"],
        "limit": 10,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "calendar_ids": [],
        "q": "",
        "time_zone": "UTC",
    }

    cache_key = generate_cache_key(user_id, "unified", "events", cache_params)

    print(f"User ID: {user_id}")
    print(f"Cache params: {json.dumps(cache_params, indent=2)}")
    print(f"Generated cache key: {cache_key}")

    # Test cache operations
    try:
        # Test setting some data
        test_data = {
            "events": [],
            "total_count": 0,
            "providers_used": ["microsoft"],
            "provider_errors": None,
            "date_range": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "time_zone": "UTC",
            },
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": ["microsoft"],
                "limit": 10,
                "calendar_ids": [],
            },
        }

        print("\nSetting test data to cache...")
        success = await cache_manager.set_to_cache(cache_key, test_data, ttl_seconds=60)
        print(f"Cache set success: {success}")

        # Test getting the data back
        print("\nRetrieving data from cache...")
        retrieved_data = await cache_manager.get_from_cache(cache_key)
        print(f"Retrieved data: {retrieved_data}")

        if retrieved_data:
            print(f"Data type: {type(retrieved_data)}")
            if isinstance(retrieved_data, dict):
                print(f"Data keys: {list(retrieved_data.keys())}")
                if "events" in retrieved_data:
                    print(f"Events count: {len(retrieved_data['events'])}")

        # Clean up
        await cache_manager.delete_from_cache(cache_key)
        print("\nCleaned up test cache entry")

    except Exception as e:
        print(f"Error testing cache: {e}")


if __name__ == "__main__":
    asyncio.run(test_cache_key_generation())
