/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AvailabilityDataResponse } from '../models/AvailabilityDataResponse';
import type { CreatePublicBookingRequest } from '../models/CreatePublicBookingRequest';
import type { PublicLinkDataResponse } from '../models/PublicLinkDataResponse';
import type { SuccessResponse } from '../models/SuccessResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class BookingsService {
    /**
     * Health Check
     * @returns string Successful Response
     * @throws ApiError
     */
    public static healthCheckApiV1BookingsHealthGet(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/health',
        });
    }
    /**
     * Get Public Link
     * Get public link metadata including template questions
     * @param token
     * @returns PublicLinkDataResponse Successful Response
     * @throws ApiError
     */
    public static getPublicLinkApiV1BookingsPublicTokenGet(
        token: string,
    ): CancelablePromise<PublicLinkDataResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/public/{token}',
            path: {
                'token': token,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Public Availability
     * Get available time slots for a public link
     * @param token
     * @param duration
     * @returns AvailabilityDataResponse Successful Response
     * @throws ApiError
     */
    public static getPublicAvailabilityApiV1BookingsPublicTokenAvailabilityGet(
        token: string,
        duration: number = 30,
    ): CancelablePromise<AvailabilityDataResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/public/{token}/availability',
            path: {
                'token': token,
            },
            query: {
                'duration': duration,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Public Booking
     * Create a booking from a public link
     * @param token
     * @param requestBody
     * @returns SuccessResponse Successful Response
     * @throws ApiError
     */
    public static createPublicBookingApiV1BookingsPublicTokenBookPost(
        token: string,
        requestBody: CreatePublicBookingRequest,
    ): CancelablePromise<SuccessResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/public/{token}/book',
            path: {
                'token': token,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Booking Links
     * List all booking links for the authenticated user
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listBookingLinksApiV1BookingsLinksGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/links',
        });
    }
    /**
     * Create Booking Link
     * Create a new evergreen booking link
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createBookingLinkApiV1BookingsLinksPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/links',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Booking Link
     * Get a specific booking link
     * @param linkId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getBookingLinkApiV1BookingsLinksLinkIdGet(
        linkId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/links/{link_id}',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Booking Link
     * Update a booking link's settings
     * @param linkId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateBookingLinkApiV1BookingsLinksLinkIdPatch(
        linkId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/bookings/links/{link_id}',
            path: {
                'link_id': linkId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Duplicate Booking Link
     * Duplicate an existing booking link
     * @param linkId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static duplicateBookingLinkApiV1BookingsLinksLinkIdDuplicatePost(
        linkId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/links/{link_id}/duplicate',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Toggle Booking Link
     * Toggle a booking link's active status
     * @param linkId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static toggleBookingLinkApiV1BookingsLinksLinkIdTogglePost(
        linkId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/links/{link_id}/toggle',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create One Time Link
     * Create a one-time link for a specific recipient
     * @param linkId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createOneTimeLinkApiV1BookingsLinksLinkIdOneTimePost(
        linkId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/links/{link_id}/one-time',
            path: {
                'link_id': linkId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List One Time Links
     * List all one-time links for a specific booking link
     * @param linkId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listOneTimeLinksApiV1BookingsLinksLinkIdOneTimeGet(
        linkId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/links/{link_id}/one-time',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Link Analytics
     * Get analytics for a specific booking link
     * @param linkId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLinkAnalyticsApiV1BookingsLinksLinkIdAnalyticsGet(
        linkId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/links/{link_id}/analytics',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Booking Templates
     * List all booking templates for the authenticated user
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listBookingTemplatesApiV1BookingsTemplatesGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/templates',
        });
    }
    /**
     * Create Booking Template
     * Create a new booking template
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createBookingTemplateApiV1BookingsTemplatesPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/bookings/templates',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Booking Template
     * Get a specific booking template
     * @param templateId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getBookingTemplateApiV1BookingsTemplatesTemplateIdGet(
        templateId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Booking Template
     * Update a booking template
     * @param templateId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateBookingTemplateApiV1BookingsTemplatesTemplateIdPatch(
        templateId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/bookings/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Booking Template
     * Delete a booking template
     * @param templateId
     * @returns string Successful Response
     * @throws ApiError
     */
    public static deleteBookingTemplateApiV1BookingsTemplatesTemplateIdDelete(
        templateId: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/bookings/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get One Time Link Details
     * Get details of a one-time link (for owner)
     * @param token
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getOneTimeLinkDetailsApiV1BookingsOneTimeTokenGet(
        token: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/bookings/one-time/{token}',
            path: {
                'token': token,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update One Time Link
     * Update a one-time link
     * @param token
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateOneTimeLinkApiV1BookingsOneTimeTokenPatch(
        token: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/bookings/one-time/{token}',
            path: {
                'token': token,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete One Time Link
     * Delete a one-time link
     * @param token
     * @returns string Successful Response
     * @throws ApiError
     */
    public static deleteOneTimeLinkApiV1BookingsOneTimeTokenDelete(
        token: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/bookings/one-time/{token}',
            path: {
                'token': token,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
