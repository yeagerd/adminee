/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ParsedTrackingInfo } from './ParsedTrackingInfo';
/**
 * Response schema for email parsing
 */
export type EmailParseResponse = {
    /**
     * Whether this appears to be a shipment email
     */
    is_shipment_email: boolean;
    /**
     * Primary detected carrier
     */
    detected_carrier?: (string | null);
    /**
     * List of tracking numbers found
     */
    tracking_numbers?: Array<ParsedTrackingInfo>;
    /**
     * Overall confidence score
     */
    confidence: number;
    /**
     * Where detection was based: 'sender', 'subject', 'body', or 'multiple'
     */
    detected_from: string;
    /**
     * Suggested package data for creating tracking entry
     */
    suggested_package_data?: (Record<string, any> | null);
};

