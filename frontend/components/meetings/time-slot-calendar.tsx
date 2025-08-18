'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SmartTimeDurationInput } from '@/components/ui/smart-time-duration-input';
import { CalendarEvent } from "@/types/api/office"';
import { Check, CheckCheck, Clock, Eye, EyeOff, Pencil, X } from 'lucide-react';
import { DateTime } from 'luxon';
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface TimeSlotCalendarProps {
    duration: number;
    timeZone: string;
    onTimeSlotsChange: (timeSlots: { start: string; end: string }[]) => void;
    selectedTimeSlots: { start: string; end: string }[];
    calendarEvents?: CalendarEvent[];
    onDurationChange?: (duration: number) => void;
}

interface TimeSlot {
    start: string;
    end: string;
    isSelected: boolean;
    isConflict: boolean;
    conflictEvents: CalendarEvent[];
}

interface DateRange {
    startDate: Date;
    endDate: Date;
}

// Helper function to check if a date is a business day (Monday-Friday)
const isBusinessDay = (date: Date): boolean => {
    const day = date.getDay();
    return day >= 1 && day <= 5; // Monday = 1, Friday = 5
};

// Helper function to get next business day
const getNextBusinessDay = (date: Date): Date => {
    const next = new Date(date);
    next.setDate(next.getDate() + 1);
    while (!isBusinessDay(next)) {
        next.setDate(next.getDate() + 1);
    }
    return next;
};

// Helper function to get previous business day
const getPreviousBusinessDay = (date: Date): Date => {
    const prev = new Date(date);
    prev.setDate(prev.getDate() - 1);
    while (!isBusinessDay(prev)) {
        prev.setDate(prev.getDate() - 1);
    }
    return prev;
};

// Memoized cell component to prevent unnecessary re-renders
interface TimeSlotCellProps {
    slot: TimeSlot;
    slotIndex: number;
    isSelected: boolean;
    onSlotMouseDown?: (slot: TimeSlot, slotIndex: number, isSelected: boolean) => void;
    onSlotMouseEnter?: (slot: TimeSlot, slotIndex: number) => void;
}

const TimeSlotCell = memo<TimeSlotCellProps>(({ slot, slotIndex, isSelected, onSlotMouseDown, onSlotMouseEnter }) => {

    return (
        <button
            key={`${slot.start}-${slot.end}`}
            type="button"
            onMouseDown={(e) => { e.preventDefault(); onSlotMouseDown?.(slot, slotIndex, isSelected); }}
            onMouseEnter={() => { onSlotMouseEnter?.(slot, slotIndex); }}
            className={`
                absolute left-0 right-0 h-8 text-xs transition-colors z-10 rounded-sm select-none
                ${isSelected
                    ? slot.isConflict
                        ? 'bg-orange-500/50 border border-orange-600 text-orange-800 hover:bg-orange-500/70'
                        : 'bg-teal-600/50 border border-teal-700 text-teal-800 hover:bg-teal-600/70'
                    : 'bg-transparent border border-transparent hover:bg-gray-50/50 hover:border-gray-400'
                }
            `}
            style={{
                top: `${slotIndex * 32}px`
            }}
            title={`Click to ${isSelected ? 'deselect' : 'select'} this time slot${slot.isConflict ? ' (conflicts with calendar event)' : ''}`}
        >
        </button>
    );
});

TimeSlotCell.displayName = 'TimeSlotCell';



