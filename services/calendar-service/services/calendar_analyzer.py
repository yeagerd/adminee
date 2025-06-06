from typing import List, Optional
from datetime import datetime, timezone  # Import timezone for UTC awareness if needed
from ..models import (
    CalendarEvent,
    ConflictingEventPair,
    ConflictDetectionResult,
    AttendeeStatusEnum,
    AnalyzedAttendee,
    EventAttendanceDetail,
    Organizer,
    Attendee,
    UserWorkHours,
    WorkHoursConflictInfo,
    WorkHoursConflictResult,
    WorkDay,  # Added new models
)
import pytz  # For timezone handling


def detect_event_conflicts(events: List[CalendarEvent]) -> ConflictDetectionResult:
    """
    Detects conflicts between a list of calendar events.
    Ignores all-day events and cancelled events for simplicity in MVP.
    """
    conflicts: List[ConflictingEventPair] = []

    # Filter out all-day and cancelled events first
    relevant_events = [
        event for event in events if not event.isAllDay and not event.isCancelled
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
                overlap_duration = (
                    overlap_end - overlap_start
                ).total_seconds() / 60.0  # in minutes

                conflicts.append(
                    ConflictingEventPair(
                        event1_id=event_a.id,
                        event1_subject=event_a.subject,
                        event1_start=a_start,  # These are already datetime objects
                        event1_end=a_end,
                        event2_id=event_b.id,
                        event2_subject=event_b.subject,
                        event2_start=b_start,
                        event2_end=b_end,
                        overlap_minutes=round(overlap_duration, 2),
                    )
                )

    return ConflictDetectionResult(
        conflicts=conflicts,
        checked_event_count=len(relevant_events),
        conflict_pair_count=len(conflicts),
    )


def map_provider_status_to_enum(provider_status: Optional[str]) -> AttendeeStatusEnum:
    if not provider_status:
        return AttendeeStatusEnum.NONE
    status_lower = provider_status.lower()
    if status_lower == "accepted":
        return AttendeeStatusEnum.ACCEPTED
    elif status_lower == "tentativelyaccepted":  # MS Graph uses this casing
        return AttendeeStatusEnum.TENTATIVELY_ACCEPTED
    elif status_lower == "declined":
        return AttendeeStatusEnum.DECLINED
    elif status_lower == "notresponded":  # MS Graph uses this casing
        return AttendeeStatusEnum.NOT_RESPONDED
    elif status_lower == "none":  # Explicit "none" from provider
        return AttendeeStatusEnum.NONE
    else:
        print(f"Warning: Unknown attendee status from provider: {provider_status}")
        return AttendeeStatusEnum.UNKNOWN


def analyze_event_attendee_status(event: CalendarEvent) -> EventAttendanceDetail:
    """
    Analyzes the attendance status for a single calendar event based on the revised models.
    """
    analyzed_attendees: List[AnalyzedAttendee] = []

    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None
    if event.organizer and event.organizer.emailAddress:
        organizer_name = event.organizer.emailAddress.name
        organizer_email = event.organizer.emailAddress.address

    for attendee_data in event.attendees:
        name: Optional[str] = None
        email: Optional[str] = None
        response_status_enum = AttendeeStatusEnum.NONE
        response_time_val: Optional[datetime] = None

        if attendee_data.emailAddress:
            name = attendee_data.emailAddress.name
            email = attendee_data.emailAddress.address

        if attendee_data.status and attendee_data.status.response:
            response_status_enum = map_provider_status_to_enum(
                attendee_data.status.response
            )
            response_time_val = attendee_data.status.time

        # Special case: If the attendee is the organizer, their status might not be explicitly listed
        # or might be implicitly "accepted" or "none". For now, we rely on explicit status if present.
        # If an organizer is also listed as an attendee, their explicit attendee status will be used.

        analyzed_attendees.append(
            AnalyzedAttendee(
                name=name,
                email=email,
                attendee_type=attendee_data.type,
                response_status=response_status_enum,
                response_time=response_time_val,
            )
        )

    return EventAttendanceDetail(
        event_id=event.id,
        event_subject=event.subject,
        organizer_name=organizer_name,
        organizer_email=organizer_email,
        attendees=analyzed_attendees,
    )


def detect_work_hours_conflicts(
    events: List[CalendarEvent], user_work_hours: UserWorkHours, user_timezone_str: str
) -> WorkHoursConflictResult:
    """
    Detects if events fall outside of specified user work hours.
    Assumes event start/end times are already in the user's local timezone as per DateTimeTimeZone.
    The user_timezone_str is used to correctly interpret work hour start/end times and day boundaries.
    """
    conflict_infos: List[WorkHoursConflictInfo] = []
    checked_event_count = 0

    try:
        user_tz = pytz.timezone(user_timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        # This should ideally be validated before calling this function,
        # perhaps when user settings are saved or when an API request is made.
        # Raising an error or returning a specific error response might be appropriate.
        # For now, we'll assume valid timezone string or handle as an empty result if not.
        # Or, better, let it propagate if the service layer can catch it.
        raise ValueError(f"Unknown timezone: {user_timezone_str}")

    days_map = {
        0: user_work_hours.monday,
        1: user_work_hours.tuesday,
        2: user_work_hours.wednesday,
        3: user_work_hours.thursday,
        4: user_work_hours.friday,
        5: user_work_hours.saturday,
        6: user_work_hours.sunday,
    }

    for event in events:
        if event.isAllDay or event.isCancelled:
            # Optionally, all-day events on non-working days could be flagged.
            # For now, skipping them like in pairwise conflict detection.
            continue

        checked_event_count += 1
        is_outside = False
        details = []

        # Event times are in event.start.dateTime and event.end.dateTime
        # These are datetime objects. The event.start.timeZone and event.end.timeZone
        # indicate the original timezone of the event from the provider.
        # For this analysis, we need to ensure we are comparing apples to apples.
        # The most robust way is to convert event times to the user's declared timezone.

        try:
            event_start_user_tz = event.start.dateTime.astimezone(user_tz)
            event_end_user_tz = event.end.dateTime.astimezone(user_tz)
        except ValueError as e:
            # This can happen if event.start.dateTime is naive.
            # Providers should give timezone-aware datetimes. If not, we might need a default assumption.
            # Based on previous work, MS Graph provider gives tz-aware if Prefer: outlook.timezone is used.
            # If they are naive, this is an issue with data integrity from the provider or upstream processing.
            # For now, let's assume they are timezone-aware as per DateTimeTimeZone model.
            # If event.start.timeZone is 'UTC', then astimezone(user_tz) is fine.
            # If it's already in user's local (but maybe different string like 'Eastern Standard Time' vs 'America/New_York')
            # astimezone will correctly handle it.
            # We need to handle the case where event.start.dateTime might be naive.
            # If DateTimeTimeZone.dateTime is naive, we should localize it using DateTimeTimeZone.timeZone first.

            event_original_start_tz = pytz.timezone(event.start.timeZone)
            event_original_end_tz = pytz.timezone(event.end.timeZone)

            localized_event_start = event_original_start_tz.localize(
                event.start.dateTime, is_dst=None
            )
            localized_event_end = event_original_end_tz.localize(
                event.end.dateTime, is_dst=None
            )

            event_start_user_tz = localized_event_start.astimezone(user_tz)
            event_end_user_tz = localized_event_end.astimezone(user_tz)

        event_weekday = event_start_user_tz.weekday()  # Monday is 0 and Sunday is 6
        work_day_settings: WorkDay = days_map[event_weekday]

        if not work_day_settings.is_working_day:
            is_outside = True
            details.append(
                f"Event occurs on a non-working day ({event_start_user_tz.strftime('%A')})."
            )
        else:
            if work_day_settings.start_time and work_day_settings.end_time:
                # Create datetime.time objects for comparison
                try:
                    work_start_time = datetime.strptime(
                        work_day_settings.start_time, "%H:%M"
                    ).time()
                    work_end_time = datetime.strptime(
                        work_day_settings.end_time, "%H:%M"
                    ).time()
                except ValueError:
                    # Invalid time format in settings, skip this event or error out
                    # This should be validated when settings are stored.
                    details.append("Invalid work hours format in settings.")
                    # For now, we'll consider it a conflict if format is bad, or skip analysis for this event.
                    # Let's assume for now it implies we can't confirm it's *within* work hours.
                    # To be safe, let's not mark it as a conflict, but log/note it.
                    # Or better, this event's work hours check is inconclusive.
                    # For the purpose of the function, let's assume valid format from UserWorkHours model due to regex.
                    pass  # Regex in model should prevent this

                event_start_time_local = event_start_user_tz.time()
                event_end_time_local = event_end_user_tz.time()

                # Handle events spanning midnight: if work_end_time < work_start_time, it's an overnight shift.
                # For simplicity, MVP assumes work hours are within the same calendar day.
                # If work_end_time is 00:00, it means end of the day.

                if event_start_time_local < work_start_time:
                    is_outside = True
                    details.append(
                        f"Event starts at {event_start_time_local.strftime('%H:%M')} before work hours start ({work_day_settings.start_time})."
                    )

                # If an event ends exactly at 00:00, it means it ends at the very end of that day.
                # If work_end_time is, for example, 17:00, then an event ending at 17:00 is fine.
                # An event ending at 17:01 is not.
                if event_end_time_local > work_end_time and not (
                    event_end_time_local.hour == 0
                    and event_end_time_local.minute == 0
                    and work_end_time.hour == 23
                    and work_end_time.minute == 59
                ):
                    # Special case: if work_end_time is 23:59, treat 00:00 of next day as outside if it's not the start of next day's work hours
                    is_outside = True
                    details.append(
                        f"Event ends at {event_end_time_local.strftime('%H:%M')} after work hours end ({work_day_settings.end_time})."
                    )
            else:
                # is_working_day is True, but no start/end times means it's a full working day (e.g. 24h shift, unlikely for this app but possible)
                # Or, it means settings are incomplete. For now, assume incomplete settings means we don't flag.
                pass  # Not a conflict if working day and no specific hours specified.

        conflict_infos.append(
            WorkHoursConflictInfo(
                event_id=event.id,
                event_subject=event.subject,
                is_outside_work_hours=is_outside,
                conflict_details="; ".join(details) if details else None,
            )
        )

    return WorkHoursConflictResult(
        conflicts=conflict_infos, checked_event_count=checked_event_count
    )


# Example usage (for testing purposes):
# if __name__ == '__main__':
#     from datetime import datetime, timedelta, timezone
#     tz_utc = timezone.utc
#     now = datetime.now(tz_utc)
#     sample_event_with_attendees = CalendarEvent(
#         id="att1",
#         subject="Attendance Test Event",
#         start={"dateTime": now, "timeZone": "UTC"},
#         end={"dateTime": now + timedelta(hours=1), "timeZone": "UTC"},
#         organizer=Organizer(emailAddress={"address": "org@example.com"}),
#         attendees=[
#             Attendee(emailAddress={"address": "req1@example.com"}, type="required"),
#             Attendee(emailAddress={"address": "req2@example.com"}, type="required"),
#             Attendee(emailAddress={"address": "opt1@example.com"}, type="optional"),
#             Attendee(emailAddress={"address": "res1@example.com"}, type="resource"),
#             Attendee(emailAddress={"address": "unknown_type@example.com"}, type=None), # Attendee with no specific type
#         ]
#     )
#     sample_event_no_organizer = CalendarEvent(
#         id="att2",
#         subject="No Organizer Test",
#         start={"dateTime": now, "timeZone": "UTC"},
#         end={"dateTime": now + timedelta(hours=1), "timeZone": "UTC"},
#         attendees=[]
#     )

#     analysis1 = analyze_event_attendee_status(sample_event_with_attendees)
#     print(f"Analysis for {analysis1.event_subject}:")
#     print(f"  Total: {analysis1.metrics.total_attendees}")
#     print(f"  Required: {analysis1.metrics.required_attendees}")
#     print(f"  Optional: {analysis1.metrics.optional_attendees}")
#     print(f"  Resource: {analysis1.metrics.resource_attendees}")
#     print(f"  Has Organizer: {analysis1.metrics.has_organizer}")

#     analysis2 = analyze_event_attendee_status(sample_event_no_organizer)
#     print(f"\nAnalysis for {analysis2.event_subject}:")
#     print(f"  Total: {analysis2.metrics.total_attendees}")
#     print(f"  Has Organizer: {analysis2.metrics.has_organizer}")
