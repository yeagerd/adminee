/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ReadinessStatus } from '../models/ReadinessStatus';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * Service health check
     * Basic health check for load balancer liveness probes
     * @returns ReadinessStatus Service is healthy and ready to handle requests
     * @throws ApiError
     */
    public static healthCheckHealthGet(): CancelablePromise<ReadinessStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
            errors: {
                503: `Service is unhealthy and should not receive traffic`,
            },
        });
    }
    /**
     * Service readiness check
     * Comprehensive readiness check for load balancer readiness probes
     * @returns ReadinessStatus Service is ready to handle requests
     * @throws ApiError
     */
    public static readinessCheckReadyGet(): CancelablePromise<ReadinessStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/ready',
            errors: {
                503: `Service is not ready to handle requests`,
            },
        });
    }
}
