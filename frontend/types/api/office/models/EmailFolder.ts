/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Provider } from './Provider';
/**
 * Model for email folders/labels.
 */
export type EmailFolder = {
    /**
     * Unique identifier for the folder/label
     */
    label: string;
    /**
     * Display name for the folder/label
     */
    name: string;
    /**
     * Provider this folder belongs to
     */
    provider: Provider;
    /**
     * Provider-specific folder ID
     */
    provider_folder_id?: (string | null);
    /**
     * Which account this folder belongs to
     */
    account_email: string;
    /**
     * Display name for the account
     */
    account_name?: (string | null);
    /**
     * Whether this is a system folder (inbox, sent, etc.)
     */
    is_system?: boolean;
    /**
     * Number of messages in this folder
     */
    message_count?: (number | null);
};

