/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PackageStatus } from './PackageStatus';
export type PackageUpdate = {
    status: (PackageStatus | null);
    estimated_delivery: (string | null);
    actual_delivery: (string | null);
    recipient_name: (string | null);
    shipper_name: (string | null);
    package_description: (string | null);
    order_number: (string | null);
    tracking_link: (string | null);
    archived_at: (string | null);
};

