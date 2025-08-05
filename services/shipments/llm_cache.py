"""
LLM Cache for storing and retrieving LLM inputs and outputs.

This module provides caching functionality to avoid repeated LLM API calls
during development and testing iterations.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from services.common.logging_config import get_logger
from services.shipments.settings import get_settings

logger = get_logger(__name__)


class LLMCache:
    """Cache for LLM inputs and outputs stored as JSON files."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the LLM cache.

        Args:
            cache_dir: Directory to store cache files. Defaults to ./llm_cache
        """
        if cache_dir is None:
            cache_dir = "./llm_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Get settings
        self.settings = get_settings()
        self.enabled = self.settings.use_llm_cache

        if self.enabled:
            logger.info(f"LLM cache enabled at {self.cache_dir}")
        else:
            logger.info("LLM cache disabled")

    def _generate_cache_key(self, model: str, **kwargs) -> str:
        """Generate a cache key from model and input parameters.

        Args:
            model: LLM model name
            **kwargs: Input parameters to hash

        Returns:
            Cache key string
        """
        # Create a deterministic string representation of the input
        input_str = f"{model}:{json.dumps(kwargs, sort_keys=True)}"

        # Generate hash
        hash_obj = hashlib.md5(input_str.encode("utf-8"))
        return hash_obj.hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            cache_key: Cache key string

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def get(self, model: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached response for given model and input parameters.

        Args:
            model: LLM model name
            **kwargs: Input parameters

        Returns:
            Cached response dict or None if not found
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._generate_cache_key(model, **kwargs)
            cache_file = self._get_cache_file_path(cache_key)

            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)

                logger.debug(f"Cache hit for {model}: {cache_key}")
                return cached_data
            else:
                logger.debug(f"Cache miss for {model}: {cache_key}")
                return None

        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def set(self, model: str, response: str, **kwargs) -> None:
        """Cache a response for given model and input parameters.

        Args:
            model: LLM model name
            response: LLM response string
            **kwargs: Input parameters
        """
        if not self.enabled:
            return

        try:
            cache_key = self._generate_cache_key(model, **kwargs)
            cache_file = self._get_cache_file_path(cache_key)

            # Prepare cache data
            cache_data = {
                "model": model,
                "input": kwargs,
                "response": response,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_key": cache_key,
            }

            # Write to file
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Cached response for {model}: {cache_key}")

        except Exception as e:
            logger.warning(f"Error writing cache: {e}")

    def clear(self) -> None:
        """Clear all cached responses."""
        if not self.enabled:
            return

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info(f"Cleared {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "enabled": True,
                "cache_dir": str(self.cache_dir),
                "file_count": len(cache_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache instance
_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _cache
    if _cache is None:
        _cache = LLMCache()
    return _cache
