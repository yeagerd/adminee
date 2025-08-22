"""
Utility tools for helper functions and formatting operations.

This module provides utility functions for:
- Time formatting and timezone conversion
- Data validation and processing
- Common helper operations
"""

import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class UtilityTools:
    """Collection of utility tools for common operations."""

    def __init__(self):
        pass

    def format_event_time_for_display(
        self, start_time: str, end_time: str, timezone_str: str = "UTC"
    ) -> str:
        """
        Format a datetime range for display in the specified timezone.

        Args:
            start_time: ISO datetime string for start time (e.g., "2025-06-18T10:00:00Z")
            end_time: ISO datetime string for end time (e.g., "2025-06-18T11:00:00Z")
            timezone_str: Timezone string (e.g., "US/Eastern", "US/Pacific")

        Returns:
            Formatted datetime range string in the specified timezone
        """
        try:
            from datetime import datetime
            import pytz

            def format_single_time(dt_str: str) -> Union[datetime, str]:
                """Format a single datetime string."""
                try:
                    # Parse the datetime string
                    if dt_str.endswith("Z"):
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(dt_str)

                    # If no timezone info, assume UTC
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)

                    return dt
                except Exception:
                    # Return original string if parsing fails
                    return dt_str

            # Parse both times
            start_dt = format_single_time(start_time)
            end_dt = format_single_time(end_time)

            # If either failed to parse, return original format
            if isinstance(start_dt, str) or isinstance(end_dt, str):
                return f"{start_time} to {end_time}"

            # Convert to target timezone
            try:
                target_tz = pytz.timezone(timezone_str)
                localized_start = start_dt.astimezone(target_tz)
                localized_end = end_dt.astimezone(target_tz)
            except pytz.exceptions.UnknownTimeZoneError:
                # Fall back to UTC if timezone is invalid
                localized_start = start_dt.astimezone(pytz.UTC)
                localized_end = end_dt.astimezone(pytz.UTC)

            # Format for display
            start_formatted = localized_start.strftime("%I:%M %p")
            end_formatted = localized_end.strftime("%I:%M %p")

            # Check if same day
            if localized_start.date() == localized_end.date():
                return f"{start_formatted} to {end_formatted}"
            else:
                # Different days, include dates
                start_date = localized_start.strftime("%b %d")
                end_date = localized_end.strftime("%b %d")
                return f"{start_date} {start_formatted} to {end_date} {end_formatted}"

        except Exception as e:
            logger.error(f"Error formatting datetime range {start_time} to {end_time}: {e}")
            return (
                f"{start_time} to {end_time}"  # Return original format if formatting fails
            )

    def validate_email_format(self, email: str) -> bool:
        """
        Validate email format using basic regex pattern.
        
        Args:
            email: Email string to validate
            
        Returns:
            True if email format is valid, False otherwise
        """
        import re
        
        # Basic email validation pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def sanitize_string(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string by removing potentially harmful characters.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length to truncate to (optional)
            
        Returns:
            Sanitized string
        """
        if not text:
            return ""
        
        # Remove control characters and normalize whitespace
        sanitized = "".join(char for char in text if ord(char) >= 32)
        sanitized = " ".join(sanitized.split())
        
        # Truncate if max_length specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip() + "..."
            
        return sanitized

    def parse_date_range(self, date_string: str) -> Dict[str, Optional[str]]:
        """
        Parse a date range string into start and end dates.
        
        Args:
            date_string: String like "today", "this week", "2024-01-01 to 2024-01-31"
            
        Returns:
            Dict with 'start_date' and 'end_date' keys
        """
        try:
            from datetime import datetime, timedelta
            
            date_string = date_string.lower().strip()
            
            if date_string == "today":
                today = datetime.now().date()
                return {
                    "start_date": today.strftime("%Y-%m-%d"),
                    "end_date": today.strftime("%Y-%m-%d")
                }
            elif date_string == "yesterday":
                yesterday = (datetime.now().date() - timedelta(days=1))
                return {
                    "start_date": yesterday.strftime("%Y-%m-%d"),
                    "end_date": yesterday.strftime("%Y-%m-%d")
                }
            elif date_string == "this week":
                today = datetime.now().date()
                start_of_week = today - timedelta(days=today.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                return {
                    "start_date": start_of_week.strftime("%Y-%m-%d"),
                    "end_date": end_of_week.strftime("%Y-%m-%d")
                }
            elif " to " in date_string:
                # Parse explicit date range
                parts = date_string.split(" to ")
                if len(parts) == 2:
                    start_date = parts[0].strip()
                    end_date = parts[1].strip()
                    # Validate date format
                    try:
                        datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.strptime(end_date, "%Y-%m-%d")
                        return {
                            "start_date": start_date,
                            "end_date": end_date
                        }
                    except ValueError:
                        pass
            
            # If no pattern matches, return None for both
            return {"start_date": None, "end_date": None}
            
        except Exception as e:
            logger.error(f"Error parsing date range '{date_string}': {e}")
            return {"start_date": None, "end_date": None}

    def format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in bytes to human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., "1.5 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"

    def extract_phone_number(self, text: str) -> Optional[str]:
        """
        Extract phone number from text using regex pattern.
        
        Args:
            text: Text to search for phone numbers
            
        Returns:
            Extracted phone number or None if not found
        """
        import re
        
        # Pattern for various phone number formats
        patterns = [
            r'\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
            r'\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}',  # International
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 3:
                    # US format
                    return f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                else:
                    # International format
                    return match.group(0)
        
        return None

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate a summary of text by truncating and adding ellipsis.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summarized text
        """
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        # Try to break at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        
        if last_space > max_length * 0.8:  # If we can break at a reasonable word boundary
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
