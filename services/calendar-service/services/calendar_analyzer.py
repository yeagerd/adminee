from typing import List
from datetime import datetime, timezone # Import timezone for UTC awareness if needed
from ..models import CalendarEvent, ConflictingEventPair, ConflictDetectionResult

def detect_event_conflicts(events: List[CalendarEvent]) -> ConflictDetectionResult:
    """
    Detects conflicts between a list of calendar events.
    Ignores all-day events and cancelled events for simplicity in MVP.
    """
    conflicts: List[ConflictingEventPair] = []

    # Filter out all-day and cancelled events first
    relevant_events = [
        event for event in events 
        if not event.isAllDay and not event.isCancelled
    ]

    # Sort events by start time to potentially optimize, though not strictly necessary for O(n^2) pairwise
    relevant_events.sort(key=lambda e: e.start.dateTime)

    for i in range(len(relevant_events)):
        event_a = relevant_events[i]
        a_start = event_a.start.dateTime
        a_end = event_a.end.dateTime

        # Ensure datetimes are timezone-aware. Pydantic V2 with default parsing should handle ISO strings
        # into timezone-aware datetime objects if the string contains timezone info (like 'Z' or offset).
        # If string is naive, Pydantic creates naive datetime. MS Graph with Prefer: outlook.timezone="TZ"
        # should return datetimes with that TZ in the string.
        # For robustness, one might explicitly check/convert here if an upstream process could yield naive datetimes.
        # However, our models.py DateTimeTimeZone.dateTime is `datetime`, which could be naive or aware.
        # Assuming the provider gives us aware datetimes for start/end as per Prefer header.

        for j in range(i + 1, len(relevant_events)):
            event_b = relevant_events[j]
            b_start = event_b.start.dateTime
            b_end = event_b.end.dateTime

            # Conflict condition: (A.start < B.end) and (A.end > B.start)
            if a_start < b_end and a_end > b_start:
                # Calculate overlap duration
                overlap_start = max(a_start, b_start)
                overlap_end = min(a_end, b_end)
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 60.0 # in minutes

                conflicts.append(
                    ConflictingEventPair(
                        event1_id=event_a.id,
                        event1_subject=event_a.subject,
                        event1_start=a_start, # These are already datetime objects
                        event1_end=a_end,
                        event2_id=event_b.id,
                        event2_subject=event_b.subject,
                        event2_start=b_start,
                        event2_end=b_end,
                        overlap_minutes=round(overlap_duration, 2)
                    )
                )
    
    return ConflictDetectionResult(
        conflicts=conflicts,
        checked_event_count=len(relevant_events),
        conflict_pair_count=len(conflicts)
    ) 