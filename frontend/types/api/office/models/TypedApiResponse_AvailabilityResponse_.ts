/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AvailabilityResponse } from './AvailabilityResponse';
import type { Provider } from './Provider';
export type TypedApiResponse_AvailabilityResponse_ = {
    success: boolean;
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
    data?: (AvailabilityResponse | null);
};

