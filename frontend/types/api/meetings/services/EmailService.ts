/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailResponseRequest } from '../models/EmailResponseRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EmailService {
    /**
     * Process Email Response
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static processEmailResponseApiV1MeetingsProcessEmailResponsePost(
        requestBody: EmailResponseRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/process-email-response/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
