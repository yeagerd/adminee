/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationErrorSummary } from './IntegrationErrorSummary';
import type { SyncStats } from './SyncStats';
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
    recent_errors?: Array<IntegrationErrorSummary>;
    /**
     * Synchronization statistics
     */
    sync_stats?: SyncStats;
};

