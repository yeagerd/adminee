/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataRetentionPeriod } from './DataRetentionPeriod';
/**
 * Privacy preferences schema.
 */
export type PrivacyPreferencesSchema = {
    /**
     * Allow data collection for improvements
     */
    data_collection?: boolean;
    /**
     * Allow analytics tracking
     */
    analytics?: boolean;
    /**
     * Allow personalization based on usage
     */
    personalization?: boolean;
    /**
     * Data retention period
     */
    data_retention_period?: DataRetentionPeriod;
    /**
     * Share anonymous usage statistics
     */
    share_anonymous_usage?: boolean;
    /**
     * Receive marketing communications
     */
    marketing_communications?: boolean;
    /**
     * Use secure deletion methods
     */
    secure_deletion?: boolean;
    /**
     * Encrypt sensitive data
     */
    encrypt_sensitive_data?: boolean;
    /**
     * Allow collection of shipment data for service improvements
     */
    shipment_data_collection?: boolean;
};

