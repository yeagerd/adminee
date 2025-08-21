/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BackfillRequest } from './BackfillRequest';
import type { BackfillStatusEnum } from './BackfillStatusEnum';
/**
 * Current status of a backfill job
 */
export type BackfillStatus = {
    /**
     * Unique identifier for the backfill job
     */
    job_id: string;
    /**
     * User who owns this job
     */
    user_id: string;
    /**
     * Current status of the job
     */
    status: BackfillStatusEnum;
    /**
     * When the job started
     */
    start_time: string;
    /**
     * When the job ended
     */
    end_time?: (string | null);
    /**
     * When the job was paused
     */
    pause_time?: (string | null);
    /**
     * When the job was resumed
     */
    resume_time?: (string | null);
    /**
     * Original backfill request
     */
    request: BackfillRequest;
    /**
     * Progress percentage
     */
    progress?: number;
    /**
     * Total emails to process
     */
    total_emails?: number;
    /**
     * Number of emails processed
     */
    processed_emails?: number;
    /**
     * Number of emails that failed
     */
    failed_emails?: number;
    /**
     * Error message if job failed
     */
    error_message?: (string | null);
};

