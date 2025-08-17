/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PollResponseTokenRequest } from '../models/PollResponseTokenRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicService {
    /**
     * Get Poll By Response Token
     * Get poll data for a specific response token.
     * @param responseToken
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPollByResponseTokenApiV1PublicPollsResponseResponseTokenGet(
        responseToken: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/polls/response/{response_token}',
            path: {
                'response_token': responseToken,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Respond With Token
     * @param responseToken
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static respondWithTokenApiV1PublicPollsResponseResponseTokenPut(
        responseToken: string,
        requestBody: PollResponseTokenRequest,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/public/polls/response/{response_token}',
            path: {
                'response_token': responseToken,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
