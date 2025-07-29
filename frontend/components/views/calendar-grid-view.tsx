"use client"

import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useIntegrations } from '@/contexts/integrations-context';
import { useUserPreferences } from '@/contexts/settings-context';
import { gatewayClient } from '@/lib/gateway-client';
import type { CalendarEvent } from '@/types/office-service';
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { DateTime } from 'luxon';
import { getSession } from 'next-auth/react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarGridEvent } from './calendar-grid-event';

interface CalendarGridViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
}

type ViewType = 'day' | 'work-week' | 'week' | 'month';

interface TimeSlot {
    hour: number;
    minute: number;
    time: string;
}

export default function CalendarGridView({ toolDataLoading = false, activeTool }: CalendarGridViewProps) {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentDate, setCurrentDate] = useState(() => new Date());
    const [viewType, setViewType] = useState<ViewType>('week');

    const { loading: integrationsLoading, activeProviders } = useIntegrations();
    const { effectiveTimezone } = useUserPreferences();

    // Calculate date range based on view type
    const dateRange = useMemo(() => {
        const start = new Date(currentDate);
        const end = new Date(currentDate);

        let result;

        switch (viewType) {
            case 'day':
                // Single day - set start to beginning of day and end to end of day
                const dayStart = new Date(start);
                dayStart.setHours(0, 0, 0, 0);
                const dayEnd = new Date(start);
                dayEnd.setHours(23, 59, 59, 999);
                result = { start: dayStart, end: dayEnd };
                break;
            case 'work-week':
                // Monday to Friday
                const dayOfWeek = start.getDay();
                const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Sunday = 0, Monday = 1
                const monday = new Date(start);
                monday.setDate(start.getDate() - daysToMonday);
                monday.setHours(0, 0, 0, 0);
                const friday = new Date(monday);
                friday.setDate(monday.getDate() + 4); // Monday + 4 = Friday
                friday.setHours(23, 59, 59, 999);
                result = { start: monday, end: friday };
                break;
            case 'week':
                // Sunday to Saturday
                const daysToSunday = start.getDay();
                const sunday = new Date(start);
                sunday.setDate(start.getDate() - daysToSunday);
                sunday.setHours(0, 0, 0, 0);
                const saturday = new Date(sunday);
                saturday.setDate(sunday.getDate() + 6);
                saturday.setHours(23, 59, 59, 999);
                result = { start: sunday, end: saturday };
                break;
            case 'month':
                // First day of month to last day of month
                const firstDay = new Date(start.getFullYear(), start.getMonth(), 1);
                firstDay.setHours(0, 0, 0, 0);
                const lastDay = new Date(start.getFullYear(), start.getMonth() + 1, 0);
                lastDay.setHours(23, 59, 59, 999);
                result = { start: firstDay, end: lastDay };
                break;
        }



        return result;
    }, [currentDate, viewType]);

    // Generate time slots (6 AM to 10 PM)
    const timeSlots = useMemo(() => {
        const slots: TimeSlot[] = [];
        for (let hour = 6; hour <= 22; hour++) {
            for (let minute = 0; minute < 60; minute += 30) {
                // Create a simple time string in the user's timezone
                const timeString = `${hour}:${minute.toString().padStart(2, '0')}`;
                const time = DateTime.fromFormat(timeString, 'H:mm', { zone: effectiveTimezone });
                slots.push({
                    hour,
                    minute,
                    time: time.toFormat('h:mm a')
                });
            }
        }
        return slots;
    }, [effectiveTimezone]);

    // Generate days for the current view
    const days = useMemo(() => {
        const daysArray: Date[] = [];
        const current = new Date(dateRange.start);

        while (current <= dateRange.end) {
            daysArray.push(new Date(current));
            current.setDate(current.getDate() + 1);
        }

        return daysArray;
    }, [dateRange.start, dateRange.end]);

    // Filter events for the current date range
    const filteredEvents = useMemo(() => {
        return events.filter(event => {
            const eventStart = new Date(event.start_time);
            const eventEnd = new Date(event.end_time);
            return eventStart <= dateRange.end && eventEnd >= dateRange.start;
        });
    }, [events, dateRange]);

    // Group events by day
    const eventsByDay = useMemo(() => {
        const grouped: Record<string, CalendarEvent[]> = {};
        days.forEach(day => {
            const dayKey = DateTime.fromJSDate(day).setZone(effectiveTimezone).toFormat('yyyy-MM-dd');
            grouped[dayKey] = filteredEvents.filter(event => {
                const eventStart = DateTime.fromISO(event.start_time).setZone(effectiveTimezone);
                const eventDate = eventStart.toFormat('yyyy-MM-dd');
                return eventDate === dayKey;
            });
        });
        return grouped;
    }, [filteredEvents, days, effectiveTimezone]);

    const fetchCalendarEvents = useCallback(async (noCache = false) => {
        if (!activeProviders || activeProviders.length === 0) {
            return;
        }

        try {
            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');



            const response = await gatewayClient.getCalendarEvents(
                activeProviders,
                100, // Increased limit for grid view
                dateRange.start.toISOString().split('T')[0],
                dateRange.end.toISOString().split('T')[0],
                undefined,
                undefined,
                effectiveTimezone,
                noCache
            );

            if (response.success && response.data) {
                const events = Array.isArray(response.data) ? response.data : [];
                setEvents(events);
                setError(null);
            } else {
                setError('Failed to fetch calendar events');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load calendar events' : 'Failed to load calendar events');
        }
    }, [activeProviders, dateRange, effectiveTimezone]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchCalendarEvents(true);
        } finally {
            setRefreshing(false);
        }
    }, [fetchCalendarEvents]);

    const navigateDate = useCallback((direction: 'prev' | 'next') => {
        const newDate = new Date(currentDate);
        switch (viewType) {
            case 'day':
                newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1));
                break;
            case 'work-week':
            case 'week':
                newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7));
                break;
            case 'month':
                newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1));
                break;
        }
        setCurrentDate(newDate);
    }, [currentDate, viewType]);

    const goToToday = useCallback(() => {
        setCurrentDate(new Date());
    }, []);

    useEffect(() => {
        if (toolDataLoading) return;
        if (integrationsLoading) return;
        if (!activeProviders || activeProviders.length === 0) {
            setError('No active calendar integrations found. Please connect your calendar account first.');
            setEvents([]);
            setLoading(false);
            return;
        }
        if (activeTool !== 'calendar') {
            setLoading(false);
            return;
        }

        let isMounted = true;
        setLoading(true);
        (async () => {
            try {
                await fetchCalendarEvents(false);
            } finally {
                if (isMounted) setLoading(false);
            }
        })();
        return () => { isMounted = false; };
    }, [activeProviders, integrationsLoading, toolDataLoading, activeTool, fetchCalendarEvents]);

    // Format date for display
    const formatDate = (date: Date) => {
        return DateTime.fromJSDate(date).setZone(effectiveTimezone).toFormat('EEE MMM d');
    };

    // Format date for header
    const formatDateHeader = (date: Date) => {
        const today = new Date();
        const isToday = date.toDateString() === today.toDateString();
        const dayName = DateTime.fromJSDate(date).setZone(effectiveTimezone).toFormat('EEE');
        const dayNumber = date.getDate();

        return (
            <div className={`text-center ${isToday ? 'bg-blue-100 rounded' : ''}`}>
                <div className="text-xs text-gray-500">{dayName}</div>
                <div className={`text-lg font-semibold ${isToday ? 'text-blue-600' : ''}`}>
                    {dayNumber}
                </div>
            </div>
        );
    };

    // Check for integration status
    const hasActiveCalendarIntegration = activeProviders.length > 0;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3">Loading calendar...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-red-600">
                Error: {error}
            </div>
        );
    }

    if (!hasActiveCalendarIntegration) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <p className="text-gray-600 mb-4">No active calendar integration found.</p>
                    <p className="text-sm text-gray-500">Connect your Google Calendar or Microsoft Outlook to view your events.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-white">
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={goToToday}>
                        Today
                    </Button>
                    <div className="flex items-center gap-1">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigateDate('prev')}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigateDate('next')}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="ml-4 font-semibold">
                        {viewType === 'day' && formatDate(currentDate)}
                        {viewType === 'work-week' && `${formatDate(dateRange.start)} - ${formatDate(dateRange.end)}`}
                        {viewType === 'week' && `${formatDate(dateRange.start)} - ${formatDate(dateRange.end)}`}
                        {viewType === 'month' && DateTime.fromJSDate(currentDate).setZone(effectiveTimezone).toFormat('MMMM yyyy')}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Select value={viewType} onValueChange={(value: ViewType) => setViewType(value)}>
                        <SelectTrigger className="w-32">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="day">Day</SelectItem>
                            <SelectItem value="work-week">Work week</SelectItem>
                            <SelectItem value="week">Week</SelectItem>
                            <SelectItem value="month">Month</SelectItem>
                        </SelectContent>
                    </Select>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={refreshing}
                    >
                        <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                    </Button>
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="flex-1 overflow-auto">
                <div className="min-h-full" style={{ minWidth: `${60 + (days.length * 120)}px` }}>
                    {/* Day Headers */}
                    <div className="sticky top-0 z-10 bg-white border-b">
                        <div
                            className="grid border-b"
                            style={{
                                gridTemplateColumns: `60px repeat(${days.length}, minmax(120px, 1fr))`,
                                minWidth: `${60 + (days.length * 120)}px`
                            }}
                        >
                            <div className="p-2 border-r bg-gray-50"></div>
                            {days.map((day, index) => (
                                <div key={index} className="p-2 border-r">
                                    {formatDateHeader(day)}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* All-day events section */}
                    {viewType !== 'day' && (
                        <div className="border-b bg-gray-50">
                            <div
                                className="grid"
                                style={{
                                    gridTemplateColumns: `60px repeat(${days.length}, minmax(120px, 1fr))`,
                                    minWidth: `${60 + (days.length * 120)}px`
                                }}
                            >
                                <div className="p-2 border-r bg-gray-50 text-xs text-gray-500 font-medium">
                                    All day
                                </div>
                                {days.map((day, dayIndex) => (
                                    <div key={dayIndex} className="border-r relative min-h-[32px] p-1">
                                        {eventsByDay[DateTime.fromJSDate(day).setZone(effectiveTimezone).toFormat('yyyy-MM-dd')]?.filter(event => event.all_day).map((event) => (
                                            <CalendarGridEvent
                                                key={event.id}
                                                event={event}
                                                day={day}
                                                effectiveTimezone={effectiveTimezone}
                                            />
                                        ))}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Time Grid */}
                    <div className="relative">
                        <div
                            className="grid"
                            style={{
                                gridTemplateColumns: `60px repeat(${days.length}, minmax(120px, 1fr))`,
                                minWidth: `${60 + (days.length * 120)}px`
                            }}
                        >
                            {/* Time Labels */}
                            <div className="border-r">
                                {timeSlots.map((slot, index) => (
                                    <div
                                        key={index}
                                        className="h-8 border-b border-gray-100 flex items-start justify-end pr-2 text-xs text-gray-500"
                                    >
                                        {slot.minute === 0 ? slot.time : ''}
                                    </div>
                                ))}
                            </div>

                            {/* Day Columns */}
                            {days.map((day, dayIndex) => (
                                <div key={dayIndex} className="border-r relative">
                                    {/* Current time indicator */}
                                    {(() => {
                                        const now = DateTime.now().setZone(effectiveTimezone);
                                        const today = DateTime.now().setZone(effectiveTimezone);
                                        const dayDate = DateTime.fromJSDate(day).setZone(effectiveTimezone);

                                        if (dayDate.toFormat('yyyy-MM-dd') === today.toFormat('yyyy-MM-dd')) {
                                            const currentHour = now.hour + now.minute / 60;
                                            const gridStartHour = 6;
                                            const gridEndHour = 22;
                                            if (currentHour >= gridStartHour && currentHour <= gridEndHour) {
                                                const topPercent = ((currentHour - gridStartHour) / (gridEndHour - gridStartHour)) * 100;
                                                const totalHeight = (gridEndHour - gridStartHour) * 2 * 16; // 16px per 30-min slot
                                                const topPixels = (topPercent / 100) * totalHeight;

                                                return (
                                                    <div
                                                        className="absolute left-0 right-0 z-10 pointer-events-none"
                                                        style={{ top: `${topPixels}px` }}
                                                    >
                                                        <div className="flex items-center">
                                                            <div className="w-2 h-2 bg-red-500 rounded-full -ml-1"></div>
                                                            <div className="flex-1 h-0.5 bg-red-500"></div>
                                                        </div>
                                                    </div>
                                                );
                                            }
                                        }
                                        return null;
                                    })()}

                                    {/* Time slots */}
                                    {timeSlots.map((slot, slotIndex) => (
                                        <div
                                            key={slotIndex}
                                            className="h-8 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                                            onClick={() => {
                                                // Future: Create event on click
                                                console.log('Create event at:', day, slot.time);
                                            }}
                                        />
                                    ))}

                                    {/* Events for this day */}
                                    <div className="absolute inset-0 pointer-events-none">
                                        {(() => {
                                            const dayKey = DateTime.fromJSDate(day).setZone(effectiveTimezone).toFormat('yyyy-MM-dd');
                                            const dayEvents = eventsByDay[dayKey]?.filter(event => !event.all_day) || [];
                                            return dayEvents.map((event) => (
                                                <CalendarGridEvent
                                                    key={event.id}
                                                    event={event}
                                                    day={day}
                                                    effectiveTimezone={effectiveTimezone}
                                                />
                                            ));
                                        })()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
} 