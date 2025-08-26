/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailContactEventCount } from './EmailContactEventCount';
/**
 * Contact database model with event type counters and last_seen tracking.
 */
export type Contact = {
    /**
     * Unique contact ID
     */
    id?: (string | null);
    /**
     * User ID who owns this contact
     */
    user_id: string;
    /**
     * Contact's email address
     */
    email_address: string;
    /**
     * Contact's display name
     */
    display_name?: (string | null);
    /**
     * Contact's given/first name
     */
    given_name?: (string | null);
    /**
     * Contact's family/last name
     */
    family_name?: (string | null);
    /**
     * Count of events by type for this contact
     */
    event_counts?: Record<string, EmailContactEventCount>;
    /**
     * Total number of events across all types
     */
    total_event_count?: number;
    /**
     * When this contact was last seen in any event
     */
    last_seen: string;
    /**
     * When this contact was first seen
     */
    first_seen: string;
    /**
     * Contact relevance score (0.0 to 1.0)
     */
    relevance_score?: number;
    /**
     * Factors contributing to relevance score
     */
    relevance_factors?: Record<string, number>;
    /**
     * Services where this contact was discovered
     */
    source_services?: Array<string>;
    /**
     * Contact tags
     */
    tags?: Array<string>;
    /**
     * Additional notes about the contact
     */
    notes?: (string | null);
    /**
     * Office service provider (Google, Microsoft, etc.)
     */
    provider?: (string | null);
    /**
     * When this contact was last synced from Office Service
     */
    last_synced?: (string | null);
    /**
     * Contact phone numbers
     */
    phone_numbers?: (Array<string> | null);
    /**
     * Contact addresses
     */
    addresses?: Array<Record<string, any>>;
    /**
     * When this contact record was created
     */
    created_at?: string;
    /**
     * When this contact record was last updated
     */
    updated_at?: string;
};

