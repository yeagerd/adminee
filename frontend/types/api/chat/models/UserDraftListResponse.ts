/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserDraftResponse } from './UserDraftResponse';
/**
 * Response model for user draft lists.
 */
export type UserDraftListResponse = {
    drafts: Array<UserDraftResponse>;
    total_count: number;
    has_more: boolean;
};

