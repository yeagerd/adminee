/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
/**
 * Request model for creating calendar events.
 */
export type CreateCalendarEventRequest = {
    /**
     * Event title
     */
    title: string;
    /**
     * Event description
     */
    description?: (string | null);
    /**
     * Event start time
     */
    start_time: string;
    /**
     * Event end time
     */
    end_time: string;
    /**
     * Whether this is an all-day event
     */
    all_day?: boolean;
    /**
     * Event location
     */
    location?: (string | null);
    /**
     * List of attendees
     */
    attendees?: (Array<EmailAddress> | null);
    /**
     * Calendar ID (uses primary if not specified)
     */
    calendar_id?: (string | null);
    /**
     * Provider preference (google, microsoft)
     */
    provider?: (string | null);
    /**
     * Event visibility (default, public, private)
     */
    visibility?: (string | null);
    /**
     * Event status (confirmed, tentative, cancelled)
     */
    status?: (string | null);
};

