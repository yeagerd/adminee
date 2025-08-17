import { 
    CreatePublicBookingRequest,
    SuccessResponse
} from '../../types/api/meetings';
import { GatewayClient } from './gateway-client';

// Legacy types for backward compatibility - these should be removed once all components are updated
export interface CreateBookingLinkData {
    title: string;
    description: string;
    duration: number;
    buffer_before: number;
    buffer_after: number;
    max_per_day: number;
    max_per_week: number;
    advance_days: number;
    max_advance_days: number;
    business_hours: Record<string, { start: string; end: string; enabled: boolean }>;
    holiday_exclusions: string[];
    last_minute_cutoff: number;
    template_name?: string;
    questions?: Array<{ id: string; label: string; required: boolean; type: string }>;
    emailFollowup?: boolean;
    is_single_use?: boolean;
    recipient_email?: string;
    recipient_name?: string;
    expires_in_days?: number;
}

export interface OneTimeLinkData {
    recipient_email: string;
    recipient_name: string;
    expires_in_days: number;
}

export interface BookingLinkSettings {
    title?: string;
    description?: string;
    duration?: number;
    buffer_before?: number;
    buffer_after?: number;
    max_per_day?: number;
    max_per_week?: number;
    advance_days?: number;
    max_advance_days?: number;
    business_hours?: Record<string, { start: string; end: string; enabled: boolean }>;
    holiday_exclusions?: string[];
    last_minute_cutoff?: number;
}

export interface BookingLink {
    id: string;
    owner_user_id: string;
    slug: string;
    is_active: boolean;
    settings: BookingLinkSettings | null;
    template_id: string | null;
    created_at: string;
    updated_at: string;
    total_views: number;
    total_bookings: number;
    conversion_rate: string;
}

export interface Booking {
    id: string;
    link_id: string;
    one_time_link_id: string | null;
    start_at: string;
    end_at: string;
    attendee_email: string;
    answers: Record<string, string> | null;
    calendar_event_id: string | null;
    created_at: string;
}

export interface AnalyticsData {
    link_id: string;
    views: number;
    bookings: number;
    conversion_rate: string;
    last_viewed: string | null;
    top_referrers: string[];
    recent_activity: Array<{ type: string; timestamp: string | null }>;
}

export interface CreateBookingLinkResponse {
    data: {
        id: string;
        slug: string;
        public_url: string;
        message: string;
    };
}

export interface ListBookingLinksResponse {
    data: BookingLink[];
    total: number;
}

export interface ToggleBookingLinkResponse {
    data: {
        is_active: boolean;
    };
}

export interface DuplicateBookingLinkResponse {
    data: {
        slug: string;
    };
}

export interface CreateOneTimeLinkResponse {
    data: {
        token: string;
        public_url: string;
        expires_at: string;
        message: string;
    };
}

export interface PublicAvailabilityResponse {
    data: {
        slots: Array<{ start: string; end: string; available: boolean }>;
        duration: number;
        timezone: string;
    };
}

export interface CreatePublicBookingResponse {
    data: {
        id: string;
        message: string;
        calendar_event_id: string | null;
    };
}

export class BookingsClient extends GatewayClient {
    // Booking Link methods
    async createBookingLink(data: CreateBookingLinkData): Promise<CreateBookingLinkResponse> {
        return this.request('/api/v1/bookings/links', {
            method: 'POST',
            body: data,
        });
    }

    async listBookingLinks(): Promise<ListBookingLinksResponse> {
        return this.request('/api/v1/bookings/links');
    }

    async toggleBookingLink(linkId: string): Promise<ToggleBookingLinkResponse> {
        return this.request(`/api/v1/bookings/links/${linkId}/toggle`, {
            method: 'POST',
        });
    }

    async duplicateBookingLink(linkId: string): Promise<DuplicateBookingLinkResponse> {
        return this.request(`/api/v1/bookings/links/${linkId}/duplicate`, {
            method: 'POST',
        });
    }

    async createOneTimeLink(linkId: string, data: {
        recipient_email: string;
        recipient_name: string;
        expires_in_days: number;
    }): Promise<CreateOneTimeLinkResponse> {
        return this.request(`/api/v1/bookings/links/${linkId}/one-time`, {
            method: 'POST',
            body: data,
        });
    }

    async getPublicAvailability(token: string, duration: number = 30): Promise<PublicAvailabilityResponse> {
        return this.request(`/api/v1/bookings/public/${token}/availability?duration=${duration}`);
    }

    async createPublicBooking(token: string, bookingData: { start: string; end: string; attendeeEmail: string; answers?: Record<string, string> }): Promise<CreatePublicBookingResponse> {
        return this.request(`/api/v1/bookings/public/${token}/book`, {
            method: 'POST',
            body: bookingData,
        });
    }
}
