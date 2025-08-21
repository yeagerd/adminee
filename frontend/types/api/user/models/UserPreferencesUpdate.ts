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
 * User preferences update schema for partial updates.
 */
export type UserPreferencesUpdate = {
    /**
     * UI preferences to update
     */
    ui?: (UIPreferencesSchema | null);
    /**
     * Notification preferences to update
     */
    notifications?: (NotificationPreferencesSchema | null);
    /**
     * AI preferences to update
     */
    ai?: (AIPreferencesSchema | null);
    /**
     * Integration preferences to update
     */
    integrations?: (IntegrationPreferencesSchema | null);
    /**
     * Privacy preferences to update
     */
    privacy?: (PrivacyPreferencesSchema | null);
    /**
     * Timezone mode: 'auto' or 'manual'
     */
    timezone_mode?: (string | null);
    /**
     * Manual timezone override (IANA name, or empty if not set)
     */
    manual_timezone?: (string | null);
};

