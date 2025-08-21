/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationFrequency } from './NotificationFrequency';
/**
 * Notification preferences schema.
 */
export type NotificationPreferencesSchema = {
    /**
     * Enable email notifications
     */
    email_notifications?: boolean;
    /**
     * Enable push notifications
     */
    push_notifications?: boolean;
    /**
     * Enable SMS notifications
     */
    sms_notifications?: boolean;
    /**
     * Frequency for summary notifications
     */
    summary_frequency?: NotificationFrequency;
    /**
     * Frequency for activity notifications
     */
    activity_frequency?: NotificationFrequency;
    /**
     * Notify on document updates
     */
    document_updates?: boolean;
    /**
     * Notify on system updates
     */
    system_updates?: boolean;
    /**
     * Notify on security alerts
     */
    security_alerts?: boolean;
    /**
     * Notify on integration status changes
     */
    integration_status?: boolean;
    /**
     * Enable quiet hours
     */
    quiet_hours_enabled?: boolean;
    /**
     * Quiet hours start time (HH:MM)
     */
    quiet_hours_start?: string;
    /**
     * Quiet hours end time (HH:MM)
     */
    quiet_hours_end?: string;
};

