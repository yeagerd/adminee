/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LabelCreate } from '../models/LabelCreate';
import type { LabelOut } from '../models/LabelOut';
import type { LabelUpdate } from '../models/LabelUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LabelsService {
    /**
     * List Labels
     * List all labels for the authenticated user.
     *
     * **Authentication:**
     * - Requires user authentication (JWT token or gateway headers)
     * - Returns only labels owned by the authenticated user
     * - Requires service API key for service-to-service calls
     * @returns LabelOut Successful Response
     * @throws ApiError
     */
    public static listLabelsV1ShipmentsLabelsGet(): CancelablePromise<Array<LabelOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/labels/',
        });
    }
    /**
     * Create Label
     * Create a new label for the authenticated user.
     *
     * **Authentication:**
     * - Requires user authentication (JWT token or gateway headers)
     * - User ownership is automatically derived from authenticated user context
     * - Requires service API key for service-to-service calls
     * @param requestBody
     * @returns LabelOut Successful Response
     * @throws ApiError
     */
    public static createLabelV1ShipmentsLabelsPost(
        requestBody: LabelCreate,
    ): CancelablePromise<LabelOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/labels/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Label
     * @param id
     * @param requestBody
     * @returns LabelOut Successful Response
     * @throws ApiError
     */
    public static updateLabelV1ShipmentsLabelsIdPut(
        id: string,
        requestBody: LabelUpdate,
    ): CancelablePromise<LabelOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/shipments/labels/{id}',
            path: {
                'id': id,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Label
     * @param id
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteLabelV1ShipmentsLabelsIdDelete(
        id: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/shipments/labels/{id}',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
