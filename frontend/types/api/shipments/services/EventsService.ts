/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailParseRequest } from '../models/EmailParseRequest';
import type { EmailParseResponse } from '../models/EmailParseResponse';
import type { TrackingEventOut } from '../models/TrackingEventOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EventsService {
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
