/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferencesResetRequest } from '../models/PreferencesResetRequest';
import type { UserPreferencesResponse } from '../models/UserPreferencesResponse';
import type { UserPreferencesUpdate } from '../models/UserPreferencesUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PreferencesService {
    /**
     * Get current user's preferences
     * Retrieve preferences for the authenticated user.
     * @returns UserPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static getMyPreferencesV1UsersMePreferencesGet(): CancelablePromise<UserPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me/preferences',
        });
    }
    /**
     * Update current user's preferences
     * Update preferences for the authenticated user.
     * @param requestBody
     * @returns UserPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static updateMyPreferencesV1UsersMePreferencesPut(
        requestBody: UserPreferencesUpdate,
    ): CancelablePromise<UserPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/users/me/preferences',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset current user's preferences
     * Reset preferences for the authenticated user.
     * @param requestBody
     * @returns UserPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static resetMyPreferencesV1UsersMePreferencesResetPost(
        requestBody: PreferencesResetRequest,
    ): CancelablePromise<UserPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/me/preferences/reset',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
