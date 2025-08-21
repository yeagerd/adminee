/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Draft calendar change data structure.
 */
export type DraftCalendarChange = {
    id?: (string | null);
    type?: string;
    event_id?: (string | null);
    change_type?: (string | null);
    new_title?: (string | null);
    new_start_time?: (string | null);
    new_end_time?: (string | null);
    new_attendees?: (string | null);
    new_location?: (string | null);
    new_description?: (string | null);
    thread_id: string;
    created_at: string;
    updated_at?: (string | null);
};

