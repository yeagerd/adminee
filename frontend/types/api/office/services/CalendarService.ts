/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse } from '../models/ApiResponse';
import type { CreateCalendarEventRequest } from '../models/CreateCalendarEventRequest';
import type { TypedApiResponse_AvailabilityResponse_ } from '../models/TypedApiResponse_AvailabilityResponse_';
import type { TypedApiResponse_CalendarEventResponse_ } from '../models/TypedApiResponse_CalendarEventResponse_';
import type { TypedApiResponse_List_CalendarEvent__ } from '../models/TypedApiResponse_List_CalendarEvent__';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CalendarService {
    /**
     * Get User Availability
     * Get user availability for a given time range.
     *
     * Checks the user's calendar across multiple providers to find available time slots
     * for a meeting of the specified duration.
     *
     * Args:
     * start: Start time for availability check
     * end: End time for availability check
     * duration: Duration in minutes for the meeting
     * providers: List of providers to check (defaults to all available)
     *
     * Returns:
     * ApiResponse with available time slots
     * @param start Start time for availability check (ISO format)
     * @param end End time for availability check (ISO format)
     * @param duration Duration in minutes for the meeting
     * @param providers Providers to check (google, microsoft). If not specified, checks all available providers
     * @returns TypedApiResponse_AvailabilityResponse_ Successful Response
     * @throws ApiError
     */
    public static getUserAvailabilityV1CalendarAvailabilityGet(
        start: string,
        end: string,
        duration: number,
        providers?: (Array<string> | null),
    ): CancelablePromise<TypedApiResponse_AvailabilityResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/calendar/availability',
            query: {
                'start': start,
                'end': end,
                'duration': duration,
                'providers': providers,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Calendar Events
     * Get unified calendar events from multiple providers.
     *
     * Fetches calendar events from Google Calendar and Microsoft Calendar APIs,
     * normalizes them to a unified format, and returns aggregated results.
     * Responses are cached for improved performance.
     *
     * Args:
     * user_id: ID of the user to fetch events for
     * providers: List of providers to query (defaults to all available)
     * limit: Maximum events per provider
     * start_date: Start date for filtering (defaults to today)
     * end_date: End date for filtering (defaults to 30 days from start)
     * calendar_ids: Specific calendars to query
     * q: Search query string
     * time_zone: Time zone for date operations
     *
     * Returns:
     * ApiResponse with aggregated calendar events
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param limit Maximum number of events to return per provider
     * @param startDate Start date for event range (ISO format: YYYY-MM-DD)
     * @param endDate End date for event range (ISO format: YYYY-MM-DD)
     * @param calendarIds Specific calendar IDs to fetch from
     * @param q Search query to filter events
     * @param timeZone Time zone for date filtering
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns TypedApiResponse_List_CalendarEvent__ Successful Response
     * @throws ApiError
     */
    public static getCalendarEventsV1CalendarEventsGet(
        providers?: (Array<string> | null),
        limit: number = 50,
        startDate?: (string | null),
        endDate?: (string | null),
        calendarIds?: (Array<string> | null),
        q?: (string | null),
        timeZone?: (string | null),
        noCache: boolean = false,
    ): CancelablePromise<TypedApiResponse_List_CalendarEvent__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/calendar/events',
            query: {
                'providers': providers,
                'limit': limit,
                'start_date': startDate,
                'end_date': endDate,
                'calendar_ids': calendarIds,
                'q': q,
                'time_zone': timeZone,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Calendar Event
     * Create a calendar event in a specific provider.
     *
     * This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
     * provider-specific format, and uses the correct API client to create the event.
     *
     * Args:
     * event_data: Event content and configuration
     *
     * Returns:
     * ApiResponse with created event details
     * @param requestBody
     * @returns TypedApiResponse_CalendarEventResponse_ Successful Response
     * @throws ApiError
     */
    public static createCalendarEventV1CalendarEventsPost(
        requestBody: CreateCalendarEventRequest,
    ): CancelablePromise<TypedApiResponse_CalendarEventResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/calendar/events',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Calendar Event
     * Get a specific calendar event by ID.
     *
     * The event_id should be in the format "provider_originalId" (e.g., "google_abc123" or "microsoft_xyz789").
     * This endpoint determines the correct provider from the event ID and fetches the full event details.
     *
     * Args:
     * event_id: Event ID with provider prefix
     *
     * Returns:
     * ApiResponse with the specific calendar event
     * @param eventId Event ID (format: provider_originalId)
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static getCalendarEventV1CalendarEventsEventIdGet(
        eventId: string,
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/calendar/events/{event_id}',
            path: {
                'event_id': eventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Calendar Event
     * Update a calendar event by ID.
     *
     * This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
     * provider-specific format, and uses the correct API client to update the event.
     *
     * Args:
     * event_id: Event ID with provider prefix (e.g., "google_abc123")
     * event_data: Updated event content and configuration
     *
     * Returns:
     * ApiResponse with updated event details
     * @param eventId Event ID (format: provider_originalId)
     * @param requestBody
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static updateCalendarEventV1CalendarEventsEventIdPut(
        eventId: string,
        requestBody: CreateCalendarEventRequest,
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/calendar/events/{event_id}',
            path: {
                'event_id': eventId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Calendar Event
     * Delete a calendar event by ID.
     *
     * This endpoint requires logic to find the original provider from the event ID
     * and use its API to delete the event.
     *
     * Args:
     * event_id: Event ID with provider prefix (e.g., "google_abc123")
     *
     * Returns:
     * ApiResponse confirming deletion
     * @param eventId Event ID (format: provider_originalId)
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static deleteCalendarEventV1CalendarEventsEventIdDelete(
        eventId: string,
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/calendar/events/{event_id}',
            path: {
                'event_id': eventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
