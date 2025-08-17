/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for data collection
 */
export type DataCollectionResponse = {
    /**
     * Whether data collection was successful
     */
    success: boolean;
    /**
     * Unique identifier for this data collection entry
     */
    collection_id: string;
    /**
     * When the data was collected
     */
    timestamp: string;
    /**
     * Response message
     */
    message: string;
};

