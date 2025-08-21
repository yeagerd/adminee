/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
import type { Provider } from './Provider';
export type EmailMessage = {
    id: string;
    thread_id?: (string | null);
    subject?: (string | null);
    snippet?: (string | null);
    body_text?: (string | null);
    body_html?: (string | null);
    from_address?: (EmailAddress | null);
    to_addresses?: Array<EmailAddress>;
    cc_addresses?: Array<EmailAddress>;
    bcc_addresses?: Array<EmailAddress>;
    date: string;
    labels?: Array<string>;
    is_read?: boolean;
    has_attachments?: boolean;
    provider: Provider;
    provider_message_id: string;
    account_email: string;
    account_name?: (string | null);
};

