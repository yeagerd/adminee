// Unified Calendar Event interface matching office service schema
export interface EmailAddress {
    email: string;
    name?: string;
}

export interface CalendarEvent {
    id: string;
    calendar_id: string;
    title: string;
    description?: string;
    start_time: string; // ISO datetime string
    end_time: string; // ISO datetime string
    all_day: boolean;
    location?: string;
    attendees: EmailAddress[];
    organizer?: EmailAddress;
    status: string; // confirmed, tentative, cancelled
    visibility: string; // default, public, private
    // Provenance Information
    provider: 'google' | 'microsoft';
    provider_event_id: string;
    account_email: string;
    account_name?: string;
    calendar_name: string;
    created_at: string; // ISO datetime string
    updated_at: string; // ISO datetime string
}

export interface CalendarEventsResponse {
    events: CalendarEvent[];
    total_count: number;
    providers_used: string[];
    provider_errors?: Record<string, string>;
    date_range: {
        start_date: string;
        end_date: string;
        time_zone: string;
    };
    request_metadata: {
        user_id: string;
        providers_requested: string[];
        limit: number;
        calendar_ids?: string[];
    };
}

export interface ApiResponse<T = any> {
    success: boolean;
    data: T;
    cache_hit?: boolean;
    provider_used?: 'google' | 'microsoft';
    request_id?: string;
}

// Request interfaces for creating/updating events
export interface CreateCalendarEventRequest {
    title: string;
    description?: string;
    start_time: string; // ISO datetime string
    end_time: string; // ISO datetime string
    all_day?: boolean;
    location?: string;
    attendees?: EmailAddress[];
    calendar_id?: string;
    provider?: string;
    visibility?: string;
    status?: string;
} 