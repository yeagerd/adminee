/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
import type { Provider } from './Provider';
export type CalendarEvent = {
    id: string;
    calendar_id: string;
    title: string;
    description?: (string | null);
    start_time: string;
    end_time: string;
    all_day?: boolean;
    location?: (string | null);
    attendees?: Array<EmailAddress>;
    organizer?: (EmailAddress | null);
    status?: string;
    visibility?: string;
    provider: Provider;
    provider_event_id: string;
    account_email: string;
    account_name?: (string | null);
    calendar_name: string;
    created_at: string;
    updated_at: string;
};

