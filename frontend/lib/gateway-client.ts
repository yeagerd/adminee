import {
    ApiResponse,
    CalendarEventsResponse,
    EmailFolder,
    GetEmailsResponse,
} from '@/types/office-service';
import { getSession } from 'next-auth/react';
import { IntegrationStatus } from './constants';
import { env, validateClientEnv } from './env';
import { PackageStatus } from './package-status';

interface GatewayClientOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: unknown;
    headers?: Record<string, string>;
}

export class GatewayClient {
    constructor() {
        // Validate client-side environment variables on instantiation
        validateClientEnv();
    }

    private async getAuthHeaders(): Promise<Record<string, string>> {
        const session = await getSession();

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        // Add JWT token if available
        if (session?.accessToken) {
            headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        return headers;
    }

    public async request<T>(endpoint: string, options: GatewayClientOptions = {}): Promise<T> {
        const { method = 'GET', body, headers: customHeaders } = options;

        const authHeaders = await this.getAuthHeaders();
        const headers = { ...authHeaders, ...customHeaders };

        const config: RequestInit = {
            method,
            headers,
        };

        if (body && method !== 'GET') {
            config.body = JSON.stringify(body);
        }

        const url = `${env.GATEWAY_URL}${endpoint}`;

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Gateway Error (${response.status}): ${errorText}`;

                // Try to parse JSON error response
                try {
                    const errorJson = JSON.parse(errorText);
                    if (errorJson.message) {
                        errorMessage = errorJson.message;
                    }
                } catch {
                    // If not JSON, use the raw text
                }

                throw new Error(errorMessage);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            }

            return response.text() as T;
        } catch (error) {
            console.error('Gateway Client Error:', error);
            throw error;
        }
    }

    // Chat Service
    async chat(message: string, threadId?: string, userContext?: Record<string, unknown>) {
        return this.request('/api/v1/chat/completions', {
            method: 'POST',
            body: {
                message,
                thread_id: threadId,
                user_context: userContext,
            },
        });
    }

    async chatStream(message: string, threadId?: string, userContext?: Record<string, unknown>, signal?: AbortSignal): Promise<ReadableStream> {
        const session = await getSession();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (session?.accessToken) {
            headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        const response = await fetch(`${env.GATEWAY_URL}/api/v1/chat/completions/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message,
                thread_id: threadId,
                user_context: userContext,
            }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Gateway Stream Error (${response.status}): ${errorText}`);
        }

        return response.body!;
    }

    async getChatHistory(threadId: string) {
        return this.request(`/api/v1/chat/threads/${threadId}/history`);
    }

    async getChatThreads(limit = 20, offset = 0) {
        const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
        return this.request(`/api/v1/chat/threads?${params.toString()}`);
    }

    // User Service
    async getCurrentUser() {
        return this.request('/api/v1/users/me');
    }

    async updateUser(userData: Record<string, unknown>) {
        return this.request('/api/v1/users/me', {
            method: 'PUT',
            body: userData,
        });
    }

    async getUserPreferences() {
        return this.request('/api/v1/users/me/preferences');
    }

    async updateUserPreferences(preferences: Record<string, unknown>) {
        return this.request('/api/v1/users/me/preferences', {
            method: 'PUT',
            body: preferences,
        });
    }

    // Integration Management
    async getIntegrations(): Promise<IntegrationListResponse> {
        return this.request<IntegrationListResponse>('/api/v1/users/me/integrations');
    }

    async startOAuthFlow(provider: string, scopes: string[]) {
        // Use a dedicated integration callback URL to avoid conflicts with NextAuth
        const redirectUri = `${window.location.origin}/integrations/callback`;

        return this.request('/api/v1/users/me/integrations/oauth/start', {
            method: 'POST',
            body: {
                provider,
                scopes,
                redirect_uri: redirectUri,
            },
        });
    }

    async completeOAuthFlow(provider: string, code: string, state: string): Promise<OAuthCallbackResponse> {
        return this.request<OAuthCallbackResponse>(`/api/v1/users/me/integrations/oauth/callback?provider=${provider}`, {
            method: 'POST',
            body: { code, state },
        });
    }

    async disconnectIntegration(provider: string) {
        return this.request(`/api/v1/users/me/integrations/${provider}`, {
            method: 'DELETE',
        });
    }

    async refreshIntegrationTokens(provider: string) {
        return this.request(`/api/v1/users/me/integrations/${provider}/refresh`, {
            method: 'PUT',
        });
    }

    async getProviderScopes(provider: string) {
        return this.request<{
            provider: string;
            scopes: Array<{
                name: string;
                description: string;
                required: boolean;
                sensitive: boolean;
            }>;
            default_scopes: string[];
        }>(`/api/v1/users/me/integrations/${provider}/scopes`);
    }

    // Office Service
    async getCalendarEvents(
        providers?: string[],
        limit: number = 50,
        start_date?: string,
        end_date?: string,
        calendar_ids?: string[],
        q?: string,
        time_zone: string = 'UTC',
        noCache?: boolean
    ) {
        const params = new URLSearchParams();
        if (providers && providers.length > 0) {
            providers.forEach(provider => params.append('providers', provider));
        }
        params.append('limit', limit.toString());
        if (start_date) params.append('start_date', start_date);
        if (end_date) params.append('end_date', end_date);
        if (calendar_ids && calendar_ids.length > 0) {
            calendar_ids.forEach(id => params.append('calendar_ids', id));
        }
        if (q) params.append('q', q);
        params.append('time_zone', time_zone);
        if (noCache) params.append('no_cache', 'true');

        return this.request<ApiResponse<CalendarEventsResponse>>(`/api/v1/calendar/events?${params.toString()}`);
    }

    async getEmails(
        providers: string[],
        limit?: number,
        offset?: number,
        noCache?: boolean,
        labels?: string[],
        folderId?: string
    ): Promise<ApiResponse<GetEmailsResponse>> {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());
        if (offset) params.append('offset', offset.toString());
        if (noCache) params.append('no_cache', 'true');

        // Add providers as a list
        providers.forEach(provider => {
            params.append('providers', provider);
        });

        // Add labels for folder filtering
        if (labels && labels.length > 0) {
            labels.forEach(label => {
                params.append('labels', label);
            });
        }

        // Add folder_id for folder-specific fetching
        if (folderId) {
            params.append('folder_id', folderId);
        }

        return this.request<ApiResponse<GetEmailsResponse>>(`/api/v1/email/messages?${params.toString()}`);
    }

    async getEmailFolders(
        providers?: string[],
        noCache?: boolean
    ): Promise<ApiResponse<{ folders: EmailFolder[] }>> {
        const params = new URLSearchParams();
        if (noCache) params.append('no_cache', 'true');

        // Add providers as a list
        if (providers && providers.length > 0) {
            providers.forEach(provider => {
                params.append('providers', provider);
            });
        }

        return this.request<ApiResponse<{ folders: EmailFolder[] }>>(`/api/v1/email/folders?${params.toString()}`);
    }

    async getFiles(provider: string, path?: string) {
        const params = new URLSearchParams();
        if (path) params.append('path', path);

        return this.request(`/api/v1/files?provider=${provider}&${params.toString()}`);
    }

    // Draft Management
    async listDrafts(filters?: { type?: string | string[]; status?: string | string[]; search?: string; }): Promise<DraftListResponse> {
        const params = new URLSearchParams();
        if (filters?.type) {
            if (Array.isArray(filters.type)) {
                filters.type.forEach(t => params.append('draft_type', t));
            } else {
                params.append('draft_type', filters.type);
            }
        }
        if (filters?.status) {
            if (Array.isArray(filters.status)) {
                filters.status.forEach(s => params.append('status', s));
            } else {
                params.append('status', filters.status);
            }
        }
        if (filters?.search) params.append('search', filters.search);
        return this.request<DraftListResponse>(`/api/v1/drafts?${params.toString()}`);
    }

    async createDraft(draftData: { type: string; content: string; metadata?: Record<string, unknown>; threadId?: string; }): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>('/api/v1/drafts', {
            method: 'POST',
            body: draftData,
        });
    }

    async updateDraft(draftId: string, draftData: { content?: string; metadata?: Record<string, unknown>; status?: string; }): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>(`/api/v1/drafts/${draftId}`, {
            method: 'PUT',
            body: draftData,
        });
    }

    async deleteDraft(draftId: string): Promise<void> {
        return this.request<void>(`/api/v1/drafts/${draftId}`, {
            method: 'DELETE',
        });
    }

    async getDraft(draftId: string): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>(`/api/v1/drafts/${draftId}`);
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // WebSocket connection helper
    createWebSocketConnection(endpoint: string): WebSocket {
        const wsUrl = env.GATEWAY_URL.replace('http', 'ws');
        return new WebSocket(`${wsUrl}${endpoint}`);
    }

    // Meetings Service
    async listMeetingPolls(): Promise<MeetingPoll[]> {
        return this.request<MeetingPoll[]>('/api/v1/meetings/polls');
    }

    async getMeetingPoll(pollId: string): Promise<MeetingPoll> {
        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`);
    }

    async createMeetingPoll(pollData: MeetingPollCreate): Promise<MeetingPoll> {
        return this.request<MeetingPoll>('/api/v1/meetings/polls', {
            method: 'POST',
            body: pollData,
        });
    }

    async updateMeetingPoll(pollId: string, pollData: MeetingPollUpdate): Promise<MeetingPoll> {
        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`, {
            method: 'PUT',
            body: pollData,
        });
    }

    async deleteMeetingPoll(pollId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}`, {
            method: 'DELETE',
        });
    }

    async sendMeetingInvitations(pollId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}/send-invitations`, {
            method: 'POST',
        });
    }

    async resendMeetingInvitation(pollId: string, participantId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}/participants/${participantId}/resend-invitation`, {
            method: 'POST',
        });
    }

    async addMeetingParticipant(pollId: string, email: string, name: string): Promise<PollParticipant> {
        return this.request<PollParticipant>(`/api/v1/meetings/polls/${pollId}/participants`, {
            method: 'POST',
            body: { email, name },
        });
    }

    // Shipments Service
    async parseEmail(emailData: { subject: string; sender: string; body: string; content_type: string }): Promise<{
        is_shipment_email: boolean;
        detected_carrier?: string;
        tracking_numbers: Array<{
            tracking_number: string;
            carrier?: string;
            confidence: number;
            source: string;
        }>;
        confidence: number;
        detected_from: string;
        suggested_package_data?: {
            tracking_number?: string;
            carrier?: string;
            recipient_name?: string;
            shipper_name?: string;
            package_description?: string;
            order_number?: string;
            estimated_delivery?: string;
        };
    }> {
        return this.request('/api/v1/shipments/events/from-email', {
            method: 'POST',
            body: emailData,
        });
    }

    async createPackage(packageData: {
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
    }): Promise<{
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
    }> {
        return this.request('/api/v1/shipments/packages', {
            method: 'POST',
            body: packageData,
        });
    }

    async getPackages(): Promise<{
        data: Array<{
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
        }>;
        pagination: {
            page: number;
            per_page: number;
            total: number;
            total_pages: number;
            has_next: boolean;
            has_prev: boolean;
        };
    }> {
        return this.request('/api/v1/shipments/packages');
    }

    async getPackage(id: number): Promise<{
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
    }> {
        return this.request(`/api/v1/shipments/packages/${id}`);
    }

    async updatePackage(id: number, packageData: Record<string, unknown>): Promise<{
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
    }> {
        return this.request(`/api/v1/shipments/packages/${id}`, {
            method: 'PUT',
            body: packageData,
        });
    }

    async deletePackage(id: number): Promise<void> {
        return this.request(`/api/v1/shipments/packages/${id}`, {
            method: 'DELETE',
        });
    }

    async refreshPackage(id: number): Promise<{
        success: boolean;
        message: string;
        updated_data?: Partial<{
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
        }>;
    }> {
        return this.request(`/api/v1/shipments/packages/${id}/refresh`, {
            method: 'POST',
        });
    }

    async getTrackingEvents(packageId: number): Promise<Array<{
        id: number;
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }>> {
        return this.request(`/api/v1/shipments/packages/${packageId}/events`);
    }

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
        return this.request(`/api/v1/shipments/packages/${packageId}/events`, {
            method: 'POST',
            body: eventData,
        });
    }

    async collectShipmentData(data: {
        user_id: string;
        email_message_id: string;
        original_email_data: Record<string, unknown>;
        auto_detected_data: Record<string, unknown>;
        user_corrected_data: Record<string, unknown>;
        detection_confidence: number;
        correction_reason?: string;
        consent_given: boolean;
    }): Promise<{
        success: boolean;
        collection_id: string;
        timestamp: string;
        message: string;
    }> {
        return this.request('/api/v1/shipments/packages/collect-data', {
            method: 'POST',
            body: data,
        });
    }
}

