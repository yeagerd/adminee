'use client';

import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { DateTime } from 'luxon';
import { useCallback, useEffect, useState } from 'react';

interface DateTimeRangePickerProps {
    startTime: Date | null;
    endTime: Date | null;
    onStartTimeChange: (time: Date) => void;
    onEndTimeChange: (time: Date) => void;
    effectiveTimezone: string;
    className?: string;
}

export function DateTimeRangePicker({
    startTime,
    endTime,
    onStartTimeChange,
    onEndTimeChange,
    effectiveTimezone,
    className = ''
}: DateTimeRangePickerProps) {
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [showStartTimePicker, setShowStartTimePicker] = useState(false);
    const [showEndTimePicker, setShowEndTimePicker] = useState(false);

    // Helper function to create a time in the effective timezone
    const createTimeInTimezone = useCallback((date: Date, hour: number, minute: number): Date => {
        const dateTime = DateTime.fromJSDate(date).setZone(effectiveTimezone);
        const timeInZone = dateTime.set({ hour, minute, second: 0, millisecond: 0 });
        return timeInZone.toJSDate();
    }, [effectiveTimezone]);

    // Helper function to preserve time while changing date in effective timezone
    const preserveTimeChangeDate = useCallback((originalTime: Date, newDate: Date): Date => {
        const originalDateTime = DateTime.fromJSDate(originalTime).setZone(effectiveTimezone);
        const newDateTime = DateTime.fromJSDate(newDate).setZone(effectiveTimezone);

        return newDateTime.set({
            hour: originalDateTime.hour,
            minute: originalDateTime.minute,
            second: 0,
            millisecond: 0
        }).toJSDate();
    }, [effectiveTimezone]);

    // Generate start time options in effective timezone
    const startTimeOptions = useMemo(() => {
        const options = [];
        // Use the selected date if available, otherwise use today
        const baseDate = startTime ? new Date(startTime) : new Date();
        for (let hour = 0; hour < 24; hour++) {
            for (let minute = 0; minute < 60; minute += 15) {
                const time = createTimeInTimezone(baseDate, hour, minute);
                options.push(time);
            }
        }
        return options;
    }, [startTime, createTimeInTimezone]);

    const generateTimeOptions = useCallback((startTime: Date, maxDurationHours: number = 23.5) => {
        const options: Array<{ time: Date; label: string; duration: string }> = [];
        const startDateTime = DateTime.fromJSDate(startTime).setZone(effectiveTimezone);

        // Generate options in 15-minute increments
        for (let hour = 0; hour <= maxDurationHours; hour++) {
            for (let minute = 0; minute < 60; minute += 15) {
                const time = startDateTime.plus({ hours: hour, minutes: minute }).toJSDate();
                const durationMs = time.getTime() - startTime.getTime();
                const durationHours = Math.floor(durationMs / (1000 * 60 * 60));
                const durationMinutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));

                let durationLabel = '';
                if (durationHours === 0) {
                    durationLabel = `${durationMinutes} mins`;
                } else if (durationMinutes === 0) {
                    durationLabel = `${durationHours} hr${durationHours > 1 ? 's' : ''}`;
                } else {
                    durationLabel = `${durationHours} hr${durationHours > 1 ? 's' : ''} ${durationMinutes} mins`;
                }

                options.push({
                    time,
                    label: DateTime.fromJSDate(time).setZone(effectiveTimezone).toFormat('h:mm a'),
                    duration: durationLabel
                });
            }
        }

        return options;
    }, [effectiveTimezone]);

    const handleDateSelect = useCallback((date: Date) => {
        if (startTime) {
            // Keep the time, change the date using effective timezone
            const newStartTime = preserveTimeChangeDate(startTime, date);
            onStartTimeChange(newStartTime);

            if (endTime) {
                const duration = endTime.getTime() - startTime.getTime();
                const newEndTime = new Date(newStartTime.getTime() + duration);
                onEndTimeChange(newEndTime);
            }
        } else {
            // Set both start and end time to 9 AM and 10 AM on selected date in effective timezone
            const newStartTime = createTimeInTimezone(date, 9, 0);
            onStartTimeChange(newStartTime);

            const newEndTime = createTimeInTimezone(date, 10, 0);
            onEndTimeChange(newEndTime);
        }
        setShowDatePicker(false);
    }, [startTime, endTime, onStartTimeChange, onEndTimeChange, preserveTimeChangeDate, createTimeInTimezone]);

    const handleStartTimeSelect = useCallback((time: Date) => {
        // Preserve the date from startTime, only update the time using effective timezone
        let newStartTime: Date;
        if (startTime) {
            newStartTime = preserveTimeChangeDate(time, startTime);
        } else {
            newStartTime = time;
        }

        onStartTimeChange(newStartTime);
        setShowStartTimePicker(false);

        // Adjust end time to maintain duration
        if (endTime) {
            const duration = endTime.getTime() - startTime!.getTime();
            const newEndTime = new Date(newStartTime.getTime() + duration);
            onEndTimeChange(newEndTime);
        } else {
            // Set default 1-hour duration
            const newEndTime = new Date(newStartTime.getTime() + 60 * 60 * 1000);
            onEndTimeChange(newEndTime);
        }
    }, [startTime, endTime, onStartTimeChange, onEndTimeChange, preserveTimeChangeDate]);

    const handleEndTimeSelect = useCallback((time: Date) => {
        // Preserve the date from endTime, only update the time using effective timezone
        let newEndTime: Date;
        if (endTime) {
            newEndTime = preserveTimeChangeDate(time, endTime);
        } else {
            newEndTime = time;
        }

        onEndTimeChange(newEndTime);
        setShowEndTimePicker(false);
    }, [endTime, onEndTimeChange, preserveTimeChangeDate]);

    // Close pickers when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('[data-picker]')) {
                setShowDatePicker(false);
                setShowStartTimePicker(false);
                setShowEndTimePicker(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className={`space-y-3 ${className}`}>
            <Label>Date & Time</Label>
            <div className="grid grid-cols-3 gap-2 mt-2">
                {/* Date Picker */}
                <div className="relative">
                    <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                        onClick={() => setShowDatePicker(!showDatePicker)}
                    >
                        {startTime ?
                            DateTime.fromJSDate(startTime).setZone(effectiveTimezone).toFormat('EEE, MMM d') :
                            'Select date'
                        }
                    </Button>
                    {showDatePicker && (
                        <div className="absolute z-50 mt-1 bg-white border rounded-lg shadow-lg p-3 min-w-[280px]" data-picker>
                            <div className="grid grid-cols-7 gap-1 text-xs text-center mb-2">
                                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, index) => (
                                    <div key={index} className="p-1 font-medium text-gray-500">{day}</div>
                                ))}
                            </div>
                            <div className="grid grid-cols-7 gap-1">
                                {(() => {
                                    const today = new Date();
                                    const currentMonth = startTime ? new Date(startTime.getFullYear(), startTime.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth(), 1);
                                    const firstDay = new Date(currentMonth);
                                    const startDate = new Date(firstDay);
                                    startDate.setDate(startDate.getDate() - firstDay.getDay());

                                    const dates = [];
                                    for (let i = 0; i < 42; i++) {
                                        const date = new Date(startDate);
                                        date.setDate(startDate.getDate() + i);
                                        dates.push(date);
                                    }

                                    return dates.map((date, index) => {
                                        const isCurrentMonth = date.getMonth() === currentMonth.getMonth();
                                        const isToday = date.toDateString() === today.toDateString();
                                        const isSelected = startTime && date.toDateString() === startTime.toDateString();

                                        return (
                                            <button
                                                key={index}
                                                type="button"
                                                className={`p-2 text-xs rounded hover:bg-gray-100 ${isCurrentMonth ? 'text-gray-900' : 'text-gray-400'
                                                    } ${isToday ? 'bg-blue-100 text-blue-600 font-medium' : ''
                                                    } ${isSelected ? 'bg-blue-600 text-white' : ''
                                                    }`}
                                                onClick={() => handleDateSelect(date)}
                                            >
                                                {date.getDate()}
                                            </button>
                                        );
                                    });
                                })()}
                            </div>
                        </div>
                    )}
                </div>

                {/* Start Time Picker */}
                <div className="relative">
                    <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                        onClick={() => setShowStartTimePicker(!showStartTimePicker)}
                    >
                        {startTime ?
                            DateTime.fromJSDate(startTime).setZone(effectiveTimezone).toFormat('h:mm a') :
                            'Start time'
                        }
                    </Button>
                    {showStartTimePicker && (
                        <div className="absolute z-50 mt-1 bg-white border rounded-lg shadow-lg p-1 min-w-[120px] max-h-60 overflow-y-auto" data-picker>
                            {startTimeOptions.map((time, index) => (
                                <button
                                    key={index}
                                    type="button"
                                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
                                    onClick={() => handleStartTimeSelect(time)}
                                >
                                    {DateTime.fromJSDate(time).setZone(effectiveTimezone).toFormat('h:mm a')}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* End Time Picker */}
                <div className="relative">
                    <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                        onClick={() => setShowEndTimePicker(!showEndTimePicker)}
                    >
                        {endTime ?
                            DateTime.fromJSDate(endTime).setZone(effectiveTimezone).toFormat('h:mm a') :
                            'End time'
                        }
                    </Button>
                    {showEndTimePicker && startTime && (
                        <div className="absolute z-50 mt-1 bg-white border rounded-lg shadow-lg p-1 min-w-[140px] max-h-60 overflow-y-auto" data-picker>
                            {generateTimeOptions(startTime).map((option, index) => (
                                <button
                                    key={index}
                                    type="button"
                                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
                                    onClick={() => handleEndTimeSelect(option.time)}
                                >
                                    <div className="flex justify-between items-center">
                                        <span>{option.label}</span>
                                        <span className="text-xs text-gray-500 ml-2">({option.duration})</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            <div className="text-xs text-muted-foreground mt-2">
                {startTime && endTime ?
                    `${DateTime.fromJSDate(startTime).setZone(effectiveTimezone).toFormat('EEE, MMM d h:mm a')} - ${DateTime.fromJSDate(endTime).setZone(effectiveTimezone).toFormat('h:mm a')} (${Math.round((endTime.getTime() - startTime.getTime()) / (1000 * 60))} minutes)` :
                    '—'
                }
            </div>
        </div>
    );
}
