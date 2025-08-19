/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CarrierConfigOut } from '../models/CarrierConfigOut';
import type { DataCollectionRequest } from '../models/DataCollectionRequest';
import type { DataCollectionResponse } from '../models/DataCollectionResponse';
import type { EmailParseRequest } from '../models/EmailParseRequest';
import type { EmailParseResponse } from '../models/EmailParseResponse';
import type { LabelCreate } from '../models/LabelCreate';
import type { LabelOut } from '../models/LabelOut';
import type { LabelUpdate } from '../models/LabelUpdate';
import type { PackageCreate } from '../models/PackageCreate';
import type { PackageListResponse } from '../models/PackageListResponse';
import type { PackageOut } from '../models/PackageOut';
import type { PackageUpdate } from '../models/PackageUpdate';
import type { TrackingEventCreate } from '../models/TrackingEventCreate';
import type { TrackingEventOut } from '../models/TrackingEventOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ShipmentsService {
    /**
     * List Packages
     * List packages with cursor-based pagination.
     *
     * This endpoint uses cursor-based pagination instead of offset-based pagination
     * for better performance and consistency with concurrent updates.
     * @param cursor
     * @param limit
     * @param direction
     * @param carrier
     * @param status
     * @param userId
     * @param trackingNumber
     * @param emailMessageId
     * @param dateRange
     * @returns PackageListResponse Successful Response
     * @throws ApiError
     */
    public static listPackagesV1ShipmentsPackagesGet(
        cursor?: (string | null),
        limit?: (number | null),
        direction?: (string | null),
        carrier?: (string | null),
        status?: (string | null),
        userId?: (string | null),
        trackingNumber?: (string | null),
        emailMessageId?: (string | null),
        dateRange?: (string | null),
    ): CancelablePromise<PackageListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/packages/',
            query: {
                'cursor': cursor,
                'limit': limit,
                'direction': direction,
                'carrier': carrier,
                'status': status,
                'user_id': userId,
                'tracking_number': trackingNumber,
                'email_message_id': emailMessageId,
                'date_range': dateRange,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Package
     * @param requestBody
     * @returns PackageOut Successful Response
     * @throws ApiError
     */
    public static addPackageV1ShipmentsPackagesPost(
        requestBody: PackageCreate,
    ): CancelablePromise<PackageOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Packages
     * List packages with cursor-based pagination.
     *
     * This endpoint uses cursor-based pagination instead of offset-based pagination
     * for better performance and consistency with concurrent updates.
     * @param cursor
     * @param limit
     * @param direction
     * @param carrier
     * @param status
     * @param userId
     * @param trackingNumber
     * @param emailMessageId
     * @param dateRange
     * @returns PackageListResponse Successful Response
     * @throws ApiError
     */
    public static listPackagesV1ShipmentsPackagesGet1(
        cursor?: (string | null),
        limit?: (number | null),
        direction?: (string | null),
        carrier?: (string | null),
        status?: (string | null),
        userId?: (string | null),
        trackingNumber?: (string | null),
        emailMessageId?: (string | null),
        dateRange?: (string | null),
    ): CancelablePromise<PackageListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/packages',
            query: {
                'cursor': cursor,
                'limit': limit,
                'direction': direction,
                'carrier': carrier,
                'status': status,
                'user_id': userId,
                'tracking_number': trackingNumber,
                'email_message_id': emailMessageId,
                'date_range': dateRange,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Package
     * @param requestBody
     * @returns PackageOut Successful Response
     * @throws ApiError
     */
    public static addPackageV1ShipmentsPackagesPost1(
        requestBody: PackageCreate,
    ): CancelablePromise<PackageOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Package
     * @param id
     * @returns PackageOut Successful Response
     * @throws ApiError
     */
    public static getPackageV1ShipmentsPackagesIdGet(
        id: string,
    ): CancelablePromise<PackageOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/packages/{id}',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Package
     * @param id
     * @param requestBody
     * @returns PackageOut Successful Response
     * @throws ApiError
     */
    public static updatePackageV1ShipmentsPackagesIdPut(
        id: string,
        requestBody: PackageUpdate,
    ): CancelablePromise<PackageOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/shipments/packages/{id}',
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
     * Delete Package
     * @param id
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deletePackageV1ShipmentsPackagesIdDelete(
        id: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/shipments/packages/{id}',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh Package
     * @param id
     * @returns any Successful Response
     * @throws ApiError
     */
    public static refreshPackageV1ShipmentsPackagesIdRefreshPost(
        id: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages/{id}/refresh',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Label To Package
     * @param id
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addLabelToPackageV1ShipmentsPackagesIdLabelsPost(
        id: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages/{id}/labels',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Remove Label From Package
     * @param id
     * @param labelId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static removeLabelFromPackageV1ShipmentsPackagesIdLabelsLabelIdDelete(
        id: string,
        labelId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/shipments/packages/{id}/labels/{label_id}',
            path: {
                'id': id,
                'label_id': labelId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Collect Shipment Data
     * Collect user-corrected shipment data for service improvements
     *
     * This endpoint stores:
     * - Original email content
     * - Auto-detected shipment information
     * - User corrections and improvements
     * - Detection confidence scores
     *
     * This data is used to improve the accuracy of future shipment detection.
     * @param requestBody
     * @returns DataCollectionResponse Successful Response
     * @throws ApiError
     */
    public static collectShipmentDataV1ShipmentsPackagesCollectDataPost(
        requestBody: DataCollectionRequest,
    ): CancelablePromise<DataCollectionResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/packages/collect-data',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Collection Stats
     * Get statistics about data collection (for admin/monitoring purposes)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCollectionStatsV1ShipmentsPackagesCollectionStatsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/packages/collection-stats',
        });
    }
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
    /**
     * List Carriers
     * List carrier configurations.
     *
     * **Authentication:**
     * - Requires user authentication (JWT token or gateway headers)
     * - Requires service API key for service-to-service calls
     * - Note: Carrier configs are typically system-wide, not user-specific
     * @returns CarrierConfigOut Successful Response
     * @throws ApiError
     */
    public static listCarriersV1ShipmentsCarriersGet(): CancelablePromise<Array<CarrierConfigOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/carriers/',
        });
    }
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
    /**
     * Get Events By Email
     * Get tracking events by email message ID
     *
     * This endpoint allows the frontend to check if an email has associated shipment events
     * and display the appropriate UI indicators (e.g., green-filled shipping truck icon).
     * @param emailMessageId Email message ID to search for
     * @returns TrackingEventOut Successful Response
     * @throws ApiError
     */
    public static getEventsByEmailV1ShipmentsEventsGet(
        emailMessageId: string,
    ): CancelablePromise<Array<TrackingEventOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/events',
            query: {
                'email_message_id': emailMessageId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Parse Email From Event
     * Parse email content to detect shipment information and create events
     *
     * This endpoint analyzes email content to identify shipment information
     * and can optionally create tracking events from the parsed data.
     * @param requestBody
     * @returns EmailParseResponse Successful Response
     * @throws ApiError
     */
    public static parseEmailFromEventV1ShipmentsEventsFromEmailPost(
        requestBody: EmailParseRequest,
    ): CancelablePromise<EmailParseResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/shipments/events/from-email',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
