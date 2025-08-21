/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for user listing with cursor pagination.
 */
export type UserListResponse = {
    /**
     * List of users
     */
    users: Array<Record<string, any>>;
    /**
     * Cursor token for next page
     */
    next_cursor?: (string | null);
    /**
     * Cursor token for previous page
     */
    prev_cursor?: (string | null);
    /**
     * Whether there are more users after this page
     */
    has_next: boolean;
    /**
     * Whether there are users before this page
     */
    has_prev: boolean;
    /**
     * Number of users per page
     */
    limit: number;
};

