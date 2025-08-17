/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MeetingPoll } from '../models/MeetingPoll';
import type { MeetingPollCreate } from '../models/MeetingPollCreate';
import type { MeetingPollUpdate } from '../models/MeetingPollUpdate';
import type { PollParticipant } from '../models/PollParticipant';
import type { PollParticipantCreate } from '../models/PollParticipantCreate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PollsService {
    /**
     * List Polls
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static listPollsApiV1MeetingsPollsGet(): CancelablePromise<Array<MeetingPoll>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meetings/polls',
        });
    }
    /**
     * Create Poll
     * @param requestBody
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static createPollApiV1MeetingsPollsPost(
        requestBody: MeetingPollCreate,
    ): CancelablePromise<MeetingPoll> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Polls
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static listPollsApiV1MeetingsPollsGet1(): CancelablePromise<Array<MeetingPoll>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meetings/polls/',
        });
    }
    /**
     * Create Poll
     * @param requestBody
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static createPollApiV1MeetingsPollsPost1(
        requestBody: MeetingPollCreate,
    ): CancelablePromise<MeetingPoll> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Poll
     * @param pollId
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static getPollApiV1MeetingsPollsPollIdGet(
        pollId: string,
    ): CancelablePromise<MeetingPoll> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meetings/polls/{poll_id}',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Poll
     * @param pollId
     * @param requestBody
     * @returns MeetingPoll Successful Response
     * @throws ApiError
     */
    public static updatePollApiV1MeetingsPollsPollIdPut(
        pollId: string,
        requestBody: MeetingPollUpdate,
    ): CancelablePromise<MeetingPoll> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/meetings/polls/{poll_id}',
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
     * Delete Poll
     * @param pollId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deletePollApiV1MeetingsPollsPollIdDelete(
        pollId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/meetings/polls/{poll_id}',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Debug Poll
     * Debug endpoint to inspect poll details without authorization.
     * @param pollId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static debugPollApiV1MeetingsPollsPollIdDebugGet(
        pollId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meetings/polls/{poll_id}/debug',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Suggest Slots
     * @param pollId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static suggestSlotsApiV1MeetingsPollsPollIdSuggestSlotsGet(
        pollId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meetings/polls/{poll_id}/suggest-slots',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Schedule Meeting
     * @param pollId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static scheduleMeetingApiV1MeetingsPollsPollIdSchedulePost(
        pollId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/schedule',
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
     * Unschedule Meeting
     * @param pollId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static unscheduleMeetingApiV1MeetingsPollsPollIdUnschedulePost(
        pollId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/unschedule',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Resend Invitation
     * Resend invitation email to a specific participant.
     * @param pollId
     * @param participantId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static resendInvitationApiV1MeetingsPollsPollIdParticipantsParticipantIdResendInvitationPost(
        pollId: string,
        participantId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/participants/{participant_id}/resend-invitation',
            path: {
                'poll_id': pollId,
                'participant_id': participantId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Participant
     * Add a new participant to an existing poll.
     * @param pollId
     * @param requestBody
     * @returns PollParticipant Successful Response
     * @throws ApiError
     */
    public static addParticipantApiV1MeetingsPollsPollIdParticipantsPost(
        pollId: string,
        requestBody: PollParticipantCreate,
    ): CancelablePromise<PollParticipant> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/participants',
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
}
