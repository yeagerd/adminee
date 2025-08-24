/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Create model for contacts.
 */
export type ContactCreate = {
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
     * Contact tags
     */
    tags?: (Array<string> | null);
    /**
     * Additional notes about the contact
     */
    notes?: (string | null);
};

