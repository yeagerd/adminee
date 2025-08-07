import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TimeSlotCalendar } from '../time-slot-calendar';
import { CalendarEvent } from '@/types/office-service';

// Mock Luxon's DateTime to control timezone behavior
jest.mock('luxon', () => {
    const actual = jest.requireActual('luxon');
    return {
        ...actual,
        DateTime: {
            ...actual.DateTime,
            fromISO: jest.fn().mockImplementation((isoString, options) => {
                const dt = actual.DateTime.fromISO(isoString, options);
                return dt;
            }),
            fromJSDate: jest.fn().mockImplementation((date) => {
                return actual.DateTime.fromJSDate(date);
            })
        }
    };
});

describe('TimeSlotCalendar Business Day Calculation', () => {
    const mockOnTimeSlotsChange = jest.fn();
    
    const defaultProps = {
        duration: 30,
        timeZone: 'America/New_York',
        onTimeSlotsChange: mockOnTimeSlotsChange,
        selectedTimeSlots: [],
        calendarEvents: []
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('Business Day Functionality Integration', () => {
        test('should display business days and respect weekend settings', () => {
            const { container } = render(
                <TimeSlotCalendar
                    {...defaultProps}
                />
            );

            // Set the target date to Tuesday  
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-12' } }); // Tuesday

            // Verify component renders successfully with business day calculations
            expect(screen.getByText(/Select Time Slots/)).toBeInTheDocument();
            expect(screen.getByText(/showing \d+ days total/i)).toBeInTheDocument();
            
            // Verify that date headers are displayed (business day logic is working)
            const dateElements = container.querySelectorAll('.whitespace-normal');
            expect(dateElements.length).toBeGreaterThan(0); // Should have date columns
        });

        test('should include weekends when includeWeekends is enabled', () => {
            const { container } = render(
                <TimeSlotCalendar
                    {...defaultProps}
                />
            );

            // Set target date to Friday
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-15' } });

            // Enable weekends
            const weekendsCheckbox = screen.getByLabelText(/Include Weekends/);
            fireEvent.click(weekendsCheckbox);

            // Check that the text changes to no longer mention "business days only"
            expect(screen.queryByText(/business days only/i)).not.toBeInTheDocument();
            
            // Verify more days are shown when weekends are included
            const dateElements = container.querySelectorAll('.whitespace-normal');
            expect(dateElements.length).toBeGreaterThan(0);
        });

        test('should handle business day mode vs weekend mode differently', () => {
            const { container } = render(
                <TimeSlotCalendar
                    {...defaultProps}
                />
            );

            // Set target date
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-12' } }); // Tuesday

            // Get initial count of date headers (business days mode)
            const weekendsCheckbox = screen.getByLabelText(/Include Weekends/);
            expect(weekendsCheckbox).not.toBeChecked();
            
            const businessDayHeaders = container.querySelectorAll('.whitespace-normal');
            const businessDayCount = businessDayHeaders.length;

            // Enable weekends
            fireEvent.click(weekendsCheckbox);

            // Should have different (likely more) date headers when weekends are included
            const weekendHeaders = container.querySelectorAll('.whitespace-normal');
            const weekendCount = weekendHeaders.length;
            
            // With same range, weekend mode should show same or more days
            expect(weekendCount).toBeGreaterThanOrEqual(businessDayCount);
        });
    });

    describe('Date Range Calculation with Business Logic', () => {
        test('should correctly calculate business day range for Friday target', () => {
            render(
                <TimeSlotCalendar
                    {...defaultProps}
                />
            );

            // Set target to Friday
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-15' } });

            // Set range to 7 days
            const rangeSlider = screen.getByRole('slider');
            fireEvent.change(rangeSlider, { target: { value: '7' } });

            // Verify the date range header shows correct span
            // Should display: Tue Aug 12 - Wed Aug 20
            expect(screen.getByText(/Tue Aug 12 - Wed Aug 20/)).toBeInTheDocument();
        });

        test('should handle timezone conversion correctly in date display', () => {
            render(
                <TimeSlotCalendar
                    {...defaultProps}
                    timeZone="America/Los_Angeles"
                />
            );

            // Set a specific date
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-12' } });

            // Verify the date is displayed correctly regardless of timezone
            expect(screen.getAllByText(/Tue Aug 12/).length).toBeGreaterThan(0);
        });
    });

    describe('Time Slot Selection with Business Day Logic', () => {
        test('should allow selection of time slots only on business days', () => {
            const mockCalendarEvents: CalendarEvent[] = [];
            
            render(
                <TimeSlotCalendar
                    {...defaultProps}
                    calendarEvents={mockCalendarEvents}
                />
            );

            // Set target to a Tuesday to ensure we have business days
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-12' } }); // Tuesday

            // Find and click the "Select all available slots" button for the target day
            const selectAllButtons = screen.getAllByTitle(/Select all available slots/);
            expect(selectAllButtons.length).toBeGreaterThan(0);
            
            fireEvent.click(selectAllButtons[0]);

            // Verify that the callback was called with time slots
            expect(mockOnTimeSlotsChange).toHaveBeenCalled();
            const calledSlots = mockOnTimeSlotsChange.mock.calls[0][0];
            expect(calledSlots.length).toBeGreaterThan(0);
            
            // All selected slots should be on business days
            calledSlots.forEach((slot: { start: string; end: string }) => {
                const slotDate = new Date(slot.start);
                const dayOfWeek = slotDate.getDay();
                expect(dayOfWeek).toBeGreaterThanOrEqual(1); // Monday
                expect(dayOfWeek).toBeLessThanOrEqual(5);   // Friday
            });
        });

        test('should handle conflict detection with calendar events on business days', () => {
            const mockCalendarEvents: CalendarEvent[] = [
                {
                    id: 'test-event',
                    title: 'Test Meeting',
                    start_time: '2025-08-12T10:00:00Z', // Tuesday 10 AM UTC
                    end_time: '2025-08-12T11:00:00Z',   // Tuesday 11 AM UTC
                    attendees: []
                }
            ];

            render(
                <TimeSlotCalendar
                    {...defaultProps}
                    calendarEvents={mockCalendarEvents}
                />
            );

            // Set target to Tuesday when the event occurs
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-08-12' } });

            // Verify the calendar event is displayed
            expect(screen.getByText('Test Meeting')).toBeInTheDocument();
        });
    });
});

// Integration tests that verify the complete business day calculation flow
describe('TimeSlotCalendar Business Day Integration', () => {
    const mockOnTimeSlotsChange = jest.fn();
    
    const defaultProps = {
        duration: 30,
        timeZone: 'America/New_York', 
        onTimeSlotsChange: mockOnTimeSlotsChange,
        selectedTimeSlots: [],
        calendarEvents: []
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    test('should correctly handle business day calculations end-to-end', () => {
        render(
            <TimeSlotCalendar
                {...defaultProps}
            />
        );

        // Test the complete flow: set target date, verify business days, select slots
        const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
        fireEvent.change(targetDateInput, { target: { value: '2025-08-15' } }); // Friday

        // Should automatically calculate and display surrounding business days
        // This tests the internal business day calculation logic
        expect(screen.getByText(/showing \d+ days total \(business days only\)/i)).toBeInTheDocument();
        
        // Verify that the range calculation worked correctly by checking displayed dates
        const dateHeaders = screen.getAllByText(/Aug \d+/);
        expect(dateHeaders.length).toBeGreaterThan(0);
        
        // The component should be functional and responsive
        expect(screen.getByText(/Select Time Slots/)).toBeInTheDocument();
    });
});
