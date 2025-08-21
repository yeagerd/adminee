/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for user drafts.
 */
export type UserDraftResponse = {
    id: string;
    user_id: string;
    type: string;
    content: string;
    metadata: Record<string, any>;
    status: string;
    thread_id?: (string | null);
    created_at: string;
    updated_at: string;
};

