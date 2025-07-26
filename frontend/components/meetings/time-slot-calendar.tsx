'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CalendarEvent } from '@/types/office-service';
import { ChevronLeft, ChevronRight, Clock } from 'lucide-react';
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
    const [showWeekends, setShowWeekends] = useState(true);
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
            start.setDate(start.getDate() - Math.floor(rangeDays / 2));
            const end = new Date(target);
            end.setDate(end.getDate() + Math.floor(rangeDays / 2));
            return { startDate: start, endDate: end };
        } else {
            return dateRange;
        }
    }, [dateRangeType, targetDate, rangeDays, dateRange]);

    // Generate time slots for the date range
    const timeSlots = useMemo(() => {
        const slots: TimeSlot[] = [];
        const granularityMinutes = parseInt(granularity);

        // Generate dates
        const dates: Date[] = [];
        const current = new Date(effectiveDateRange.startDate);
        while (current <= effectiveDateRange.endDate) {
            const dayOfWeek = current.getDay();
            if (showWeekends || (dayOfWeek !== 0 && dayOfWeek !== 6)) {
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
    }, [effectiveDateRange, showWeekends, granularity, businessHours, duration, calendarEvents, selectedTimeSlots]);

    // Handle slot selection
    const handleSlotClick = useCallback((slot: TimeSlot) => {
        if (slot.isConflict) return; // Don't allow selection of conflicting slots

        const newSelectedSlots = slot.isSelected
            ? selectedTimeSlots.filter(s => !(s.start === slot.start && s.end === slot.end))
            : [...selectedTimeSlots, { start: slot.start, end: slot.end }];

        onTimeSlotsChange(newSelectedSlots);
    }, [selectedTimeSlots, onTimeSlotsChange]);

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

    // Format time for display
    const formatTime = (isoString: string) => {
        return DateTime.fromISO(isoString).setZone(timeZone).toFormat('h:mm a');
    };

    // Format date for display
    const formatDate = (dateString: string) => {
        return DateTime.fromISO(dateString).setZone(timeZone).toFormat('EEE, MMM d');
    };

    // Navigation
    const navigateDateRange = (direction: 'prev' | 'next') => {
        const days = direction === 'next' ? rangeDays : -rangeDays;
        if (dateRangeType === 'target') {
            const newTarget = new Date(targetDate);
            newTarget.setDate(newTarget.getDate() + days);
            setTargetDate(newTarget.toISOString().split('T')[0]);
        } else {
            const newStart = new Date(dateRange.startDate);
            newStart.setDate(newStart.getDate() + days);
            const newEnd = new Date(dateRange.endDate);
            newEnd.setDate(newEnd.getDate() + days);
            setDateRange({ startDate: newStart, endDate: newEnd });
        }
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
                                Showing {rangeDays} days total
                            </div>
                        </div>
                    )}

                    {/* Display Options */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="showWeekends"
                                checked={showWeekends}
                                onCheckedChange={(checked) => setShowWeekends(checked as boolean)}
                            />
                            <Label htmlFor="showWeekends">Show Weekends</Label>
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
                    {/* Navigation */}
                    <div className="flex items-center justify-between p-4 border-b">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigateDateRange('prev')}
                        >
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            Previous
                        </Button>

                        <div className="text-center">
                            <div className="font-medium">
                                {formatDate(effectiveDateRange.startDate.toISOString())} - {formatDate(effectiveDateRange.endDate.toISOString())}
                            </div>
                            <div className="text-sm text-muted-foreground">
                                {Object.keys(slotsByDate).length} days, {timeSlots.length} time slots
                            </div>
                        </div>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigateDateRange('next')}
                        >
                            Next
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    </div>

                    {/* Calendar Grid */}
                    <div className="overflow-x-auto">
                        <div className="min-w-max">
                            {/* Header */}
                            <div className="grid grid-cols-[100px_repeat(auto-fit,minmax(120px,1fr))] gap-1 p-2 bg-muted/50">
                                <div className="p-2 text-sm font-medium text-muted-foreground">Time</div>
                                {Object.keys(slotsByDate).map(dateKey => (
                                    <div key={dateKey} className="p-2 text-sm font-medium text-center">
                                        {formatDate(dateKey)}
                                    </div>
                                ))}
                            </div>

                            {/* Time Slots Grid */}
                            <div className="grid grid-cols-[100px_repeat(auto-fit,minmax(120px,1fr))] gap-1 p-2">
                                {/* Time labels */}
                                <div className="space-y-1">
                                    {Array.from({ length: Math.floor((businessHours.end - businessHours.start) * 60 / parseInt(granularity)) }, (_, i) => {
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
                                {Object.keys(slotsByDate).map(dateKey => (
                                    <div key={dateKey} className="space-y-1">
                                        {slotsByDate[dateKey].map((slot, slotIndex) => (
                                            <button
                                                key={slotIndex}
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