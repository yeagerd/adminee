import { EmailMessage } from '@/types/office-service';
import { gatewayClient } from './gateway-client';

// Define proper types for shipment data
export interface SuggestedPackageData {
    tracking_number?: string;
    carrier?: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    estimated_delivery?: string;
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
    status: string;
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
    status: string;
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
    async getPackages(): Promise<{ data: PackageResponse[]; pagination: PaginationInfo }> {
        return gatewayClient.getPackages();
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
}

// Export a singleton instance
export const shipmentsClient = new ShipmentsClient();

// Export the class for testing
export default ShipmentsClient; 