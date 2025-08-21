/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PerformanceStatus } from './PerformanceStatus';
import type { ReadinessChecks } from './ReadinessChecks';
export type ReadinessStatus = {
    status: string;
    service: string;
    version: string;
    timestamp: string;
    environment: string;
    checks: ReadinessChecks;
    performance: PerformanceStatus;
};

