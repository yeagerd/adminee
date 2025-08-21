/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfigurationStatus } from './ConfigurationStatus';
import type { DatabaseStatus } from './DatabaseStatus';
import type { DependencyStatus } from './DependencyStatus';
export type ReadinessChecks = {
    database: DatabaseStatus;
    configuration: ConfigurationStatus;
    dependencies: DependencyStatus;
};

