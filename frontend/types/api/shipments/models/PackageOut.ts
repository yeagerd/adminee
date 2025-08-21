/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LabelOut } from './LabelOut';
import type { PackageStatus } from './PackageStatus';
export type PackageOut = {
    id: string;
    user_id: string;
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    estimated_delivery: (string | null);
    actual_delivery: (string | null);
    recipient_name: (string | null);
    shipper_name: (string | null);
    package_description: (string | null);
    order_number: (string | null);
    tracking_link: (string | null);
    created_at: string;
    updated_at: string;
    events_count: number;
    labels: Array<LabelOut>;
};

