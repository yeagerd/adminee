/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Contact } from './Contact';
/**
 * Response model for contact creation.
 */
export type ContactCreateResponse = {
    success: boolean;
    contact?: (Contact | null);
    error?: (Record<string, any> | null);
    request_id: string;
};

