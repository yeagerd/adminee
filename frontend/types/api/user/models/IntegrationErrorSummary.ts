/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for integration error summary.
 */
export type IntegrationErrorSummary = {
    integration_id: number;
    provider: string;
    error_type: string;
    error_message: string;
    occurred_at: string;
    retry_count?: number;
};

