/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Draft email data structure.
 */
export type DraftEmail = {
    id?: (string | null);
    type?: string;
    to?: (string | null);
    cc?: (string | null);
    bcc?: (string | null);
    subject?: (string | null);
    body?: (string | null);
    thread_id: string;
    created_at: string;
    updated_at?: (string | null);
};

