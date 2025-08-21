/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailMessage } from './EmailMessage';
import type { Provider } from './Provider';
export type EmailThread = {
    id: string;
    subject?: (string | null);
    messages: Array<EmailMessage>;
    participant_count: number;
    last_message_date: string;
    is_read?: boolean;
    providers: Array<Provider>;
};

