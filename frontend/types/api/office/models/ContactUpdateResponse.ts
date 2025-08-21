/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Contact } from './Contact';
/**
 * Response model for contact updates.
 */
export type ContactUpdateResponse = {
    success: boolean;
    contact?: (Contact | null);
    error?: (Record<string, any> | null);
    request_id: string;
};

