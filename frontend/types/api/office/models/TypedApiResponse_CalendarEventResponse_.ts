/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CalendarEventResponse } from './CalendarEventResponse';
import type { Provider } from './Provider';
export type TypedApiResponse_CalendarEventResponse_ = {
    success: boolean;
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
    data?: (CalendarEventResponse | null);
};

