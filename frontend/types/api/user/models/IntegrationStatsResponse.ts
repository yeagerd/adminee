/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for integration statistics.
 */
export type IntegrationStatsResponse = {
    /**
     * Total integrations
     */
    total_integrations: number;
    /**
     * Active integrations
     */
    active_integrations: number;
    /**
     * Failed integrations
     */
    failed_integrations: number;
    /**
     * Pending integrations
     */
    pending_integrations: number;
    /**
     * Integration counts by provider
     */
    by_provider?: Record<string, number>;
    /**
     * Integration counts by status
     */
    by_status?: Record<string, number>;
    /**
     * Recent integration errors
     */
    recent_errors?: Array<Record<string, any>>;
    /**
     * Synchronization statistics
     */
    sync_stats?: Record<string, any>;
};

