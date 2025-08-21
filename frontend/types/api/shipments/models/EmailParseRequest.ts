/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for email parsing
 */
export type EmailParseRequest = {
    /**
     * Email subject line
     */
    subject: string;
    /**
     * Email sender address
     */
    sender: string;
    /**
     * Email body content (HTML or text)
     */
    body: string;
    /**
     * Content type: 'text' or 'html'
     */
    content_type?: string;
};

