import { EmailMessage } from '@/types/office-service';
import { shipmentsApi } from '@/api';
import type { PackageStatus, EmailParseRequest, EmailParseResponse, PackageCreateRequest, PackageResponse, DataCollectionRequest, DataCollectionResponse, PackageRefreshResponse } from '@/api/clients/shipments-client';

// Re-export types for backward compatibility
export type { PackageStatus, EmailParseRequest, EmailParseResponse, PackageCreateRequest, PackageResponse, DataCollectionRequest, DataCollectionResponse, PackageRefreshResponse };

// Remove duplicate type definitions since they're now imported from the API

class ShipmentsClient {
    /**
     * Parse email content to detect shipment information
     */
    async parseEmail(email: EmailMessage): Promise<EmailParseResponse> {
        const request: EmailParseRequest = {
            subject: email.subject || '',
            sender: email.from_address?.email || '',
            body: email.body_html || email.body_text || '',
            content_type: email.body_html ? 'html' : 'text',
        };

        return shipmentsApi.parseEmail(request);
    }

    /**
     * Create a new package tracking entry
     */
    async createPackage(packageData: PackageCreateRequest): Promise<PackageResponse> {
        return shipmentsApi.createPackage(packageData);
    }

    /**
     * Submit data collection for training improvements
     */
    async collectData(data: DataCollectionRequest): Promise<DataCollectionResponse> {
        return shipmentsApi.collectShipmentData(data);
    }

    /**
     * Get all packages for the current user
     */
    async getPackages(params?: {
        cursor?: string;
        limit?: number;
        direction?: 'next' | 'prev';
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
        date_range?: string;
    }): Promise<{ packages: PackageResponse[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return shipmentsApi.getPackages(params);
    }

    /**
     * Check if a package exists with the given tracking number and carrier
     */
    async checkPackageExists(trackingNumber: string, carrier?: string): Promise<PackageResponse | null> {
        const params: { tracking_number: string; carrier?: string } = {
            tracking_number: trackingNumber
        };

        // Always include carrier in the request if it's provided, even if it's 'unknown'
        if (carrier) {
            params.carrier = carrier;
        }

        const response = await shipmentsApi.getPackages(params);

        // If no packages found, return null
        if (response.packages.length === 0) {
            return null;
        }

        // If exactly one package found, return it
        if (response.packages.length === 1) {
            return response.packages[0];
        }

        // Multiple packages found - handle based on carrier specification
        if (carrier) {
            // If carrier was specified, try to find a package that matches the specified carrier
            const matchingPackage = response.packages.find((pkg: PackageResponse) => pkg.carrier === carrier);
            if (matchingPackage) {
                return matchingPackage;
            }
            // If no matching carrier found, throw a more specific error
            throw new Error(`Multiple packages found with tracking number ${trackingNumber}, but none match the specified carrier '${carrier}'.`);
        } else {
            // No carrier specified - this indicates ambiguity
            throw new Error(`Multiple packages found with tracking number ${trackingNumber}. Please specify the carrier.`);
        }
    }

    /**
     * Get package by email message ID
     */
    async getPackageByEmail(emailMessageId: string): Promise<PackageResponse | null> {
        try {
            const response = await shipmentsApi.request<{ data: PackageResponse[] }>(`/api/v1/shipments/packages?email_message_id=${encodeURIComponent(emailMessageId)}`);

            if (response && response.data && response.data.length > 0) {
                return response.data[0];
            }

            return null;
        } catch (error: unknown) {
            if (error instanceof Error && 'response' in error && (error as { response?: { status?: number } }).response?.status === 404) {
                return null;
            }
            console.error('Error getting package by email:', error);
            return null;
        }
    }

    /**
     * Get a specific package by ID
     */
    async getPackage(id: string): Promise<PackageResponse> { // Changed from number to string (UUID)
        return shipmentsApi.getPackage(id);
    }

    /**
     * Update a package
     */
    async updatePackage(id: string, packageData: Partial<PackageCreateRequest>): Promise<PackageResponse> { // Changed from number to string (UUID)
        return shipmentsApi.updatePackage(id, packageData);
    }

    /**
     * Delete a package
     */
    async deletePackage(id: string): Promise<void> { // Changed from number to string (UUID)
        return shipmentsApi.deletePackage(id);
    }

    /**
     * Refresh tracking information for a package
     */
    async refreshPackage(id: string): Promise<PackageRefreshResponse> { // Changed from number to string (UUID)
        return shipmentsApi.refreshPackage(id);
    }

    /**
     * Get tracking events for a package
     */
    async getTrackingEvents(packageId: string): Promise<Array<{ // Changed from number to string (UUID)
        id: string; // Changed from number to string (UUID)
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }>> {
        return shipmentsApi.getTrackingEvents(packageId);
    }

    /**
     * Get tracking events by email message ID
     */
    async getEventsByEmail(emailMessageId: string): Promise<Array<{
        id: string;
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }>> {
        return shipmentsApi.getEventsByEmail(emailMessageId);
    }

    /**
     * Create a new tracking event for a package
     */
    async createTrackingEvent(packageId: string, eventData: {
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        email_message_id?: string;
    }): Promise<{
        id: string; // Changed from number to string (UUID)
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }> {
        return shipmentsApi.createTrackingEvent(packageId, eventData);
    }

    /**
     * Get the next page of packages using cursor pagination
     */
    async getNextPage(cursor: string, limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageResponse[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            cursor,
            limit,
            direction: 'next',
            ...filters
        });
    }

    /**
     * Get the previous page of packages using cursor pagination
     */
    async getPrevPage(cursor: string, limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageResponse[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            cursor,
            limit,
            direction: 'prev',
            ...filters
        });
    }

    /**
     * Get the first page of packages using cursor pagination
     */
    async getFirstPage(limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageResponse[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            limit,
            direction: 'next',
            ...filters
        });
    }
}

// Export a singleton instance
export const shipmentsClient = new ShipmentsClient();

// Export the class for testing
export default ShipmentsClient; 