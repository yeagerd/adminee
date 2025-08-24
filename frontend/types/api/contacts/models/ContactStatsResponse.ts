/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for contact statistics.
 */
export type ContactStatsResponse = {
    total_contacts: number;
    total_events: number;
    by_service: Record<string, any>;
    success?: boolean;
    message?: (string | null);
};

