/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Contact } from './Contact';
/**
 * Search result for email contacts.
 */
export type EmailContactSearchResult = {
    contact: Contact;
    relevance_score: number;
    match_highlights?: Array<string>;
};

