"use client"

import { CalendarEvent } from '@/types/office-service';
import { DateTime } from 'luxon';
import { useMemo } from 'react';

interface CalendarGridEventProps {
    event: CalendarEvent;
    day: Date;
    effectiveTimezone: string;
}

export function CalendarGridEvent({ event, day, effectiveTimezone }: CalendarGridEventProps) {
    // Parse event times - assume they come from API in UTC
    let eventStart, eventEnd;

    try {
        // Parse as UTC first, then convert to user's timezone
        eventStart = DateTime.fromISO(event.start_time, { zone: 'utc' }).setZone(effectiveTimezone);
        eventEnd = DateTime.fromISO(event.end_time, { zone: 'utc' }).setZone(effectiveTimezone);
    } catch (e) {
        // Fallback: try parsing as-is
        eventStart = DateTime.fromISO(event.start_time).setZone(effectiveTimezone);
        eventEnd = DateTime.fromISO(event.end_time).setZone(effectiveTimezone);
    }

    // Debug: log the timezone conversion
    console.log(`Event "${event.title}":`, {
        originalStart: event.start_time,
        originalEnd: event.end_time,
        parsedStart: eventStart.toISO(),
        parsedEnd: eventEnd.toISO(),
        displayStart: eventStart.toFormat('h:mm a'),
        displayEnd: eventEnd.toFormat('h:mm a'),
        timezone: effectiveTimezone,
        startHour: eventStart.hour,
        startMinute: eventStart.minute,
        isUTC: eventStart.zoneName === 'UTC'
    });

    // Check if event is all day
    const isAllDay = event.all_day;

    // Calculate position and size for grid events (non-all-day events)
    const gridPosition = useMemo(() => {
        if (isAllDay) return null;

        // Check if event starts on this day
        const eventDay = eventStart.toFormat('yyyy-MM-dd');
        const currentDay = DateTime.fromJSDate(day).setZone(effectiveTimezone).toFormat('yyyy-MM-dd');



        if (eventDay !== currentDay) return null;

        // Calculate start position (top) - using pixel-based positioning
        const startHour = eventStart.hour;
        const startMinute = eventStart.minute;
        const gridStartHour = 6; // Grid starts at 6 AM
        const gridEndHour = 22; // Grid ends at 10 PM

        // Each 30-minute slot is 32px high
        const slotHeight = 32; // 30-minute slot height
        const slotsPerHour = 2; // 2 slots per hour (30-minute intervals)

        // Calculate position in 30-minute slots
        const hoursFromStart = startHour - gridStartHour;
        const minutesOffset = startMinute / 30;
        const startSlots = hoursFromStart * slotsPerHour + minutesOffset;
        const topPixels = Math.max(0, startSlots * slotHeight);

        // Calculate height based on duration
        const durationMinutes = eventEnd.diff(eventStart, 'minutes').minutes;
        const durationSlots = Math.max(1, durationMinutes / 30); // Minimum 1 slot (30 minutes)
        const heightPixels = durationSlots * slotHeight; // Use exact slot height

        // Debug positioning
        console.log(`Event "${event.title}" positioning:`, {
            startHour,
            startMinute: eventStart.minute,
            startSlots,
            topPixels,
            durationMinutes,
            durationSlots,
            heightPixels,
            expectedTime: `${eventStart.hour}:${eventStart.minute.toString().padStart(2, '0')}`,
            slotHeight,
            gridStartHour,
            gridEndHour
        });

        return {
            top: topPixels,
            height: heightPixels,
            left: 0,
            right: 0,
        };
    }, [day, effectiveTimezone, isAllDay, eventStart, eventEnd]);

    // Calculate position for all-day events
    const allDayPosition = useMemo(() => {
        if (!isAllDay) return null;

        // Check if event is on this day
        const eventDay = eventStart.toFormat('yyyy-MM-dd');
        const currentDay = DateTime.fromJSDate(day).setZone(effectiveTimezone).toFormat('yyyy-MM-dd');

        if (eventDay !== currentDay) return null;

        return {
            top: 0,
            height: 24, // Fixed height for all-day events
            left: 0,
            right: 0,
        };
    }, [day, effectiveTimezone, isAllDay, eventStart]);

    const position = isAllDay ? allDayPosition : gridPosition;

    if (!position) return null;

    // Determine event color based on provider or status
    const getEventColor = () => {
        if (event.status === 'cancelled') {
            return 'bg-gray-300 text-gray-600 border-gray-400';
        }

        // Use different colors for different providers
        switch (event.provider) {
            case 'google':
                return 'bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-200';
            case 'microsoft':
                return 'bg-purple-100 text-purple-800 border-purple-200 hover:bg-purple-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-200';
        }
    };

    // Format event time for display
    const formatEventTime = () => {
        if (isAllDay) return 'All day';
        return `${eventStart.toFormat('h:mm a')} - ${eventEnd.toFormat('h:mm a')} ${eventStart.offsetNameShort}`;
    };

    // Check if event is currently happening
    const now = DateTime.now().setZone(effectiveTimezone);
    const isCurrent = eventStart <= now && now <= eventEnd;

    return (
        <div
            className={`
                absolute left-1 right-1 rounded px-2 py-1 text-xs font-medium
                border cursor-pointer transition-colors pointer-events-auto
                ${getEventColor()}
                ${isCurrent ? 'ring-2 ring-blue-500 ring-opacity-50' : ''}
                ${isAllDay ? 'h-6' : ''}
            `}
            style={{
                top: `${position.top}px`,
                height: isAllDay ? '24px' : `${position.height}px`,
                minHeight: isAllDay ? '20px' : '20px',
                maxHeight: isAllDay ? '24px' : '100px',
                overflow: 'hidden',
            }}
            onClick={(e) => {
                e.stopPropagation();
                // Future: Open event details modal
                console.log('Event clicked:', event.title);
            }}
            title={`${event.title} - ${formatEventTime()}`}
        >
            <div className={`truncate ${isAllDay ? 'text-xs' : 'font-semibold'}`}>
                {event.title}
            </div>
            {!isAllDay && (
                <>
                    <div className="truncate text-xs opacity-75">
                        {`${eventStart.toFormat('h:mm a')} - ${eventEnd.toFormat('h:mm a')}`}
                    </div>
                    {event.location && (
                        <div className="truncate text-xs opacity-75">
                            📍 {event.location}
                        </div>
                    )}
                </>
            )}
        </div>
    );
} 