// Export singleton instance
export const gatewayClient = new GatewayClient();

// Export types for TypeScript
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

// Meeting Poll Types
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
}

export interface PollResponse {
    id: string;
    participant_id: string;
    time_slot_id: string;
    response: string;
    comment?: string;
    created_at: string;
    updated_at: string;
}

export interface TimeSlot {
    id: string;
    start_time: string;
    end_time: string;
    timezone: string;
    is_available: boolean;
}

export interface PollParticipant {
    id: string;
    email: string;
    name?: string;
    status: string;
    invited_at: string;
    responded_at?: string;
    reminder_sent_count: number;
    response_token: string;
}

export interface MeetingPollCreate {
    title: string;
    description?: string;
    duration_minutes: number;
    location?: string;
    meeting_type: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
    reveal_participants?: boolean;
    time_slots: TimeSlotCreate[];
    participants: PollParticipantCreate[];
}

export interface TimeSlotCreate {
    start_time: string;
    end_time: string;
    timezone: string;
}

export interface PollParticipantCreate {
    email: string;
    name?: string;
    poll_id?: string;
    response_token?: string;
}

export interface PollParticipant {
    id: string;
    email: string;
    name?: string;
    status: string;
    invited_at: string;
    responded_at?: string;
    reminder_sent_count: number;
    response_token: string;
}

export interface MeetingPollUpdate {
    title?: string;
    description?: string;
    duration_minutes?: number;
    location?: string;
    meeting_type?: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
}

export default gatewayClient;