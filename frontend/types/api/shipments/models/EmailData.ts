/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for email content data.
 */
export type EmailData = {
    subject: string;
    sender: string;
    body: string;
    content_type?: string;
    received_at?: (string | null);
    message_id?: (string | null);
};

