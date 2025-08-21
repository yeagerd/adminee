/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Draft calendar event data structure.
 */
export type DraftCalendarEvent = {
    id?: (string | null);
    type?: string;
    title?: (string | null);
    start_time?: (string | null);
    end_time?: (string | null);
    attendees?: (string | null);
    location?: (string | null);
    description?: (string | null);
    thread_id: string;
    created_at: string;
    updated_at?: (string | null);
};

