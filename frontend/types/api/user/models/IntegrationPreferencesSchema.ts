/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Integration preferences schema.
 */
export type IntegrationPreferencesSchema = {
    /**
     * Enable automatic synchronization
     */
    auto_sync?: boolean;
    /**
     * Sync frequency in minutes
     */
    sync_frequency?: number;
    /**
     * Enable Google Drive integration
     */
    google_drive_enabled?: boolean;
    /**
     * Enable Microsoft 365 integration
     */
    microsoft_365_enabled?: boolean;
    /**
     * Enable Dropbox integration
     */
    dropbox_enabled?: boolean;
    /**
     * Sync document content
     */
    sync_document_content?: boolean;
    /**
     * Sync file metadata
     */
    sync_metadata?: boolean;
    /**
     * Sync file permissions
     */
    sync_permissions?: boolean;
    /**
     * How to handle sync conflicts
     */
    conflict_resolution?: string;
};

