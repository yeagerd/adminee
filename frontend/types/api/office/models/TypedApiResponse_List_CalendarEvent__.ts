/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CalendarEvent } from './CalendarEvent';
import type { Provider } from './Provider';
export type TypedApiResponse_List_CalendarEvent__ = {
    success: boolean;
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
    data?: (Array<CalendarEvent> | null);
};

