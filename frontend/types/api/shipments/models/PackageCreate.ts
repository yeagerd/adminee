/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PackageStatus } from './PackageStatus';
export type PackageCreate = {
    tracking_number: string;
    carrier: string;
    status?: (PackageStatus | null);
    estimated_delivery?: (string | null);
    actual_delivery?: (string | null);
    recipient_name?: (string | null);
    shipper_name?: (string | null);
    package_description?: (string | null);
    order_number?: (string | null);
    tracking_link?: (string | null);
    email_message_id?: (string | null);
};

