/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InvitationsService {
    /**
     * Send Invitations
     * @param pollId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static sendInvitationsApiV1MeetingsPollsPollIdSendInvitationsPost(
        pollId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/meetings/polls/{poll_id}/send-invitations/',
            path: {
                'poll_id': pollId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
