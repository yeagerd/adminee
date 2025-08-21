/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PackageStatus } from './PackageStatus';
export type TrackingEventCreate = {
    event_date: string;
    status: PackageStatus;
    location?: (string | null);
    description?: (string | null);
    email_message_id?: (string | null);
};

