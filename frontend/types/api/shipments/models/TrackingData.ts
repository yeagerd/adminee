/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for tracking information data.
 */
export type TrackingData = {
    tracking_number: string;
    carrier?: (string | null);
    status?: (string | null);
    estimated_delivery?: (string | null);
    recipient_name?: (string | null);
    shipper_name?: (string | null);
    package_description?: (string | null);
    order_number?: (string | null);
    tracking_link?: (string | null);
    confidence?: (number | null);
};

