/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for contact deletion.
 */
export type ContactDeleteResponse = {
    success: boolean;
    deleted_contact_id?: (string | null);
    error?: (Record<string, any> | null);
    request_id: string;
};

