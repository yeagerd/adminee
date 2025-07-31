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
    id: number;
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
     * Get a specific package by ID
     */
    async getPackage(id: number): Promise<PackageResponse> {
        return gatewayClient.getPackage(id);
    }

    /**
     * Update a package
     */
    async updatePackage(id: number, packageData: Partial<PackageCreateRequest>): Promise<PackageResponse> {
        return gatewayClient.updatePackage(id, packageData);
    }

    /**
     * Delete a package
     */
    async deletePackage(id: number): Promise<void> {
        return gatewayClient.deletePackage(id);
    }

    /**
     * Refresh tracking information for a package
     */
    async refreshPackage(id: number): Promise<PackageRefreshResponse> {
        return gatewayClient.refreshPackage(id);
    }

    /**
     * Get tracking events for a package
     */
    async getTrackingEvents(packageId: number): Promise<Array<{
        id: number;
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }>> {
        return gatewayClient.getTrackingEvents(packageId);
    }

    /**
     * Create a new tracking event for a package
     */
    async createTrackingEvent(packageId: number, eventData: {
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
    }): Promise<{
        id: number;
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