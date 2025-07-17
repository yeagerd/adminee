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

// Unified Email Message interface matching office service schema
export interface EmailMessage {
    id: string;
    thread_id?: string;
    subject?: string;
    snippet?: string;
    body_text?: string;
    body_html?: string;
    from_address?: EmailAddress;
    to_addresses: EmailAddress[];
    cc_addresses: EmailAddress[];
    bcc_addresses: EmailAddress[];
    date: string; // ISO datetime string
    labels: string[];
    is_read: boolean;
    has_attachments: boolean;
    provider: 'google' | 'microsoft';
    provider_message_id: string;
    account_email: string;
    account_name?: string;
}

export interface EmailThread {
    id: string;
    subject?: string;
    emails: EmailMessage[];
    participant_count: number;
    last_message_date: string; // ISO datetime string
    is_read: boolean;
    providers: ('google' | 'microsoft')[];
}

export interface EmailFilters {
    query?: string;
    [key: string]: any;
} 