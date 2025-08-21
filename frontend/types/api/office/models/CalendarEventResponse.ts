/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CalendarEvent } from './CalendarEvent';
/**
 * Response model for calendar event operations.
 */
export type CalendarEventResponse = {
    event_id?: (string | null);
    provider: string;
    status: string;
    created_at?: (string | null);
    updated_at?: (string | null);
    deleted_at?: (string | null);
    event_data?: (CalendarEvent | null);
    request_metadata: Record<string, any>;
};

