/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Individual tracking information found in email
 */
export type ParsedTrackingInfo = {
    /**
     * Extracted tracking number
     */
    tracking_number: string;
    /**
     * Detected carrier name
     */
    carrier?: (string | null);
    /**
     * Confidence score for this detection
     */
    confidence: number;
    /**
     * Where this information was found: 'subject', 'body', or 'both'
     */
    source: string;
};

