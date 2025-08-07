'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CalendarEvent } from '@/types/office-service';
import { Check, CheckCheck, Clock, X } from 'lucide-react';
import { DateTime } from 'luxon';
import { useCallback, useMemo, useState } from 'react';

interface TimeSlotCalendarProps {
    duration: number;
    timeZone: string;
    onTimeSlotsChange: (timeSlots: { start: string; end: string }[]) => void;
    selectedTimeSlots: { start: string; end: string }[];
    calendarEvents?: CalendarEvent[];
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

export function TimeSlotCalendar({
    duration,
    timeZone,
    onTimeSlotsChange,
    selectedTimeSlots,
    calendarEvents = []
}: TimeSlotCalendarProps) {
    // Date range selection
    const [dateRangeType, setDateRangeType] = useState<'target' | 'range'>('target');
    const [targetDate, setTargetDate] = useState(() => {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        return tomorrow.toISOString().split('T')[0];
    });
    const [dateRange, setDateRange] = useState<DateRange>({
        startDate: new Date(),
        endDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
    });
    const [rangeDays, setRangeDays] = useState(7);

    // Display options
    const [includeWeekends, setIncludeWeekends] = useState(false);
    const [granularity, setGranularity] = useState<'15' | '30' | '60'>('30');

    // Business hours (configurable)
    const [businessHours, setBusinessHours] = useState({
        start: 9, // 9 AM
        end: 17   // 5 PM
    });

    // Generate date range based on selection type
    const effectiveDateRange = useMemo(() => {
        if (dateRangeType === 'target') {
            const target = new Date(targetDate);
            const start = new Date(target);
            const end = new Date(target);

            if (includeWeekends) {
                // Use calendar days
                const daysBefore = Math.floor((rangeDays - 1) / 2);
                const daysAfter = rangeDays - 1 - daysBefore;
                start.setDate(start.getDate() - daysBefore);
                end.setDate(end.getDate() + daysAfter);
            } else {
                // Use business days
                let daysBefore = Math.floor((rangeDays - 1) / 2);
                let daysAfter = rangeDays - 1 - daysBefore;

                // Calculate business days before
                let currentStart = new Date(target);
                for (let i = 0; i < daysBefore; i++) {
                    currentStart = getPreviousBusinessDay(currentStart);
                }
                start.setTime(currentStart.getTime());

                // Calculate business days after
                let currentEnd = new Date(target);
                for (let i = 0; i < daysAfter; i++) {
                    currentEnd = getNextBusinessDay(currentEnd);
                }
                end.setTime(currentEnd.getTime());
            }

            return { startDate: start, endDate: end };
        } else {
            return dateRange;
        }
    }, [dateRangeType, targetDate, rangeDays, dateRange, includeWeekends]);

    // Generate time slots for the date range
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

                    // Check for conflicts with calendar events
                    const conflictEvents = calendarEvents.filter(event => {
                        const eventStart = new Date(event.start_time);
                        const eventEnd = new Date(event.end_time);
                        return (
                            (slotStart < eventEnd && slotEnd > eventStart) ||
                            (eventStart < slotEnd && eventEnd > slotStart)
                        );
                    });

                    const isConflict = conflictEvents.length > 0;

                    slots.push({
                        start: slotStart.toISOString(),
                        end: slotEnd.toISOString(),
                        isSelected: selectedTimeSlots.some(
                            slot => slot.start === slotStart.toISOString() && slot.end === slotEnd.toISOString()
                        ),
                        isConflict,
                        conflictEvents
                    });
                }
            }
        });

        return slots;
    }, [effectiveDateRange, includeWeekends, granularity, businessHours, duration, calendarEvents, selectedTimeSlots]);

    // Handle slot selection
    const handleSlotClick = useCallback((slot: TimeSlot) => {
        if (slot.isConflict) return; // Don't allow selection of conflicting slots

        const newSelectedSlots = slot.isSelected
            ? selectedTimeSlots.filter(s => !(s.start === slot.start && s.end === slot.end))
            : [...selectedTimeSlots, { start: slot.start, end: slot.end }];

        onTimeSlotsChange(newSelectedSlots);
    }, [selectedTimeSlots, onTimeSlotsChange]);

    // Handle day-level selection
    const handleDaySelection = useCallback((dateKey: string, action: 'all' | 'all_times' | 'none') => {
        const daySlots = slotsByDate[dateKey] || [];
        let newSelectedSlots = [...selectedTimeSlots];

        if (action === 'all') {
            // Add all non-conflicting slots for this day
            const availableSlots = daySlots.filter(slot => !slot.isConflict);
            const slotIds = availableSlots.map(slot => `${slot.start}-${slot.end}`);
            const existingIds = new Set(selectedTimeSlots.map(slot => `${slot.start}-${slot.end}`));

            availableSlots.forEach(slot => {
                if (!existingIds.has(`${slot.start}-${slot.end}`)) {
                    newSelectedSlots.push({ start: slot.start, end: slot.end });
                }
            });
        } else if (action === 'all_times') {
            // Add all slots for this day regardless of availability
            const allSlots = daySlots.filter(slot => !slot.isSelected);
            newSelectedSlots = [...newSelectedSlots, ...allSlots.map(slot => ({ start: slot.start, end: slot.end }))];
        } else if (action === 'none') {
            // Remove all slots for this day
            const daySlotIds = new Set(daySlots.map(slot => `${slot.start}-${slot.end}`));
            newSelectedSlots = selectedTimeSlots.filter(slot => !daySlotIds.has(`${slot.start}-${slot.end}`));
        }

        onTimeSlotsChange(newSelectedSlots);
    }, [selectedTimeSlots, onTimeSlotsChange, slotsByDate]);

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

    // Calculate actual number of days in the range
    const actualDaysInRange = useMemo(() => {
        const start = new Date(effectiveDateRange.startDate);
        const end = new Date(effectiveDateRange.endDate);
        const diffTime = end.getTime() - start.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 for inclusive range
        return diffDays;
    }, [effectiveDateRange]);

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

                        {/* Time Slots Grid */}
                        <div className={`grid gap-1 p-2`} style={{
                            gridTemplateColumns: `100px repeat(${dateChunk.length}, minmax(60px, 1fr))`
                        }}>
                            {/* Time labels */}
                            <div className="space-y-1">
                                {Array.from({ length: timeSlotCount }, (_, i) => {
                                    const hour = businessHours.start + Math.floor(i * parseInt(granularity) / 60);
                                    const minute = (i * parseInt(granularity)) % 60;
                                    const time = new Date();
                                    time.setHours(hour, minute, 0, 0);
                                    return (
                                        <div key={i} className="h-8 flex items-center text-xs text-muted-foreground">
                                            {formatTime(time.toISOString())}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Time slot cells */}
                            {dateChunk.map(dateKey => (
                                <div key={dateKey} className="space-y-1">
                                    {slotsByDate[dateKey].map((slot, slotIndex) => (
                                        <button
                                            key={slotIndex}
                                            type="button"
                                            onClick={() => handleSlotClick(slot)}
                                            disabled={slot.isConflict}
                                            className={`
                                                w-full h-8 rounded border text-xs transition-colors
                                                ${slot.isConflict
                                                    ? 'bg-gray-200 border-gray-300 cursor-not-allowed opacity-50'
                                                    : slot.isSelected
                                                        ? 'bg-teal-600 border-teal-700 text-white hover:bg-teal-700'
                                                        : 'bg-white border-gray-300 hover:bg-gray-50 hover:border-gray-400'
                                                }
                                            `}
                                            title={slot.isConflict
                                                ? `Conflict: ${slot.conflictEvents.map(e => e.title).join(', ')}`
                                                : `Click to ${slot.isSelected ? 'deselect' : 'select'} this time slot`
                                            }
                                        >
                                            {slot.isConflict && <Clock className="h-3 w-3 mx-auto" />}
                                        </button>
                                    ))}
                                </div>
                            ))}
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
                                        className="w-full border rounded px-3 py-2"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Range Days (for target mode) */}
                    {dateRangeType === 'target' && (
                        <div className="space-y-2">
                            <Label>Days Around Target (±{Math.floor(rangeDays / 2)})</Label>
                            <input
                                type="range"
                                min="3"
                                max="14"
                                step="1"
                                value={rangeDays}
                                onChange={(e) => setRangeDays(parseInt(e.target.value))}
                                className="w-full"
                            />
                            <div className="text-sm text-muted-foreground">
                                Showing {actualDaysInRange} days total {!includeWeekends && '(business days only)'}
                            </div>
                        </div>
                    )}

                    {/* Display Options */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="includeWeekends"
                                checked={includeWeekends}
                                onCheckedChange={(checked) => setIncludeWeekends(checked as boolean)}
                            />
                            <Label htmlFor="includeWeekends">Include Weekends</Label>
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
                                {formatDate(effectiveDateRange.startDate.toISOString())} - {formatDate(effectiveDateRange.endDate.toISOString())}
                            </div>
                            <div className="text-sm text-muted-foreground">
                                {Object.keys(slotsByDate).length} days, {timeSlots.length} time slots
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