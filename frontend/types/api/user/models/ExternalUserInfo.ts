/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for external user information from OAuth providers.
 */
export type ExternalUserInfo = {
    id: string;
    email: string;
    name?: (string | null);
    picture?: (string | null);
    locale?: (string | null);
    verified_email?: (boolean | null);
    provider: string;
};

