/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for package listing with cursor pagination.
 */
export type PackageListResponse = {
    /**
     * List of packages
     */
    packages: Array<Record<string, any>>;
    /**
     * Cursor token for next page
     */
    next_cursor?: (string | null);
    /**
     * Cursor token for previous page
     */
    prev_cursor?: (string | null);
    /**
     * Whether there are more packages after this page
     */
    has_next: boolean;
    /**
     * Whether there are packages before this page
     */
    has_prev: boolean;
    /**
     * Number of packages per page
     */
    limit: number;
};

