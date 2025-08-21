/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContactPhone } from './ContactPhone';
import type { EmailAddress } from './EmailAddress';
import type { Provider } from './Provider';
export type Contact = {
    id: string;
    full_name?: (string | null);
    given_name?: (string | null);
    family_name?: (string | null);
    emails?: Array<EmailAddress>;
    primary_email?: (EmailAddress | null);
    company?: (string | null);
    job_title?: (string | null);
    phones?: Array<ContactPhone>;
    photo_url?: (string | null);
    provider: Provider;
    provider_contact_id: string;
    account_email: string;
    account_name?: (string | null);
};

