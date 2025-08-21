/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CreatePublicBookingRequest = {
    /**
     * Start time of the meeting
     */
    start?: string;
    /**
     * End time of the meeting
     */
    end?: string;
    /**
     * Email address of the attendee
     */
    attendee_email?: string;
    /**
     * Answers to template questions
     */
    answers?: Record<string, string>;
};

