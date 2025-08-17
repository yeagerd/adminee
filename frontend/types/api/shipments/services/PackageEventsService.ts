/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrackingEventCreate } from '../models/TrackingEventCreate';
import type { TrackingEventOut } from '../models/TrackingEventOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PackageEventsService {
    /**
     * Get Tracking Events
     * @param packageId
     * @returns TrackingEventOut Successful Response
     * @throws ApiError
     */
    public static getTrackingEventsV1ShipmentsPackagesPackageIdEventsGet(
        packageId: string,
    ): CancelablePromise<Array<TrackingEventOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/packages/{package_id}/events',
            path: {
                'package_id': packageId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Tracking Event
     * @param packageId
     * @param requestBody
     * @returns TrackingEventOut Successful Response
     * @throws ApiError
     */
    public static createTrackingEventV1ShipmentsPackagesPackageIdEventsPost(
        packageId: string,
        requestBody: TrackingEventCreate,
    ): CancelablePromise<TrackingEventOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages/{package_id}/events',
            path: {
                'package_id': packageId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Tracking Event
     * Delete a tracking event by ID
     *
     * Validates that the user owns the package associated with the tracking event
     * before allowing deletion.
     * @param packageId
     * @param eventId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteTrackingEventV1ShipmentsPackagesPackageIdEventsEventIdDelete(
        packageId: string,
        eventId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/shipments/packages/{package_id}/events/{event_id}',
            path: {
                'package_id': packageId,
                'event_id': eventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
