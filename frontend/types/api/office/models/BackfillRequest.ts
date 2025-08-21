/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProviderEnum } from './ProviderEnum';
/**
 * Request to start a backfill job
 */
export type BackfillRequest = {
    /**
     * Email provider to backfill
     */
    provider: ProviderEnum;
    /**
     * Start date for email range
     */
    start_date?: (string | null);
    /**
     * End date for email range
     */
    end_date?: (string | null);
    /**
     * Specific folders to backfill
     */
    folders?: (Array<string> | null);
    /**
     * Batch size for processing
     */
    batch_size?: (number | null);
    /**
     * Emails per second limit
     */
    rate_limit?: (number | null);
    /**
     * Whether to include attachment metadata
     */
    include_attachments?: boolean;
    /**
     * Whether to include deleted emails
     */
    include_deleted?: boolean;
    /**
     * Maximum emails to process
     */
    max_emails?: (number | null);
    /**
     * User email (for internal endpoints)
     */
    user_id?: (string | null);
};

