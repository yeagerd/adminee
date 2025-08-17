/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CarrierConfigOut } from '../models/CarrierConfigOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CarriersService {
    /**
     * List Carriers
     * List carrier configurations.
     *
     * **Authentication:**
     * - Requires user authentication (JWT token or gateway headers)
     * - Requires service API key for service-to-service calls
     * - Note: Carrier configs are typically system-wide, not user-specific
     * @returns CarrierConfigOut Successful Response
     * @throws ApiError
     */
    public static listCarriersV1ShipmentsCarriersGet(): CancelablePromise<Array<CarrierConfigOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/shipments/carriers/',
        });
    }
}