export function TimeSlotCalendar({
    duration,
    timeZone,
    onTimeSlotsChange,
    selectedTimeSlots,
    calendarEvents = [],
    onDurationChange
}: TimeSlotCalendarProps) {

    // Use ref to track current selected slots without dependencies
    const selectedSlotsRef = useRef(selectedTimeSlots);
    selectedSlotsRef.current = selectedTimeSlots;

    // Drag selection state
    const [isDragging, setIsDragging] = useState(false);
    const dragInfoRef = useRef<{
        dateKey: string;
        startIndex: number;
        currentIndex: number;
        mode: 'add' | 'remove';
        initialSelected: { start: string; end: string }[];
    } | null>(null);



    const handleGlobalMouseUp = useCallback(() => {
        setIsDragging(false);
        dragInfoRef.current = null;
        document.removeEventListener('mouseup', handleGlobalMouseUp);
    }, []);



    // Cleanup mouseup listener on unmount just in case
    useEffect(() => {
        return () => {
            document.removeEventListener('mouseup', handleGlobalMouseUp);
        };
    }, [handleGlobalMouseUp]);

    // Date range selection
    const [dateRangeType, setDateRangeType] = useState<'target' | 'range'>('target');
    const [targetDate, setTargetDate] = useState(() => {
        // Set default date to 3 business days ahead of today
        const today = new Date();
        let businessDaysAhead = 0;
        // eslint-disable-next-line prefer-const
        let currentDate = new Date(today);

        while (businessDaysAhead < 3) {
            currentDate.setDate(currentDate.getDate() + 1);
            if (isBusinessDay(currentDate)) {
                businessDaysAhead++;
            }
        }

        return currentDate.toISOString().split('T')[0];
    });
    const [dateRange, setDateRange] = useState<DateRange>(() => {
        const today = new Date();
        const endDate = new Date(today);
        endDate.setDate(endDate.getDate() + 7);
        return {
            startDate: today,
            endDate: endDate
        };
    });
    const [daysAround, setDaysAround] = useState(2); // Default to +/- 2 days

    // Display options
    const [includeWeekends, setIncludeWeekends] = useState(false);
    const [granularity, setGranularity] = useState<'15' | '30' | '60'>('30');
    const [showCalendarEvents, setShowCalendarEvents] = useState(true);
    const [isEditingDuration, setIsEditingDuration] = useState(false);

    const formatHeaderDuration = (minutes: number): string => {
        if (minutes >= 60) {
            const hours = minutes / 60;
            // Show up to two decimals, strip trailing zeros
            const hoursStr = (Math.round(hours * 100) / 100).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1');
            const unit = Number(hoursStr) === 1 ? 'hour' : 'hours';
            return `${hoursStr} ${unit}`;
        }
        const unit = minutes === 1 ? 'minute' : 'minutes';
        return `${minutes}-${unit}`;
    };

    // Business hours (configurable)
    const [businessHours, setBusinessHours] = useState({
        start: 9, // 9 AM
        end: 17   // 5 PM
    });

    // Generate date range based on selection type
    const effectiveDateRange = useMemo(() => {
        if (dateRangeType === 'target') {
            // Create dates in local timezone to avoid timezone conversion issues
            const target = new Date(targetDate + 'T00:00:00');
            const start = new Date(targetDate + 'T00:00:00');
            const end = new Date(targetDate + 'T00:00:00');

            if (includeWeekends) {
                // Use calendar days - simply add/subtract daysAround
                start.setDate(start.getDate() - daysAround);
                end.setDate(end.getDate() + daysAround);
            } else {
                // Use business days - calculate business days before and after
                let currentStart = new Date(target);
                let currentEnd = new Date(target);

                // Calculate business days before
                for (let i = 0; i < daysAround; i++) {
                    currentStart = getPreviousBusinessDay(currentStart);
                }

                // Calculate business days after
                for (let i = 0; i < daysAround; i++) {
                    currentEnd = getNextBusinessDay(currentEnd);
                }

                start.setTime(currentStart.getTime());
                end.setTime(currentEnd.getTime());
            }

            // Ensure start date never goes before today
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (start < today) {
                start.setTime(today.getTime());
            }

            return { startDate: start, endDate: end };
        } else {
            return dateRange;
        }
    }, [dateRangeType, targetDate, daysAround, dateRange, includeWeekends]);

    // Group calendar events by date for conflict detection (moved before timeSlots calculation)
    const eventsByDateForConflicts = useMemo(() => {
        const grouped: Record<string, CalendarEvent[]> = {};
        calendarEvents.forEach(event => {
            // Use the event's start time in the user's timezone to determine the date
            const eventStart = DateTime.fromISO(event.start_time, { zone: 'utc' }).setZone(timeZone);
            const dateKey = eventStart.toFormat('yyyy-MM-dd');
            if (!grouped[dateKey]) {
                grouped[dateKey] = [];
            }
            grouped[dateKey].push(event);
        });
        return grouped;
    }, [calendarEvents, timeZone]);

    // Generate time slots for the date range (without selection state)
    const timeSlots = useMemo(() => {
        const slots: TimeSlot[] = [];
        const granularityMinutes = parseInt(granularity);

        // Generate dates
        const dates: Date[] = [];
        const current = new Date(effectiveDateRange.startDate);
        while (current <= effectiveDateRange.endDate) {
            const dayOfWeek = current.getDay();
            if (includeWeekends || (dayOfWeek !== 0 && dayOfWeek !== 6)) {
                dates.push(new Date(current));
            }
            current.setDate(current.getDate() + 1);
        }

        // Generate time slots for each date
        dates.forEach(date => {
            const startHour = businessHours.start;
            const endHour = businessHours.end;

            for (let hour = startHour; hour < endHour; hour++) {
                for (let minute = 0; minute < 60; minute += granularityMinutes) {
                    const slotStart = new Date(date);
                    slotStart.setHours(hour, minute, 0, 0);

                    const slotEnd = new Date(slotStart);
                    slotEnd.setMinutes(slotEnd.getMinutes() + duration);

                    // Check for conflicts with calendar events on the same day only
                    const dateKey = date.toISOString().split('T')[0];
                    const dayEvents = eventsByDateForConflicts[dateKey] || [];

                    const conflictEvents = dayEvents.filter(event => {
                        // Parse event times as UTC and convert to user's timezone
                        const eventStart = DateTime.fromISO(event.start_time, { zone: 'utc' }).setZone(timeZone);
                        const eventEnd = DateTime.fromISO(event.end_time, { zone: 'utc' }).setZone(timeZone);

                        // Convert slot times to the user's timezone
                        const slotStartInTz = DateTime.fromJSDate(slotStart).setZone(timeZone);
                        const slotEndInTz = DateTime.fromJSDate(slotEnd).setZone(timeZone);

                        // Check for overlap (end times are non-inclusive)
                        // A slot conflicts if it overlaps with an event
                        // Slot: [slotStartInTz, slotEndInTz)
                        // Event: [eventStart, eventEnd)
                        // For non-inclusive end times, we need slotStart < eventEnd AND slotEnd > eventStart
                        const hasConflict = slotStartInTz < eventEnd && slotEndInTz > eventStart;

                        return hasConflict;
                    });

                    const isConflict = conflictEvents.length > 0;

                    slots.push({
                        start: slotStart.toISOString(),
                        end: slotEnd.toISOString(),
                        isSelected: false, // Will be calculated separately
                        isConflict,
                        conflictEvents
                    });
                }
            }
        });

        return slots;
    }, [effectiveDateRange, includeWeekends, granularity, businessHours, duration, eventsByDateForConflicts, timeZone]);

    // Create a Set for fast selection lookup
    const selectedSlotsSet = useMemo(() => {
        return new Set(selectedTimeSlots.map(slot => `${slot.start}-${slot.end}`));
    }, [selectedTimeSlots]);

    // Group calendar events by date for display
    const eventsByDate = useMemo(() => {
        const grouped: Record<string, CalendarEvent[]> = {};
        calendarEvents.forEach(event => {
            // Use the event's start time in UTC and convert to user's timezone to determine the date
            const eventStart = DateTime.fromISO(event.start_time, { zone: 'utc' }).setZone(timeZone);
            const dateKey = eventStart.toFormat('yyyy-MM-dd');
            if (!grouped[dateKey]) {
                grouped[dateKey] = [];
            }
            grouped[dateKey].push(event);
        });
        return grouped;
    }, [calendarEvents, timeZone]);

    // Group slots by date for display
    const slotsByDate = useMemo(() => {
        const grouped: Record<string, TimeSlot[]> = {};
        timeSlots.forEach(slot => {
            const dateKey = new Date(slot.start).toISOString().split('T')[0];
            if (!grouped[dateKey]) {
                grouped[dateKey] = [];
            }
            grouped[dateKey].push(slot);
        });
        return grouped;
    }, [timeSlots]);

    // Apply drag selection to time slots
    const applyDragSelection = useCallback((dateKey: string, startIndex: number, currentIndex: number, mode: 'add' | 'remove') => {
        const daySlots = slotsByDate[dateKey] || [];
        const rangeStart = Math.max(0, Math.min(startIndex, currentIndex));
        const rangeEnd = Math.min(daySlots.length - 1, Math.max(startIndex, currentIndex));

        const currentDragInfo = dragInfoRef.current;
        const initialSelected = (currentDragInfo?.initialSelected || []).slice();

        const rangeIds = new Set<string>();
        for (let i = rangeStart; i <= rangeEnd; i++) {
            const s = daySlots[i];
            if (!s) continue;
            rangeIds.add(`${s.start}-${s.end}`);
        }

        if (mode === 'add') {
            const existingIds = new Set(initialSelected.map(s => `${s.start}-${s.end}`));
            const newSelected = initialSelected.slice();
            for (let i = rangeStart; i <= rangeEnd; i++) {
                const s = daySlots[i];
                if (!s) continue;
                const id = `${s.start}-${s.end}`;
                if (!existingIds.has(id)) {
                    newSelected.push({ start: s.start, end: s.end });
                    existingIds.add(id);
                }
            }
            onTimeSlotsChange(newSelected);
        } else {
            // remove
            const newSelected = initialSelected.filter(s => !rangeIds.has(`${s.start}-${s.end}`));
            onTimeSlotsChange(newSelected);
        }
    }, [onTimeSlotsChange, slotsByDate]);

    // Handle slot mouse down for drag selection
    const handleSlotMouseDownFactory = useCallback((dateKey: string) => (slot: TimeSlot, slotIndex: number, isSelected: boolean) => {
        setIsDragging(true);
        dragInfoRef.current = {
            dateKey,
            startIndex: slotIndex,
            currentIndex: slotIndex,
            mode: isSelected ? 'remove' : 'add',
            initialSelected: selectedTimeSlots.slice()
        };
        applyDragSelection(dateKey, slotIndex, slotIndex, isSelected ? 'remove' : 'add');
        document.addEventListener('mouseup', handleGlobalMouseUp);
    }, [applyDragSelection, handleGlobalMouseUp, selectedTimeSlots]);

    // Handle slot mouse enter for drag selection
    const handleSlotMouseEnterFactory = useCallback((dateKey: string) => (_slot: TimeSlot, slotIndex: number) => {
        const info = dragInfoRef.current;
        if (!isDragging || !info) return;
        if (info.dateKey !== dateKey) return; // restrict to a single day
        if (info.currentIndex === slotIndex) return;
        info.currentIndex = slotIndex;
        applyDragSelection(info.dateKey, info.startIndex, slotIndex, info.mode);
    }, [applyDragSelection, isDragging]);

    // Handle day-level selection
    const handleDaySelection = useCallback((dateKey: string, action: 'all' | 'all_times' | 'none') => {
        const daySlots = slotsByDate[dateKey] || [];
        let newSelectedSlots = [...selectedTimeSlots];

        if (action === 'all') {
            // Add all non-conflicting slots for this day
            const availableSlots = daySlots.filter(slot => !slot.isConflict);
            const existingIds = new Set(selectedTimeSlots.map(slot => `${slot.start}-${slot.end}`));

            availableSlots.forEach(slot => {
                if (!existingIds.has(`${slot.start}-${slot.end}`)) {
                    newSelectedSlots.push({ start: slot.start, end: slot.end });
                }
            });
        } else if (action === 'all_times') {
            // Add all slots for this day regardless of availability
            const existingIds = new Set(selectedTimeSlots.map(slot => `${slot.start}-${slot.end}`));
            const allSlots = daySlots.filter(slot => !existingIds.has(`${slot.start}-${slot.end}`));
            newSelectedSlots = [...newSelectedSlots, ...allSlots.map(slot => ({ start: slot.start, end: slot.end }))];
        } else if (action === 'none') {
            // Remove all slots for this day
            const daySlotIds = new Set(daySlots.map(slot => `${slot.start}-${slot.end}`));
            newSelectedSlots = selectedTimeSlots.filter(slot => !daySlotIds.has(`${slot.start}-${slot.end}`));
        }

        onTimeSlotsChange(newSelectedSlots);
    }, [selectedTimeSlots, onTimeSlotsChange, slotsByDate]);

    // Chunk dates into groups for multiple grid views
    const dateChunks = useMemo(() => {
        const dateKeys = Object.keys(slotsByDate).sort();
        const maxDatesPerGrid = 4; // Show max 4 dates per grid for better readability
        const chunks: string[][] = [];

        for (let i = 0; i < dateKeys.length; i += maxDatesPerGrid) {
            chunks.push(dateKeys.slice(i, i + maxDatesPerGrid));
        }

        return chunks;
    }, [slotsByDate]);

    // Format time for display
    const formatTime = (isoString: string) => {
        return DateTime.fromISO(isoString).setZone(timeZone).toFormat('h:mm a');
    };

    // Format date for display
    const formatDate = (dateString: string) => {
        return DateTime.fromISO(dateString).setZone(timeZone).toFormat('EEE MMM d');
    };

    // Format date for display from Date object
    const formatDateFromDate = (date: Date) => {
        // Use local timezone to avoid conversion issues
        return DateTime.fromJSDate(date).toFormat('EEE MMM d');
    };

    // Calculate actual number of days in the range
    const actualDaysInRange = useMemo(() => {
        const start = new Date(effectiveDateRange.startDate);
        const end = new Date(effectiveDateRange.endDate);
        const diffTime = end.getTime() - start.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 for inclusive range
        return diffDays;
    }, [effectiveDateRange]);

    // Memoized calendar event rendering for each day
    const memoizedCalendarEvents = useMemo(() => {
        const memoized: Record<string, React.ReactNode> = {};

        Object.keys(eventsByDate).forEach(dateKey => {
            const dayEvents = eventsByDate[dateKey] || [];
            if (!showCalendarEvents || dayEvents.length === 0) {
                memoized[dateKey] = null;
                return;
            }

            memoized[dateKey] = (
                <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 5 }}>
                    {dayEvents.map((event, index) => {
                        // Parse the event times as UTC and convert to user's timezone
                        const eventStart = DateTime.fromISO(event.start_time, { zone: 'utc' }).setZone(timeZone);
                        const eventEnd = DateTime.fromISO(event.end_time, { zone: 'utc' }).setZone(timeZone);

                        // Use the same positioning logic as the proven calendar grid view
                        const granularityMinutes = parseInt(granularity);
                        const slotHeight = 32; // Each time slot height (h-8)
                        const slotsPerHour = 60 / granularityMinutes; // Dynamic slots per hour based on granularity
                        const gridStartHour = businessHours.start;

                        // Calculate position based on current granularity
                        const startHour = eventStart.hour;
                        const startMinute = eventStart.minute;
                        const hoursFromStart = startHour - gridStartHour;
                        const minutesOffset = startMinute / granularityMinutes;
                        const startSlots = hoursFromStart * slotsPerHour + minutesOffset;
                        const topPixels = Math.max(0, startSlots * slotHeight);

                        // Calculate height based on duration and current granularity
                        const durationMinutes = eventEnd.diff(eventStart, 'minutes').minutes;
                        const durationSlots = Math.max(1, durationMinutes / granularityMinutes); // Minimum 1 slot
                        const heightPixels = durationSlots * slotHeight; // Use exact slot height

                        return (
                            <div
                                key={`${event.id}-${index}`}
                                className="absolute left-1 right-1 bg-blue-100/80 border border-blue-300/60 rounded text-xs text-blue-800 px-1 py-0.5 overflow-hidden"
                                style={{
                                    top: `${topPixels}px`,
                                    height: `${heightPixels}px`,
                                    pointerEvents: 'none'
                                }}
                                title={`${event.title} (${eventStart.toFormat('h:mm a')} - ${eventEnd.toFormat('h:mm a')})`}
                            >
                                <div className="truncate font-medium text-blue-900">{event.title}</div>
                                <div className="truncate text-blue-700">
                                    {eventStart.toFormat('h:mm a')} - {eventEnd.toFormat('h:mm a')}
                                </div>
                            </div>
                        );
                    })}
                </div>
            );
        });

        return memoized;
    }, [eventsByDate, showCalendarEvents, timeZone, businessHours.start, granularity]);

    // Render calendar events for a specific day (now just returns memoized result)
    const renderCalendarEvents = (dateKey: string) => {
        return memoizedCalendarEvents[dateKey] || null;
    };

    // Render a single grid for a chunk of dates
    const renderGrid = (dateChunk: string[], chunkIndex: number) => {
        const timeSlotCount = Math.floor((businessHours.end - businessHours.start) * 60 / parseInt(granularity));

        return (
            <div key={chunkIndex} className="mb-8">
                {chunkIndex > 0 && (
                    <div className="border-t border-gray-200 my-4"></div>
                )}
                <div className="mb-2">
                    <h4 className="text-sm font-medium text-muted-foreground">
                        {formatDate(dateChunk[0])} - {formatDate(dateChunk[dateChunk.length - 1])}
                    </h4>
                </div>
                <div className="overflow-x-auto">
                    <div className="min-w-max">
                        {/* Header with day selection controls */}
                        <div className={`grid gap-1 p-2 bg-muted/50`} style={{
                            gridTemplateColumns: `100px repeat(${dateChunk.length}, minmax(60px, 1fr))`
                        }}>
                            <div className="p-2 text-sm font-medium text-muted-foreground">Time</div>
                            {dateChunk.map(dateKey => (
                                <div key={dateKey} className="p-2 text-sm font-medium text-center">
                                    <div className="whitespace-normal leading-tight mb-2">
                                        {formatDate(dateKey)}
                                    </div>
                                    {/* Day selection buttons */}
                                    <div className="flex gap-1 justify-center">
                                        <button
                                            type="button"
                                            onClick={() => handleDaySelection(dateKey, 'all')}
                                            className="w-5 h-5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs flex items-center justify-center"
                                            title="Select all available slots"
                                        >
                                            <Check className="h-2 w-2" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => handleDaySelection(dateKey, 'all_times')}
                                            className="w-5 h-5 bg-gray-800 hover:bg-gray-900 text-white rounded text-xs flex items-center justify-center"
                                            title="Select all times regardless of availability"
                                        >
                                            <CheckCheck className="h-2 w-2" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => handleDaySelection(dateKey, 'none')}
                                            className="w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded text-xs flex items-center justify-center"
                                            title="Deselect all slots for this day"
                                        >
                                            <X className="h-2 w-2" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Time Slots Grid - using proven calendar grid structure */}
                        <div className="relative">
                            <div
                                className="grid"
                                style={{
                                    gridTemplateColumns: `100px repeat(${dateChunk.length}, minmax(60px, 1fr))`,
                                    minWidth: `${100 + (dateChunk.length * 60)}px`
                                }}
                            >
                                {/* Time Labels */}
                                <div className="border-r">
                                    {Array.from({ length: timeSlotCount }, (_, i) => {
                                        const hour = businessHours.start + Math.floor(i * parseInt(granularity) / 60);
                                        const minute = (i * parseInt(granularity)) % 60;
                                        const time = new Date();
                                        time.setHours(hour, minute, 0, 0);
                                        return (
                                            <div key={i} className="h-8 border-b border-gray-100 flex items-start justify-end pr-2 text-xs text-gray-500">
                                                {minute === 0 ? formatTime(time.toISOString()) : ''}
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Day Columns */}
                                {dateChunk.map(dateKey => (
                                    <div key={dateKey} className="border-r relative">
                                        {/* Horizontal lines for each time slot */}
                                        {Array.from({ length: timeSlotCount }, (_, i) => (
                                            <div
                                                key={`line-${i}`}
                                                className="absolute left-0 right-0 border-b border-gray-100"
                                                style={{
                                                    top: `${i * 32}px`,
                                                    height: '1px'
                                                }}
                                            />
                                        ))}

                                        {/* Calendar events background layer */}
                                        {renderCalendarEvents(dateKey)}

                                        {/* Time slot buttons on top */}
                                        {slotsByDate[dateKey].map((slot, slotIndex) => {
                                            const isSelected = selectedSlotsSet.has(`${slot.start}-${slot.end}`);
                                            return (
                                                <TimeSlotCell
                                                    key={`${slot.start}-${slot.end}`}
                                                    slot={slot}
                                                    slotIndex={slotIndex}
                                                    isSelected={isSelected}
                                                    onSlotMouseDown={handleSlotMouseDownFactory(dateKey)}
                                                    onSlotMouseEnter={handleSlotMouseEnterFactory(dateKey)}
                                                />
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Select Time Slots</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Date Range Selection */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Date Range Type</Label>
                            <Select value={dateRangeType} onValueChange={(value: 'target' | 'range') => setDateRangeType(value)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="target">Target Date + Range</SelectItem>
                                    <SelectItem value="range">Date Range</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {dateRangeType === 'target' ? (
                            <div className="space-y-2">
                                <Label>Target Date</Label>
                                <input
                                    type="date"
                                    value={targetDate}
                                    onChange={(e) => setTargetDate(e.target.value)}
                                    min={new Date().toISOString().split('T')[0]}
                                    className="w-full border rounded px-3 py-2"
                                />
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 gap-2">
                                <div className="space-y-2">
                                    <Label>Start Date</Label>
                                    <input
                                        type="date"
                                        value={dateRange.startDate.toISOString().split('T')[0]}
                                        onChange={(e) => setDateRange(prev => ({
                                            ...prev,
                                            startDate: new Date(e.target.value)
                                        }))}
                                        min={new Date().toISOString().split('T')[0]}
                                        className="w-full border rounded px-3 py-2"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>End Date</Label>
                                    <input
                                        type="date"
                                        value={dateRange.endDate.toISOString().split('T')[0]}
                                        onChange={(e) => setDateRange(prev => ({
                                            ...prev,
                                            endDate: new Date(e.target.value)
                                        }))}
                                        min={new Date().toISOString().split('T')[0]}
                                        className="w-full border rounded px-3 py-2"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Range Days (for target mode) */}
                    {dateRangeType === 'target' && (
                        <div className="space-y-2">
                            <Label>Days Around Target (±{daysAround})</Label>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                step="1"
                                value={daysAround}
                                onChange={(e) => setDaysAround(parseInt(e.target.value))}
                                className="w-full"
                            />
                            <div className="text-sm text-muted-foreground">
                                Showing {actualDaysInRange} days total {!includeWeekends && '(business days only)'}
                            </div>
                        </div>
                    )}

                    {/* Display Options */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="includeWeekends"
                                checked={includeWeekends}
                                onCheckedChange={(checked) => setIncludeWeekends(checked as boolean)}
                            />
                            <Label htmlFor="includeWeekends">Include Weekends</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="showCalendarEvents"
                                checked={showCalendarEvents}
                                onCheckedChange={(checked) => setShowCalendarEvents(checked as boolean)}
                            />
                            <Label htmlFor="showCalendarEvents" className="flex items-center gap-1">
                                {showCalendarEvents ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                                Show Calendar Events
                            </Label>
                        </div>

                        <div className="space-y-2">
                            <Label>Time Granularity</Label>
                            <Select value={granularity} onValueChange={(value: '15' | '30' | '60') => setGranularity(value)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="15">15 minutes</SelectItem>
                                    <SelectItem value="30">30 minutes</SelectItem>
                                    <SelectItem value="60">1 hour</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Business Hours</Label>
                            <div className="flex gap-2">
                                <input
                                    type="number"
                                    min="0"
                                    max="23"
                                    value={businessHours.start}
                                    onChange={(e) => setBusinessHours(prev => ({
                                        ...prev,
                                        start: parseInt(e.target.value)
                                    }))}
                                    className="w-16 border rounded px-2 py-1 text-center"
                                />
                                <span className="flex items-center">to</span>
                                <input
                                    type="number"
                                    min="0"
                                    max="23"
                                    value={businessHours.end}
                                    onChange={(e) => setBusinessHours(prev => ({
                                        ...prev,
                                        end: parseInt(e.target.value)
                                    }))}
                                    className="w-16 border rounded px-2 py-1 text-center"
                                />
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Calendar Grid */}
            <Card>
                <CardContent className="p-0">
                    {/* Header without navigation */}
                    <div className="flex items-center justify-center p-4 border-b">
                        <div className="text-center">
                            <div className="font-medium">
                                {formatDateFromDate(effectiveDateRange.startDate)} - {formatDateFromDate(effectiveDateRange.endDate)}
                            </div>
                            <div className="text-sm text-blue-600">
                                Select start time options for your{' '}
                                {!isEditingDuration ? (
                                    <span className="text-teal-600 font-medium underline inline-flex items-center">
                                        {formatHeaderDuration(duration)}
                                        <button
                                            type="button"
                                            className="ml-1 text-teal-700 hover:text-teal-800"
                                            onClick={() => {
                                                setIsEditingDuration(true);
                                            }}
                                            title="Edit duration"
                                        >
                                            <Pencil className="h-3 w-3" />
                                        </button>
                                    </span>
                                ) : (
                                    <SmartTimeDurationInput
                                        valueMinutes={duration}
                                        onChangeMinutes={(mins) => {
                                            if (onDurationChange) {
                                                onDurationChange(mins);
                                            }
                                            // Do not clear selected slots; parent recomputes end times for selected starts
                                            setIsEditingDuration(false);
                                        }}
                                        onCancel={() => setIsEditingDuration(false)}
                                        onFinish={() => setIsEditingDuration(false)}
                                        inputClassName="h-7 text-sm w-[100px]"
                                        autoFocus
                                    />
                                )}{' '}
                                meeting
                            </div>
                        </div>
                    </div>

                    {/* Multiple Calendar Grids */}
                    <div className="space-y-4">
                        {dateChunks.length > 0 ? (
                            dateChunks.map((dateChunk, chunkIndex) => renderGrid(dateChunk, chunkIndex))
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                No time slots available for the selected date range.
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Legend */}
            <Card>
                <CardContent className="pt-4">
                    <div className="flex items-center gap-6 text-sm">
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-white border border-gray-300 rounded"></div>
                            <span>Available</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-teal-600 border border-teal-700 rounded"></div>
                            <span>Selected</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-gray-200 border border-gray-300 rounded opacity-50">
                                <Clock className="h-3 w-3 mx-auto" />
                            </div>
                            <span>Conflict</span>
                        </div>
                        {showCalendarEvents && (
                            <div className="flex items-center gap-2">
                                <div className="w-4 h-4 bg-blue-100 border border-blue-300 rounded"></div>
                                <span>Calendar Event</span>
                            </div>
                        )}
                        <div className="flex items-center gap-2">
                            <div className="flex gap-1">
                                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                                <div className="w-3 h-3 bg-gray-800 rounded"></div>
                                <div className="w-3 h-3 bg-red-500 rounded"></div>
                            </div>
                            <span>Day controls: Available | All Times | None</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Summary */}
            {selectedTimeSlots.length > 0 && (
                <Card>
                    <CardContent className="pt-4">
                        <div className="text-sm">
                            <div className="font-medium mb-2">Selected Time Slots ({selectedTimeSlots.length})</div>
                            <div className="space-y-1 max-h-32 overflow-y-auto">
                                {selectedTimeSlots.map((slot, index) => (
                                    <div key={index} className="text-muted-foreground">
                                        {formatDate(slot.start)} at {formatTime(slot.start)} ({timeZone})
                                    </div>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
} 