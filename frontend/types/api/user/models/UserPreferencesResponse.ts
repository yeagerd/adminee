/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIPreferencesSchema } from './AIPreferencesSchema';
import type { IntegrationPreferencesSchema } from './IntegrationPreferencesSchema';
import type { NotificationPreferencesSchema } from './NotificationPreferencesSchema';
import type { PrivacyPreferencesSchema } from './PrivacyPreferencesSchema';
import type { UIPreferencesSchema } from './UIPreferencesSchema';
/**
 * Complete user preferences response schema.
 */
export type UserPreferencesResponse = {
    /**
     * User ID
     */
    user_id: string;
    /**
     * Preferences schema version
     */
    version?: string;
    /**
     * UI preferences
     */
    ui: UIPreferencesSchema;
    /**
     * Notification preferences
     */
    notifications: NotificationPreferencesSchema;
    /**
     * AI preferences
     */
    ai: AIPreferencesSchema;
    /**
     * Integration preferences
     */
    integrations: IntegrationPreferencesSchema;
    /**
     * Privacy preferences
     */
    privacy: PrivacyPreferencesSchema;
    /**
     * Creation timestamp
     */
    created_at: string;
    /**
     * Last update timestamp
     */
    updated_at: string;
    /**
     * Timezone mode: 'auto' or 'manual'
     */
    timezone_mode?: string;
    /**
     * Manual timezone override (IANA name, or empty if not set)
     */
    manual_timezone?: string;
};

