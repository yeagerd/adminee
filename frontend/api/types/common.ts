// Import generated types from OpenAPI schemas
export type { ErrorResponse, BrieflyAPIError } from '../../types/api/common';

export interface ApiResponse<T = unknown> {
    success: boolean;
    data: T;
    cache_hit?: boolean;
    provider_used?: 'google' | 'microsoft';
    request_id?: string;
}

export interface EmailAddress {
    email: string;
    name?: string;
}

export type IntegrationStatus = 'ACTIVE' | 'INACTIVE' | 'ERROR' | 'PENDING' | 'EXPIRED';

export interface Integration {
    id: number;
    user_id: string;
    provider: string;
    status: IntegrationStatus;
    scopes: string[];
    external_user_id?: string;
    external_email?: string;
    external_name?: string;
    has_access_token: boolean;
    has_refresh_token: boolean;
    token_expires_at?: string;
    token_created_at?: string;
    last_sync_at?: string;
    last_error?: string;
    error_count: number;
    created_at: string;
    updated_at: string;
}

export interface IntegrationListResponse {
    integrations: Integration[];
    total: number;
    active_count: number;
    error_count: number;
}

export interface User {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    profile_image_url?: string;
    onboarding_completed: boolean;
    onboarding_step?: string;
}

export interface OAuthStartResponse {
    authorization_url: string;
    state: string;
    expires_at: string;
    requested_scopes: string[];
}

export interface OAuthCallbackResponse {
    success: boolean;
    integration_id?: number;
    provider: string;
    status: string;
    scopes: string[];
    external_user_info?: Record<string, unknown>;
    error?: string;
}

// Legacy draft types - these should be replaced with generated types from chat service
export interface DraftApiResponse {
    id: string;
    type: string;
    status: string;
    content: string;
    metadata: Record<string, unknown>;
    is_ai_generated?: boolean;
    created_at: string;
    updated_at: string;
    user_id: string;
    thread_id?: string;
}

export interface DraftListResponse {
    drafts: DraftApiResponse[];
    total_count: number;
    has_more: boolean;
}

// Bulk action types enum
export enum BulkActionType {
    ARCHIVE = 'archive',
    DELETE = 'delete',
    SNOOZE = 'snooze',
    MARK_READ = 'mark_read',
    MARK_UNREAD = 'mark_unread'
}

// Email Draft Response Types
export interface EmailDraftResponse {
    success: boolean;
    data?: {
        provider?: 'google' | 'microsoft';
        draft?: Record<string, unknown>;
        drafts?: unknown[];
        deleted?: boolean;
    };
    error?: {
        message?: string;
    };
    request_id: string;
}

// Legacy meeting poll types - these should be replaced with generated types from meetings service
export interface MeetingPoll {
    id: string;
    user_id: string;
    title: string;
    description?: string;
    duration_minutes: number;
    location?: string;
    meeting_type: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
    reveal_participants?: boolean;
    status: string;
    created_at: string;
    updated_at: string;
    poll_token: string;
    time_slots: TimeSlot[];
    participants: PollParticipant[];
    responses?: PollResponse[];
    scheduled_slot_id?: string;
    calendar_event_id?: string;
}

export interface PollParticipant {
    id: string;
    poll_id: string;
    email: string;
    name?: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface TimeSlot {
    id: string;
    poll_id: string;
    start_time: string;
    end_time: string;
    created_at: string;
}

export interface PollResponse {
    id: string;
    participant_id: string;
    time_slot_id: string;
    response: string;
    created_at: string;
    updated_at: string;
}
