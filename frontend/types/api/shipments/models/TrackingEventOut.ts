/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PackageStatus } from './PackageStatus';
export type TrackingEventOut = {
    id: string;
    event_date: string;
    status: PackageStatus;
    location: (string | null);
    description: (string | null);
    created_at: string;
};

