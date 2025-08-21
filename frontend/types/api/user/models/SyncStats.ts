/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for synchronization statistics.
 */
export type SyncStats = {
    total_syncs?: number;
    successful_syncs?: number;
    failed_syncs?: number;
    last_successful_sync?: (string | null);
    last_failed_sync?: (string | null);
    average_sync_duration?: (number | null);
    sync_errors_by_type?: Record<string, number>;
};

