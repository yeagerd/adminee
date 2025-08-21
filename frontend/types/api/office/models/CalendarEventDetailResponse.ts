/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Provider } from './Provider';
/**
 * Response model for calendar event detail operations.
 */
export type CalendarEventDetailResponse = {
    success: boolean;
    data?: (Record<string, any> | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

