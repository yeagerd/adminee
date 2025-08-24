/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Count of events for a specific contact and event type.
 */
export type EmailContactEventCount = {
    /**
     * Type of event (email, calendar, document)
     */
    event_type: string;
    /**
     * Number of events of this type
     */
    count?: number;
    /**
     * When this contact was last seen in this event type
     */
    last_seen: string;
    /**
     * When this contact was first seen in this event type
     */
    first_seen: string;
};

