import { EmailMessage } from '@/types/office-service';

// Types for shipments service
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
    suggested_package_data?: any;
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
    labels: any[];
}

class ShipmentsClient {
    private baseUrl: string;

    constructor() {
        // Use the gateway URL for now, will be updated when gateway is configured
        this.baseUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001';
    }

    private async makeRequest<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}/api/v1/shipments${endpoint}`;
        
        const defaultOptions: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            credentials: 'include', // Include cookies for authentication
        };

        const response = await fetch(url, {
            ...defaultOptions,
            ...options,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                errorData.detail || `HTTP error! status: ${response.status}`
            );
        }

        return response.json();
    }

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

        return this.makeRequest<EmailParseResponse>('/email-parser/parse', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    /**
     * Create a new package tracking entry
     */
    async createPackage(packageData: PackageCreateRequest): Promise<PackageResponse> {
        return this.makeRequest<PackageResponse>('/packages', {
            method: 'POST',
            body: JSON.stringify(packageData),
        });
    }

    /**
     * Get all packages for the current user
     */
    async getPackages(): Promise<{ data: PackageResponse[]; pagination: any }> {
        return this.makeRequest<{ data: PackageResponse[]; pagination: any }>('/packages');
    }

    /**
     * Get a specific package by ID
     */
    async getPackage(id: number): Promise<PackageResponse> {
        return this.makeRequest<PackageResponse>(`/packages/${id}`);
    }

    /**
     * Update a package
     */
    async updatePackage(id: number, packageData: Partial<PackageCreateRequest>): Promise<PackageResponse> {
        return this.makeRequest<PackageResponse>(`/packages/${id}`, {
            method: 'PUT',
            body: JSON.stringify(packageData),
        });
    }

    /**
     * Delete a package
     */
    async deletePackage(id: number): Promise<void> {
        return this.makeRequest<void>(`/packages/${id}`, {
            method: 'DELETE',
        });
    }

    /**
     * Refresh tracking information for a package
     */
    async refreshPackage(id: number): Promise<any> {
        return this.makeRequest<any>(`/packages/${id}/refresh`, {
            method: 'POST',
        });
    }
}

// Export a singleton instance
export const shipmentsClient = new ShipmentsClient();

// Export the class for testing
export default ShipmentsClient; 