/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimeSlot } from '../models/TimeSlot';
import type { TimeSlotCreate } from '../models/TimeSlotCreate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SlotsService {
    /**
     * Add Slot
     * @param pollId
     * @param requestBody
     * @returns TimeSlot Successful Response
     * @throws ApiError
     */
    public static addSlotApiV1MeetingsPollsPollIdSlotsPost(
        pollId: string,
        requestBody: TimeSlotCreate,
    ): CancelablePromise<TimeSlot> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/slots/',
            path: {
                'poll_id': pollId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Slot
     * @param pollId
     * @param slotId
     * @param requestBody
     * @returns TimeSlot Successful Response
     * @throws ApiError
     */
    public static updateSlotApiV1MeetingsPollsPollIdSlotsSlotIdPut(
        pollId: string,
        slotId: string,
        requestBody: TimeSlotCreate,
    ): CancelablePromise<TimeSlot> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/meetings/polls/{poll_id}/slots/{slot_id}',
            path: {
                'poll_id': pollId,
                'slot_id': slotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Slot
     * @param pollId
     * @param slotId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteSlotApiV1MeetingsPollsPollIdSlotsSlotIdDelete(
        pollId: string,
        slotId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/meetings/polls/{poll_id}/slots/{slot_id}',
            path: {
                'poll_id': pollId,
                'slot_id': slotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
