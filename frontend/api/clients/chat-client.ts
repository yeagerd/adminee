import { ApiResponse, DraftApiResponse, DraftListResponse, EmailDraftResponse } from '../types/common';
import { GatewayClient } from './gateway-client';

export class ChatClient extends GatewayClient {
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
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        const response = await fetch(`${this.getGatewayUrl()}/api/v1/chat/completions/stream`, {
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

    // Helper method for gateway URL
    private getGatewayUrl(): string {
        // Access the environment variable directly for the stream method
        return process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001';
    }

    // Email Provider Draft Methods
    async createEmailDraft(draftData: {
        action?: 'new' | 'reply' | 'reply_all' | 'forward';
        to?: { email: string; name?: string }[];
        cc?: { email: string; name?: string }[];
        bcc?: { email: string; name?: string }[];
        subject?: string;
        body?: string;
        thread_id?: string;
        reply_to_message_id?: string;
        provider: 'google' | 'microsoft';
    }): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>('/api/v1/chat/email-drafts', {
            method: 'POST',
            body: draftData,
        });
    }

    async updateEmailDraft(draftId: string, draftData: {
        to?: { email: string; name?: string }[];
        cc?: { email: string; name?: string }[];
        bcc?: { email: string; name?: string }[];
        subject?: string;
        body?: string;
        provider: 'google' | 'microsoft';
    }): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>(`/api/v1/chat/email-drafts/${encodeURIComponent(draftId)}`, {
            method: 'PUT',
            body: draftData,
        });
    }

    async deleteEmailDraft(draftId: string, provider: 'google' | 'microsoft'): Promise<void> {
        const params = new URLSearchParams({ provider });
        return this.request<void>(`/api/v1/chat/email-drafts/${encodeURIComponent(draftId)}`, {
            method: 'DELETE',
        });
    }

    async listThreadDrafts(threadId: string): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>(`/api/v1/chat/threads/${encodeURIComponent(threadId)}/drafts`);
    }
}
