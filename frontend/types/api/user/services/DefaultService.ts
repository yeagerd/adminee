/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Oauth Callback Redirect
     * Global OAuth callback endpoint that handles provider redirects.
     *
     * This endpoint receives OAuth callbacks from providers and processes them
     * directly using the integration service.
     *
     * The state parameter contains information about the user and provider
     * that allows us to route the callback correctly.
     * @param code
     * @param state
     * @param error
     * @param errorDescription
     * @returns any Successful Response
     * @throws ApiError
     */
    public static oauthCallbackRedirectOauthCallbackGet(
        code?: (string | null),
        state?: (string | null),
        error?: (string | null),
        errorDescription?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/oauth/callback',
            query: {
                'code': code,
                'state': state,
                'error': error,
                'error_description': errorDescription,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
