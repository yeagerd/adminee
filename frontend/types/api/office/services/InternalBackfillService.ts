/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BackfillRequest } from '../models/BackfillRequest';
import type { BackfillResponse } from '../models/BackfillResponse';
import type { BackfillStatus } from '../models/BackfillStatus';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InternalBackfillService {
    /**
     * Start Internal Backfill
     * Internal endpoint for starting backfill jobs (service-to-service)
     * @param userId User email address
     * @param requestBody
     * @returns BackfillResponse Successful Response
     * @throws ApiError
     */
    public static startInternalBackfillInternalBackfillStartPost(
        userId: string,
        requestBody: BackfillRequest,
    ): CancelablePromise<BackfillResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/backfill/start',
            query: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Internal Backfill Status
     * Internal endpoint for getting backfill job status
     * @param jobId
     * @param userId User email address
     * @returns BackfillStatus Successful Response
     * @throws ApiError
     */
    public static getInternalBackfillStatusInternalBackfillStatusJobIdGet(
        jobId: string,
        userId: string,
    ): CancelablePromise<BackfillStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/backfill/status/{job_id}',
            path: {
                'job_id': jobId,
            },
            query: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Internal Backfill Jobs
     * Internal endpoint for listing backfill jobs for a user
     * @param userId User email address
     * @returns BackfillStatus Successful Response
     * @throws ApiError
     */
    public static listInternalBackfillJobsInternalBackfillStatusGet(
        userId: string,
    ): CancelablePromise<Array<BackfillStatus>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/backfill/status',
            query: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel Internal Backfill Job
     * Internal endpoint for cancelling a backfill job
     * @param jobId
     * @param userId User email address
     * @returns string Successful Response
     * @throws ApiError
     */
    public static cancelInternalBackfillJobInternalBackfillJobIdDelete(
        jobId: string,
        userId: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/backfill/{job_id}',
            path: {
                'job_id': jobId,
            },
            query: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
