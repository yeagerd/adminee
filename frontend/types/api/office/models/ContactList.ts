/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Contact } from './Contact';
import type { Provider } from './Provider';
/**
 * Response model for contact lists.
 */
export type ContactList = {
    success: boolean;
    data?: (Array<Contact> | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

