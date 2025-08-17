/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AvailableSlot } from './AvailableSlot';
/**
 * Response model for availability checks.
 */
export type AvailabilityResponse = {
    available_slots: Array<AvailableSlot>;
    total_slots: number;
    time_range: Record<string, string>;
    providers_used: Array<string>;
    provider_errors?: (Record<string, string> | null);
    request_metadata: Record<string, any>;
};

