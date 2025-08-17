/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse } from '../models/ApiResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class FilesService {
    /**
     * Get Files
     * Get unified files from multiple providers.
     *
     * Fetches files from Google Drive and Microsoft OneDrive APIs,
     * normalizes them to a unified format, and returns aggregated results.
     * Responses are cached for improved performance.
     *
     * Args:
     * user_id: ID of the user to fetch files for
     * providers: List of providers to query (defaults to all available)
     * limit: Maximum files per provider
     * folder_id: Specific folder to list (provider-specific ID)
     * file_types: Filter by file types/mime types
     * q: Search query string
     * order_by: Sort order for results
     * include_folders: Whether to include folders
     *
     * Returns:
     * ApiResponse with aggregated files
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param limit Maximum number of files to return per provider
     * @param folderId Folder ID to list files from (provider-specific)
     * @param fileTypes Filter by file types/mime types
     * @param q Search query to filter files
     * @param orderBy Sort order (modifiedTime, name, size)
     * @param includeFolders Whether to include folders in results
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static getFilesV1FilesGet(
        providers?: (Array<string> | null),
        limit: number = 50,
        folderId?: (string | null),
        fileTypes?: (Array<string> | null),
        q?: (string | null),
        orderBy?: (string | null),
        includeFolders: boolean = true,
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/files/',
            query: {
                'providers': providers,
                'limit': limit,
                'folder_id': folderId,
                'file_types': fileTypes,
                'q': q,
                'order_by': orderBy,
                'include_folders': includeFolders,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search Files
     * Search files across multiple providers.
     *
     * Performs a unified search across Google Drive and Microsoft OneDrive,
     * returning aggregated and normalized results.
     *
     * Args:
     * q: Search query string
     * providers: List of providers to search (defaults to all)
     * limit: Maximum results per provider
     * file_types: Filter by file types
     *
     * Returns:
     * ApiResponse with search results
     * @param q Search query
     * @param providers Providers to search in (google, microsoft)
     * @param limit Maximum number of results per provider
     * @param fileTypes Filter by file types/mime types
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static searchFilesV1FilesSearchGet(
        q: string,
        providers?: (Array<string> | null),
        limit: number = 50,
        fileTypes?: (Array<string> | null),
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/files/search',
            query: {
                'q': q,
                'providers': providers,
                'limit': limit,
                'file_types': fileTypes,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get File
     * Get a specific file by ID.
     *
     * The file_id should be in the format "provider_originalId" (e.g., "google_abc123" or "microsoft_xyz789").
     * This endpoint determines the correct provider from the file ID and fetches the full file details.
     *
     * Args:
     * file_id: File ID with provider prefix
     * include_download_url: Whether to include download URL
     *
     * Returns:
     * ApiResponse with the specific file
     * @param fileId File ID (format: provider_originalId)
     * @param includeDownloadUrl Whether to include download URL
     * @returns ApiResponse Successful Response
     * @throws ApiError
     */
    public static getFileV1FilesFileIdGet(
        fileId: string,
        includeDownloadUrl: boolean = false,
    ): CancelablePromise<ApiResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/files/{file_id}',
            path: {
                'file_id': fileId,
            },
            query: {
                'include_download_url': includeDownloadUrl,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
