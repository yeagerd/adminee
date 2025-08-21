/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new user.
 */
export type UserCreate = {
    /**
     * User's email address
     */
    email: string;
    /**
     * User's first name
     */
    first_name?: (string | null);
    /**
     * User's last name
     */
    last_name?: (string | null);
    /**
     * URL to user's profile image
     */
    profile_image_url?: (string | null);
    /**
     * External authentication provider user ID
     */
    external_auth_id: string;
    /**
     * Authentication provider name
     */
    auth_provider?: string;
    /**
     * Preferred integration provider (google or microsoft)
     */
    preferred_provider?: (string | null);
};

