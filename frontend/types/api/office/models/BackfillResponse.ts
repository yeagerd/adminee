/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BackfillStatusEnum } from './BackfillStatusEnum';
/**
 * Response from starting a backfill job
 */
export type BackfillResponse = {
    /**
     * Unique identifier for the backfill job
     */
    job_id: string;
    /**
     * Status of the job
     */
    status: BackfillStatusEnum;
    /**
     * Human-readable message
     */
    message: string;
};

