import { EmailMessage } from '@/types/office-service';
import { gatewayClient } from './gateway-client';
import { PackageStatus } from './package-status';

// Define proper types for shipment data
export interface SuggestedPackageData {
    tracking_number?: string;
    carrier?: string;
    status?: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    estimated_delivery?: string;
    tracking_link?: string;
}

export interface PaginationInfo {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
}

export interface EmailParseRequest {
    subject: string;
    sender: string;
    body: string;
    content_type: string;
}

export interface ParsedTrackingInfo {
    tracking_number: string;
    carrier?: string;
    confidence: number;
    source: string;
}

export interface EmailParseResponse {
    is_shipment_email: boolean;
    detected_carrier?: string;
    tracking_numbers: ParsedTrackingInfo[];
    confidence: number;
    detected_from: string;
    suggested_package_data?: SuggestedPackageData;
}

export interface PackageCreateRequest {
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    estimated_delivery?: string;
    actual_delivery?: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    email_message_id?: string;
}

export interface PackageResponse {
    id: string; // Changed from number to string (UUID)
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    estimated_delivery?: string;
    actual_delivery?: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    updated_at: string;
    events_count: number;
    labels: string[];
}

export interface DataCollectionRequest {
    user_id: string;
    email_message_id: string;
    original_email_data: Record<string, unknown>;
    auto_detected_data: Record<string, unknown>;
    user_corrected_data: Record<string, unknown>;
    detection_confidence: number;
    correction_reason?: string;
    consent_given: boolean;
}

export interface DataCollectionResponse {
    success: boolean;
    collection_id: string;
    timestamp: string;
    message: string;
}

export interface PackageRefreshResponse {
    success: boolean;
    message: string;
    updated_data?: Partial<PackageResponse>;
}

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

        return gatewayClient.parseEmail(request);
    }

    /**
     * Create a new package tracking entry
     */
    async createPackage(packageData: PackageCreateRequest): Promise<PackageResponse> {
        return gatewayClient.createPackage(packageData);
    }

    /**
     * Submit data collection for training improvements
     */
    async collectData(data: DataCollectionRequest): Promise<DataCollectionResponse> {
        return gatewayClient.collectShipmentData(data);
    }

    /**
     * Get all packages for the current user
     */
    async getPackages(params?: {
        tracking_number?: string;
        carrier?: string;
    }): Promise<{ data: PackageResponse[]; pagination: PaginationInfo }> {
        return gatewayClient.getPackages(params);
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

        const response = await gatewayClient.getPackages(params);

        // If no packages found, return null
        if (response.data.length === 0) {
            return null;
        }

        // If exactly one package found, return it
        if (response.data.length === 1) {
            return response.data[0];
        }

        // Multiple packages found - handle based on carrier specification
        if (carrier) {
            // If carrier was specified, try to find a package that matches the specified carrier
            const matchingPackage = response.data.find(pkg => pkg.carrier === carrier);
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
            const response = await gatewayClient.request<{ data: PackageResponse[] }>(`/api/v1/shipments/packages?email_message_id=${encodeURIComponent(emailMessageId)}`);

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
        return gatewayClient.getPackage(id);
    }

    /**
     * Update a package
     */
    async updatePackage(id: string, packageData: Partial<PackageCreateRequest>): Promise<PackageResponse> { // Changed from number to string (UUID)
        return gatewayClient.updatePackage(id, packageData);
    }

    /**
     * Delete a package
     */
    async deletePackage(id: string): Promise<void> { // Changed from number to string (UUID)
        return gatewayClient.deletePackage(id);
    }

    /**
     * Refresh tracking information for a package
     */
    async refreshPackage(id: string): Promise<PackageRefreshResponse> { // Changed from number to string (UUID)
        return gatewayClient.refreshPackage(id);
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
        return gatewayClient.getTrackingEvents(packageId);
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
        return gatewayClient.request<Array<{
            id: string;
            event_date: string;
            status: PackageStatus;
            location?: string;
            description?: string;
            created_at: string;
        }>>(`/api/v1/shipments/events?email_message_id=${encodeURIComponent(emailMessageId)}`);
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
        return gatewayClient.createTrackingEvent(packageId, eventData);
    }
}

// Export a singleton instance
export const shipmentsClient = new ShipmentsClient();

// Export the class for testing
export default ShipmentsClient; 