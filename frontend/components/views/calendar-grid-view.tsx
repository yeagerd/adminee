"use client"

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { useIntegrations } from '@/contexts/integrations-context';
import { useUserPreferences } from '@/contexts/settings-context';
import { gatewayClient } from '@/lib/gateway-client';
import type { CalendarEvent } from '@/types/office-service';
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { DateTime } from 'luxon';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CalendarEventItem } from '../calendar-event-item';
import { CalendarGridEvent } from './calendar-grid-event';

interface CalendarGridViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
    events?: CalendarEvent[];
    loading?: boolean;
    refreshing?: boolean;
    error?: string | null;
    onRefresh?: () => void;
}

type ViewType = 'day' | 'work-week' | 'week' | 'month' | 'list';

interface TimeSlot {
    hour: number;
    minute: number;
    time: string;
}

export default function CalendarGridView({
    toolDataLoading = false,
    activeTool,
    events: externalEvents,
    loading: externalLoading,
    refreshing: externalRefreshing,
    error: externalError,
    onRefresh
}: CalendarGridViewProps) {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentDate, setCurrentDate] = useState(() => new Date());
    const [viewType, setViewType] = useState<ViewType>('week');
    const { toast } = useToast();

    // Selection state for creating a new event
    const [isSelecting, setIsSelecting] = useState(false);
    const selectionStartRef = useRef<{ day: Date; slotIndex: number } | null>(null);
    const [selection, setSelection] = useState<null | { day: Date; startIndex: number; endIndex: number }>(null);
    const [hoverPreview, setHoverPreview] = useState<null | { day: Date; slotIndex: number }>(null);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [formTitle, setFormTitle] = useState('');
    const [formDescription, setFormDescription] = useState('');
    const [formLocation, setFormLocation] = useState('');
    const [formAllDay, setFormAllDay] = useState(false);
    const [formStartTime, setFormStartTime] = useState<Date | null>(null);
    const [formEndTime, setFormEndTime] = useState<Date | null>(null);
    const [formAttendees, setFormAttendees] = useState<Array<{ id: string; email: string; name: string }>>([]);
    const [attendeeQuery, setAttendeeQuery] = useState('');

    const { loading: integrationsLoading, activeProviders } = useIntegrations();
    const { effectiveTimezone } = useUserPreferences();

    // Derived start/end from current selection
    const selectedStartEnd = useMemo(() => {
        if (!selection) return null;
        const gridStartHour = 6;
        const slotMinutes = 15;
        const startSlot = Math.min(selection.startIndex, selection.endIndex);
        const endSlot = Math.max(selection.startIndex, selection.endIndex) + 1; // inclusive end slot -> add 1

        // Build start/end as Zoned DateTimes in effectiveTimezone, then output JS Dates representing the same instant
        const selectionDay = DateTime.fromJSDate(selection.day).setZone(effectiveTimezone);
        const startHours = gridStartHour + Math.floor(startSlot / 4);
        const startMinutes = (startSlot % 4) * slotMinutes;
        const startZoned = selectionDay.set({ hour: startHours, minute: startMinutes, second: 0, millisecond: 0 });
        const endHours = gridStartHour + Math.floor(endSlot / 4);
        const endMinutes = (endSlot % 4) * slotMinutes;
        const endZoned = selectionDay.set({ hour: endHours, minute: endMinutes, second: 0, millisecond: 0 });

        // Convert to JS Dates preserving the actual instant in time
        const start = new Date(startZoned.toMillis());
        const end = new Date(endZoned.toMillis());
        return { start, end };
    }, [selection, effectiveTimezone]);

    const clearSelection = useCallback(() => {
        setIsSelecting(false);
        selectionStartRef.current = null;
        setSelection(null);
        setHoverPreview(null);
    }, []);

    const handleStartTimeChange = useCallback((newStartTime: Date) => {
        if (!formEndTime) return;

        // Calculate duration in milliseconds
        const duration = formEndTime.getTime() - formStartTime!.getTime();

        // Set new start time
        setFormStartTime(newStartTime);

        // Adjust end time to maintain duration
        const newEndTime = new Date(newStartTime.getTime() + duration);
        setFormEndTime(newEndTime);
    }, [formStartTime, formEndTime]);

        const handleEndTimeChange = useCallback((newEndTime: Date) => {
        if (!formStartTime) return;
        
        // Set new end time (this changes the duration)
        setFormEndTime(newEndTime);
    }, [formStartTime]);

    const addAttendee = useCallback((email: string, name?: string) => {
        const newAttendee = {
            id: Math.random().toString(36).substr(2, 9),
            email: email.trim(),
            name: name?.trim() || ''
        };
        setFormAttendees(prev => [...prev, newAttendee]);
        setAttendeeQuery('');
    }, []);

    const removeAttendee = useCallback((id: string) => {
        setFormAttendees(prev => prev.filter(attendee => attendee.id !== id));
    }, []);

    const parseAttendeeFromText = useCallback((text: string): Array<{ email: string; name?: string }> => {
        const results: Array<{ email: string; name?: string }> = [];
        const lines = text.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            
            // Try to parse "Name <email@domain.com>" format
            const emailMatch = trimmed.match(/<(.+?)>/);
            if (emailMatch) {
                const email = emailMatch[1].trim();
                const name = trimmed.replace(/<.+?>/, '').trim();
                if (email && email.includes('@')) {
                    results.push({ email, name: name || undefined });
                }
            } else if (trimmed.includes('@')) {
                // Just an email address
                results.push({ email: trimmed });
            }
        }
        
        return results;
    }, []);

    // Use external props if provided, otherwise use internal state
    // For list view, always use internal events to support navigation
    const finalEvents = viewType === 'list' ? events : (externalEvents || events);
    const finalLoading = viewType === 'list' ? loading : (externalLoading !== undefined ? externalLoading : loading);
    const finalRefreshing = viewType === 'list' ? refreshing : (externalRefreshing !== undefined ? externalRefreshing : refreshing);
    const finalError = viewType === 'list' ? error : (externalError !== undefined ? externalError : error);

    // Calculate date range based on view type
    const dateRange = useMemo(() => {
        const start = new Date(currentDate);

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
            case 'list':
                // List view - show next 7 days
                const listStart = new Date(start);
                listStart.setHours(0, 0, 0, 0);
                const listEnd = new Date(start);
                listEnd.setDate(start.getDate() + 7);
                listEnd.setHours(23, 59, 59, 999);
                result = { start: listStart, end: listEnd };
                break;
        }



        return result;
    }, [currentDate, viewType]);

    // Generate time slots (6 AM to 10 PM) - 15 minute increments
    const timeSlots = useMemo(() => {
        const slots: TimeSlot[] = [];
        for (let hour = 6; hour <= 22; hour++) {
            for (let minute = 0; minute < 60; minute += 15) {
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

            // For list view, only include events that start within the date range
            if (viewType === 'list') {
                return eventStart >= dateRange.start && eventStart <= dateRange.end;
            }

            // For grid views, include events that overlap with the date range
            return eventStart <= dateRange.end && eventEnd >= dateRange.start;
        });
    }, [events, dateRange, viewType]);

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
            // const session = await getSession();
            // const userId = session?.user?.id;
            // if (!userId) throw new Error('No user id found in session');



            // Convert date range to UTC for API call
            const startUTC = DateTime.fromJSDate(dateRange.start).setZone(effectiveTimezone).startOf('day').toUTC();
            const endUTC = DateTime.fromJSDate(dateRange.end).setZone(effectiveTimezone).endOf('day').toUTC();



            const response = await gatewayClient.getCalendarEvents(
                activeProviders,
                100, // Increased limit for grid view
                startUTC.toFormat('yyyy-MM-dd'),
                endUTC.toFormat('yyyy-MM-dd'),
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
            case 'list':
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

    // Fetch events when date range changes (for list view or when not using external events)
    useEffect(() => {
        if (viewType !== 'list' && externalEvents !== undefined) return; // Don't fetch if using external events (except for list view)
        if (toolDataLoading) return;
        if (integrationsLoading) return;
        if (!activeProviders || activeProviders.length === 0) return;
        if (activeTool !== 'calendar') return;

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
    }, [dateRange, viewType, externalEvents, toolDataLoading, integrationsLoading, activeProviders, activeTool, fetchCalendarEvents]);

    // Initialize form times when selection changes
    useEffect(() => {
        if (selectedStartEnd) {
            setFormStartTime(selectedStartEnd.start);
            setFormEndTime(selectedStartEnd.end);
        }
    }, [selectedStartEnd]);

    // Global mouse event handlers for drag selection
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isSelecting || !selectionStartRef.current) return;

            // Try to find the time slot element under the mouse
            const target = e.target as HTMLElement;
            const timeSlot = target.closest('[data-slot-index]');
            let dayElement = null;
            let slotIndex = 0;
            let day = null;

            // If closest() doesn't work, try to find by mouse position
            if (!timeSlot) {
                // Find the calendar grid container
                const calendarGrid = document.querySelector('[data-calendar-grid]');
                if (calendarGrid) {
                    const rect = calendarGrid.getBoundingClientRect();
                    const mouseY = e.clientY - rect.top;

                    // Calculate slot index based on mouse Y position
                    // Each slot is 12px (h-3), grid starts at 6 AM
                    const gridStartY = 0; // Assuming grid starts at top
                    const slotHeight = 12;
                    const calculatedSlotIndex = Math.floor((mouseY - gridStartY) / slotHeight);

                    if (calculatedSlotIndex >= 0 && calculatedSlotIndex < 64) { // 6 AM to 10 PM = 16 hours * 4 slots per hour
                        slotIndex = calculatedSlotIndex;

                        // Find the day column by mouse X position
                        const mouseX = e.clientX - rect.left;
                        const dayWidth = rect.width / (days.length + 1); // +1 for time labels column
                        const dayIndex = Math.floor((mouseX - 60) / dayWidth); // 60px for time labels

                        if (dayIndex >= 0 && dayIndex < days.length) {
                            day = days[dayIndex];
                        }
                    }
                }
            } else {
                // Use the original closest() approach
                slotIndex = parseInt(timeSlot.getAttribute('data-slot-index') || '0');
                dayElement = timeSlot.closest('[data-day]');

                if (!dayElement) return;

                const dayString = dayElement.getAttribute('data-day');
                if (!dayString) return;
                day = new Date(dayString);
            }

            if (day && day.toDateString() === selectionStartRef.current.day.toDateString()) {
                // Ensure minimum selection of 1 slot (15 minutes) when dragging
                const startIndex = selectionStartRef.current.slotIndex;
                let endIndex = slotIndex;

                // If dragging backwards, ensure we have at least 1 slot
                if (endIndex < startIndex) {
                    endIndex = Math.max(startIndex - 1, 0);
                }

                setSelection({
                    day,
                    startIndex,
                    endIndex
                });
            }
        };

        const handleMouseUp = () => {
            if (isSelecting && selectionStartRef.current) {
                setIsSelecting(false);
                if (selection) {
                    setIsCreateOpen(true);
                }
            }
        };

        if (isSelecting) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isSelecting, selection, days]);

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
                <div className="flex items-center gap-4">
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
                        {viewType === 'list' && `${formatDate(dateRange.start)} - ${formatDate(dateRange.end)}`}
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
                            <SelectItem value="list">List</SelectItem>
                        </SelectContent>
                    </Select>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onRefresh || handleRefresh}
                        disabled={finalRefreshing}
                    >
                        <RefreshCw className={`h-4 w-4 ${finalRefreshing ? 'animate-spin' : ''}`} />
                    </Button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto">
                {viewType === 'list' ? (
                    <div className="p-6">
                        {finalLoading && (
                            <div className="flex items-center justify-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                                <span className="ml-3">Loading calendar events...</span>
                            </div>
                        )}

                        {finalError && (
                            <div className="p-3 bg-red-100 border border-red-300 rounded text-red-700 mb-6">
                                Error: {finalError}
                            </div>
                        )}

                        {!finalLoading && finalEvents.length === 0 && !finalError && (
                            <div className="text-center py-8 text-muted-foreground">
                                <p>No calendar events found.</p>
                            </div>
                        )}

                        {!finalLoading && finalEvents.length > 0 && (
                            <div className="space-y-4">
                                {finalEvents.map((event) => (
                                    <CalendarEventItem key={event.id} event={event} effectiveTimezone={effectiveTimezone} />
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
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
                                className="grid select-none"
                                data-calendar-grid
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
                                            className={`h-3 flex items-start justify-end pr-2 text-xs text-gray-500 ${index % 4 === 3 ? 'border-b border-gray-200' : ''
                                                }`}
                                        >
                                            {slot.minute === 0 ? slot.time : ''}
                                        </div>
                                    ))}
                                </div>

                                {/* Day Columns */}
                                {days.map((day, dayIndex) => (
                                    <div
                                        key={dayIndex}
                                        className="border-r relative"
                                        data-day={day.toISOString()}
                                    >
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
                                                    const totalHeight = (gridEndHour - gridStartHour) * 4 * 12; // 12px per 15-min slot (h-3)
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

                                        {/* Hover preview (30-minute shadow) */}
                                        {!isSelecting && hoverPreview && hoverPreview.day.toDateString() === day.toDateString() && (() => {
                                            const topPos = hoverPreview.slotIndex * 12;
                                            const height = 2 * 12; // 2 slots = 30 minutes

                                            return (
                                                <div
                                                    className="absolute left-0 right-0 pointer-events-none z-15"
                                                    style={{
                                                        top: `${topPos}px`,
                                                        height: `${height}px`,
                                                    }}
                                                >
                                                    <div
                                                        className="mx-1 rounded-md bg-blue-300/40 border border-blue-400/60"
                                                        style={{
                                                            height: '100%',
                                                            transition: 'all 0.1s ease-out'
                                                        }}
                                                    />
                                                </div>
                                            );
                                        })()}

                                        {/* Selection overlay (drag) */}
                                        {selection && selection.day.toDateString() === day.toDateString() && (() => {
                                            const topPos = Math.min(selection.startIndex, selection.endIndex) * 12;
                                            const height = (Math.abs(selection.endIndex - selection.startIndex) + 1) * 12;

                                            return (
                                                <div
                                                    key={`selection-${selection.startIndex}-${selection.endIndex}`}
                                                    className="absolute left-0 right-0 pointer-events-none z-20"
                                                    style={{
                                                        top: `${topPos}px`,
                                                        height: `${height}px`,
                                                    }}
                                                >
                                                    <div
                                                        className="mx-1 rounded-md bg-blue-500/70 border border-blue-600 shadow-lg"
                                                        style={{
                                                            height: '100%',
                                                            transition: 'all 0.1s ease-out'
                                                        }}
                                                    />
                                                </div>
                                            );
                                        })()}


                                        {/* Time slots */}
                                        {timeSlots.map((slot, slotIndex) => (
                                            <div
                                                key={slotIndex}
                                                className={`h-3 hover:bg-gray-50 cursor-pointer transition-colors ${slotIndex % 4 === 3 ? 'border-b border-gray-200' : ''
                                                    }`}
                                                data-slot-index={slotIndex}
                                                onMouseEnter={() => {
                                                    if (!isSelecting) {
                                                        setHoverPreview({ day, slotIndex });
                                                    }
                                                }}
                                                onMouseLeave={() => {
                                                    if (!isSelecting) {
                                                        setHoverPreview(null);
                                                    }
                                                }}
                                                onMouseDown={() => {
                                                    setHoverPreview(null);
                                                    setIsSelecting(true);
                                                    selectionStartRef.current = { day, slotIndex };
                                                    setSelection({ day, startIndex: slotIndex, endIndex: slotIndex });
                                                }}
                                                onClick={() => {
                                                    // Single click create (30 min slot - 2 slots)
                                                    setSelection({ day, startIndex: slotIndex, endIndex: slotIndex + 1 });
                                                    setIsCreateOpen(true);
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
                )}
            </div>

            {/* Create Event Modal */}
            <Dialog open={isCreateOpen} onOpenChange={(open) => {
                setIsCreateOpen(open);
                                if (!open) {
                    setFormTitle('');
                    setFormDescription('');
                    setFormLocation('');
                    setFormAllDay(false);
                    setFormStartTime(null);
                    setFormEndTime(null);
                    setFormAttendees([]);
                    setAttendeeQuery('');
                    clearSelection();
                }
            }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>New meeting</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="title">Title</Label>
                            <Input id="title" value={formTitle} onChange={(e) => setFormTitle(e.target.value)} placeholder="Meeting title" />
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <Label htmlFor="startTime">Start</Label>
                                <Input
                                    id="startTime"
                                    type="datetime-local"
                                    value={formStartTime ? DateTime.fromJSDate(formStartTime).setZone(effectiveTimezone).toFormat('yyyy-MM-dd\'T\'HH:mm') : ''}
                                    onChange={(e) => {
                                        const newStartTime = DateTime.fromFormat(e.target.value, 'yyyy-MM-dd\'T\'HH:mm', { zone: effectiveTimezone }).toJSDate();
                                        handleStartTimeChange(newStartTime);
                                    }}
                                    className="text-sm"
                                />
                                <div className="text-xs text-muted-foreground mt-1">
                                    {formStartTime ? DateTime.fromJSDate(formStartTime).setZone(effectiveTimezone).toFormat('EEE, MMM d h:mm a') : '—'}
                                </div>
                            </div>
                            <div>
                                <Label htmlFor="endTime">End</Label>
                                <Input
                                    id="endTime"
                                    type="datetime-local"
                                    value={formEndTime ? DateTime.fromJSDate(formEndTime).setZone(effectiveTimezone).toFormat('yyyy-MM-dd\'T\'HH:mm') : ''}
                                    onChange={(e) => {
                                        const newEndTime = DateTime.fromFormat(e.target.value, 'yyyy-MM-dd\'T\'HH:mm', { zone: effectiveTimezone }).toJSDate();
                                        handleEndTimeChange(newEndTime);
                                    }}
                                    className="text-sm"
                                />
                                <div className="text-xs text-muted-foreground mt-1">
                                    {formStartTime && formEndTime ?
                                        `Duration: ${Math.round((formEndTime.getTime() - formStartTime.getTime()) / (1000 * 60))} minutes` :
                                        '—'
                                    }
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch id="allDay" checked={formAllDay} onCheckedChange={setFormAllDay} />
                            <Label htmlFor="allDay">All day</Label>
                        </div>
                        <div>
                            <Label htmlFor="location">Location</Label>
                            <Input id="location" value={formLocation} onChange={(e) => setFormLocation(e.target.value)} placeholder="Location or conferencing" />
                        </div>
                        <div>
                            <Label htmlFor="attendees">Attendees</Label>
                            <div className="space-y-2">
                                <div className="relative">
                                    <Input
                                        id="attendees"
                                        value={attendeeQuery}
                                        onChange={(e) => setAttendeeQuery(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.preventDefault();
                                                if (attendeeQuery.trim() && attendeeQuery.includes('@')) {
                                                    addAttendee(attendeeQuery);
                                                }
                                            }
                                        }}
                                        onPaste={(e) => {
                                            const text = e.clipboardData.getData('text');
                                            const parsed = parseAttendeeFromText(text);
                                            if (parsed.length > 0) {
                                                e.preventDefault();
                                                parsed.forEach(person => addAttendee(person.email, person.name));
                                            }
                                        }}
                                        placeholder="Type email or paste multiple (e.g., First Last <email@domain.com>)"
                                        className="text-sm"
                                    />
                                </div>
                                {formAttendees.length > 0 && (
                                    <div className="space-y-1">
                                        {formAttendees.map((attendee) => (
                                            <div key={attendee.id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                                                <div className="flex-1 min-w-0">
                                                    {attendee.name && (
                                                        <div className="font-medium truncate">{attendee.name}</div>
                                                    )}
                                                    <div className="text-gray-600 truncate">{attendee.email}</div>
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeAttendee(attendee.id)}
                                                    className="ml-2 h-6 w-6 p-0 text-gray-400 hover:text-gray-600"
                                                >
                                                    ×
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div>
                            <Label htmlFor="description">Description</Label>
                            <Textarea id="description" value={formDescription} onChange={(e) => setFormDescription(e.target.value)} placeholder="Add details" />
                        </div>
                    </div>
                    <DialogFooter>
                        <div className="flex w-full justify-end gap-2">
                            <Button
                                variant="ghost"
                                onClick={() => {
                                    // Clear selection and close modal
                                    setIsCreateOpen(false);
                                    clearSelection();
                                }}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={async () => {
                                    if (!formStartTime || !formEndTime) return;
                                    const title = formTitle.trim() || 'New meeting';
                                    try {
                                        const startUtc = DateTime.fromJSDate(formStartTime).toUTC();
                                        const endUtc = DateTime.fromJSDate(formEndTime).toUTC();
                                        await gatewayClient.createCalendarEvent({
                                            title,
                                            description: formDescription || undefined,
                                            start_time: startUtc.toISO()!,
                                            end_time: endUtc.toISO()!,
                                            all_day: formAllDay || false,
                                            location: formLocation || undefined,
                                            attendees: formAttendees.length > 0 ? formAttendees.map(a => ({ email: a.email, name: a.name || undefined })) : undefined,
                                        });
                                        setIsCreateOpen(false);
                                        clearSelection();
                                        setFormTitle('');
                                        setFormDescription('');
                                        setFormLocation('');
                                        setFormAllDay(false);
                                        setFormStartTime(null);
                                        setFormEndTime(null);
                                        await (onRefresh ? onRefresh() : handleRefresh());
                                        toast({ description: 'Meeting created' });
                                    } catch (e) {
                                        toast({ description: e instanceof Error ? e.message : 'Failed to create meeting' });
                                    }
                                }}
                            >
                                Save
                            </Button>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
} 