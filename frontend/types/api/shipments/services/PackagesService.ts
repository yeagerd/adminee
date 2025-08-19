/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataCollectionRequest } from '../models/DataCollectionRequest';
import type { DataCollectionResponse } from '../models/DataCollectionResponse';
import type { PackageCreate } from '../models/PackageCreate';
import type { PackageListResponse } from '../models/PackageListResponse';
import type { PackageOut } from '../models/PackageOut';
import type { PackageUpdate } from '../models/PackageUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PackagesService {
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
}
