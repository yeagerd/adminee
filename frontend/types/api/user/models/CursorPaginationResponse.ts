/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Base response schema for cursor-based pagination.
 */
export type CursorPaginationResponse = {
    items: Array<any>;
    /**
     * Cursor token for next page
     */
    next_cursor?: (string | null);
    /**
     * Cursor token for previous page
     */
    prev_cursor?: (string | null);
    /**
     * Whether there are more items after this page
     */
    has_next: boolean;
    /**
     * Whether there are items before this page
     */
    has_prev: boolean;
    /**
     * Number of items per page
     */
    limit: number;
};

