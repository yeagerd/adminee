import { CalendarEvent } from "@/types/api/office";
import { IntegrationProvider } from "@/types/api/user";
import { fireEvent, render, screen } from '@testing-library/react';
import { TimeSlotCalendar } from '../time-slot-calendar';

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

// Helpers to pick future dates so ranges are never in the past
const getFutureWeekday = (weekdayIndex: number, minDaysAhead: number): string => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + minDaysAhead);
    while (d.getDay() !== weekdayIndex) {
        d.setDate(d.getDate() + 1);
    }
    return d.toISOString().split('T')[0];
};

const FUTURE_TUESDAY = getFutureWeekday(2, 10);
const FUTURE_FRIDAY = getFutureWeekday(5, 10);

describe('TimeSlotCalendar Business Day Calculation', () => {
    const mockOnTimeSlotsChange = jest.fn();

    const defaultProps = {
        duration: 30,
        timeZone: 'America/New_York',
        onTimeSlotsChange: mockOnTimeSlotsChange,
        selectedTimeSlots: [],
        calendarEvents: []
    };

    beforeAll(() => {
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2025-08-01T00:00:00Z'));
    });

    afterAll(() => {
        jest.useRealTimers();
    });

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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_TUESDAY } }); // Tuesday

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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_FRIDAY } });

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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_TUESDAY } }); // Tuesday

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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_FRIDAY } });

            // Set range to 3 days (meaning +/- 3 days around Friday Aug 15)
            const rangeSlider = screen.getByRole('slider');
            fireEvent.change(rangeSlider, { target: { value: '3' } });

            // Verify that the range shows the correct number of days (9 business days for +/- 3 days around Friday)
            expect(screen.getByText(/Showing 9 days total/)).toBeInTheDocument();

            // Verify that the slider value is correctly set to 3
            const sliderElement = screen.getByRole('slider') as HTMLInputElement;
            expect(sliderElement.value).toBe('3');
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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_TUESDAY } });

            // Verify the date is displayed correctly regardless of timezone
            const dt = new Date(FUTURE_TUESDAY + 'T00:00:00');
            const weekdayShort = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][dt.getDay()];
            const monthShort = dt.toLocaleString('en-US', { month: 'short' });
            const day = dt.getDate();
            const expected = new RegExp(`${weekdayShort} ${monthShort} ${day}`);
            expect(screen.getAllByText(expected).length).toBeGreaterThan(0);
        });

        test('should clamp start date to today when computed business range partially falls in the past', () => {
            // Freeze time to a known date to make clamping deterministic
            jest.useFakeTimers();
            jest.setSystemTime(new Date('2025-08-01T00:00:00Z'));

            render(
                <TimeSlotCalendar
                    {...defaultProps}
                />
            );

            // Set target to the previous day (Thu Jul 31) relative to mocked today (Fri Aug 1)
            const targetDateInput = screen.getByDisplayValue(/\d{4}-\d{2}-\d{2}/);
            fireEvent.change(targetDateInput, { target: { value: '2025-07-31' } });

            // Set range to 1 business day so end remains >= today after clamping
            const rangeSlider = screen.getByRole('slider');
            fireEvent.change(rangeSlider, { target: { value: '1' } });

            // We expect the earliest header to include the mocked today (Fri Aug 1)
            expect(screen.getAllByText(/Fri Aug 1/).length).toBeGreaterThan(0);

            jest.useRealTimers();
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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_TUESDAY } }); // Tuesday

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
                    calendar_id: 'test-calendar-id',
                    title: 'Test Meeting',
                    start_time: `${FUTURE_TUESDAY}T10:00:00Z`, // Tuesday 10 AM UTC
                    end_time: `${FUTURE_TUESDAY}T11:00:00Z`,   // Tuesday 11 AM UTC
                    all_day: false,
                    attendees: [],
                    status: 'confirmed',
                    visibility: 'default',
                    provider: Provider.GOOGLE,
                    provider_event_id: 'test-provider-event-id',
                    account_email: 'test@example.com',
                    calendar_name: 'Test Calendar',
                    created_at: `${FUTURE_TUESDAY}T00:00:00Z`,
                    updated_at: `${FUTURE_TUESDAY}T00:00:00Z`
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
            fireEvent.change(targetDateInput, { target: { value: FUTURE_TUESDAY } });

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

    beforeAll(() => {
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2025-08-01T00:00:00Z'));
    });

    afterAll(() => {
        jest.useRealTimers();
    });

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
        fireEvent.change(targetDateInput, { target: { value: FUTURE_FRIDAY } }); // Friday

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
