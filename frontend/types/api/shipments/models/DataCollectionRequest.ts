/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailData } from './EmailData';
import type { TrackingData } from './TrackingData';
/**
 * Request schema for collecting user-corrected shipment data
 */
export type DataCollectionRequest = {
    /**
     * Original email message ID
     */
    email_message_id: string;
    /**
     * Original email content
     */
    original_email_data: EmailData;
    /**
     * Auto-detected shipment data
     */
    auto_detected_data: TrackingData;
    /**
     * User-corrected shipment data
     */
    user_corrected_data: TrackingData;
    /**
     * Original detection confidence
     */
    detection_confidence: number;
    /**
     * Reason for user correction
     */
    correction_reason?: (string | null);
    /**
     * Whether user has given consent for data collection
     */
    consent_given: boolean;
};

