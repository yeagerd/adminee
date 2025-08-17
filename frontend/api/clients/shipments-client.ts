import { 
    PackageOut,
    PackageCreate,
    PackageUpdate,
    PackageStatus,
    EmailParseRequest,
    EmailParseResponse,
    ParsedTrackingInfo,
    DataCollectionRequest,
    DataCollectionResponse,
    LabelOut,
    LabelCreate,
    LabelUpdate,
    TrackingEventOut,
    TrackingEventCreate,
    CarrierConfigOut
} from '../../types/api/shipments';
import { GatewayClient } from './gateway-client';

// Legacy types for backward compatibility - these should be removed once all components are updated
export type { PackageStatus } from '../../types/api/shipments';
export type { EmailParseRequest, EmailParseResponse, ParsedTrackingInfo } from '../../types/api/shipments';
export type { DataCollectionRequest, DataCollectionResponse } from '../../types/api/shipments';

// Additional types that may not be in the generated schema yet
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

export interface CursorPaginationInfo {
    next_cursor?: string;
    prev_cursor?: string;
    has_next: boolean;
    has_prev: boolean;
    limit: number;
}

export interface PackageRefreshResponse {
    success: boolean;
    message: string;
    updated_data?: Partial<PackageOut>;
}

export class ShipmentsClient extends GatewayClient {
    // Shipments Service
    async parseEmail(emailData: EmailParseRequest): Promise<EmailParseResponse> {
        return this.request('/api/v1/shipments/events/from-email', {
            method: 'POST',
            body: emailData,
        });
    }

    async createPackage(packageData: PackageCreate): Promise<PackageOut> {
        return this.request('/api/v1/shipments/packages', {
            method: 'POST',
            body: packageData,
        });
    }

    async getPackages(params?: {
        cursor?: string;
        limit?: number;
        direction?: 'next' | 'prev';
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
        date_range?: string;
    }): Promise<{ packages: PackageOut[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        const queryParams = new URLSearchParams();

        // Cursor-based pagination parameters
        if (params?.cursor) {
            queryParams.append('cursor', params.cursor);
        }
        if (params?.limit) {
            queryParams.append('limit', params.limit.toString());
        }
        if (params?.direction) {
            queryParams.append('direction', params.direction);
        }

        // Filter parameters
        if (params?.tracking_number) {
            queryParams.append('tracking_number', params.tracking_number);
        }
        if (params?.carrier) {
            queryParams.append('carrier', params.carrier);
        }
        if (params?.status) {
            queryParams.append('status', params.status);
        }
        if (params?.user_id) {
            queryParams.append('user_id', params.user_id);
        }
        if (params?.date_range) {
            queryParams.append('date_range', params.date_range);
        }

        const url = queryParams.toString() ? `/api/v1/shipments/packages?${queryParams.toString()}` : '/api/v1/shipments/packages';
        return this.request(url);
    }

    async getPackage(id: string): Promise<PackageOut> {
        return this.request(`/api/v1/shipments/packages/${id}`);
    }

    async updatePackage(id: string, packageData: PackageUpdate): Promise<PackageOut> {
        return this.request(`/api/v1/shipments/packages/${id}`, {
            method: 'PUT',
            body: packageData,
        });
    }

    async deletePackage(id: string): Promise<void> {
        return this.request(`/api/v1/shipments/packages/${id}`, {
            method: 'DELETE',
        });
    }

    async refreshPackage(id: string): Promise<PackageRefreshResponse> {
        return this.request(`/api/v1/shipments/packages/${id}/refresh`, {
            method: 'POST',
        });
    }

    async getTrackingEvents(packageId: string): Promise<Array<TrackingEventOut>> {
        return this.request(`/api/v1/shipments/packages/${packageId}/events`);
    }

    async createTrackingEvent(packageId: string, eventData: TrackingEventCreate): Promise<TrackingEventOut> {
        return this.request(`/api/v1/shipments/packages/${packageId}/events`, {
            method: 'POST',
            body: eventData,
        });
    }

    async getEventsByEmail(emailMessageId: string): Promise<Array<TrackingEventOut>> {
        return this.request(`/api/v1/shipments/events?email_message_id=${encodeURIComponent(emailMessageId)}`);
    }

    async deleteTrackingEvent(packageId: string, eventId: string): Promise<void> {
        return this.request(`/api/v1/shipments/packages/${packageId}/events/${eventId}`, {
            method: 'DELETE',
        });
    }

    async collectShipmentData(data: DataCollectionRequest): Promise<DataCollectionResponse> {
        return this.request('/api/v1/shipments/packages/collect-data', {
            method: 'POST',
            body: data,
        });
    }

    // Helper methods for pagination
    async getNextPage(cursor: string, limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageOut[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            cursor,
            limit,
            direction: 'next',
            ...filters
        });
    }

    async getPrevPage(cursor: string, limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageOut[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            cursor,
            limit,
            direction: 'prev',
            ...filters
        });
    }

    async getFirstPage(limit?: number, filters?: {
        tracking_number?: string;
        carrier?: string;
        status?: string;
        user_id?: string;
    }): Promise<{ packages: PackageOut[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean; limit: number }> {
        return this.getPackages({
            limit,
            direction: 'next',
            ...filters
        });
    }

    // Helper method to check if a package exists
    async checkPackageExists(trackingNumber: string, carrier?: string): Promise<PackageOut | null> {
        const params: { tracking_number: string; carrier?: string } = {
            tracking_number: trackingNumber
        };

        // Always include carrier in the request if it's provided, even if it's 'unknown'
        if (carrier) {
            params.carrier = carrier;
        }

        const response = await this.getPackages(params);

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
            const matchingPackage = response.packages.find((pkg: PackageOut) => pkg.carrier === carrier);
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

    // Helper method to get package by email message ID
    async getPackageByEmail(emailMessageId: string): Promise<PackageOut | null> {
        try {
            const response = await this.request<{ data: PackageOut[] }>(`/api/v1/shipments/packages?email_message_id=${encodeURIComponent(emailMessageId)}`);

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
}
