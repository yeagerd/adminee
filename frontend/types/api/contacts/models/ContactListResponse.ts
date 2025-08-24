/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Contact } from './Contact';
/**
 * Response model for contact lists.
 */
export type ContactListResponse = {
    contacts: Array<Contact>;
    total: number;
    limit: number;
    offset: number;
    success?: boolean;
    message?: (string | null);
};

