/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserResponse } from './UserResponse';
/**
 * Response model for user creation/upsert with creation status.
 */
export type UserCreateResponse = {
    user: UserResponse;
    created: boolean;
};

