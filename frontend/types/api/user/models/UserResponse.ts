/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for user response data.
 */
export type UserResponse = {
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
     * User's internal database ID (primary key)
     */
    id: number;
    /**
     * External authentication provider user ID
     */
    external_auth_id: string;
    /**
     * Authentication provider name
     */
    auth_provider: string;
    /**
     * Preferred integration provider (google or microsoft)
     */
    preferred_provider?: (string | null);
    /**
     * Whether user has completed onboarding
     */
    onboarding_completed: boolean;
    /**
     * Current onboarding step if not completed
     */
    onboarding_step?: (string | null);
    /**
     * When the user was created
     */
    created_at: any;
    /**
     * When the user was last updated
     */
    updated_at: any;
};

