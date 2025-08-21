import { env } from '../../lib/env';
import {
    ChatRequest,
    ChatResponse,
    DeleteUserDraftResponse,
    UserDraftListResponse,
    UserDraftRequest,
    UserDraftResponse
} from '../../types/api/chat';
import { GatewayClient } from './gateway-client';

export class ChatClient extends GatewayClient {
    // Chat Service
    async chat(request: ChatRequest): Promise<ChatResponse> {
        return this.request<ChatResponse>('/api/v1/chat/completions', {
            method: 'POST',
            body: request,
        });
    }

    async chatStream(request: ChatRequest, signal?: AbortSignal): Promise<ReadableStream> {
        // Get authentication headers from the base class
        const authHeaders = await this.getAuthHeaders();

        const response = await fetch(`${this.getGatewayUrl()}/api/v1/chat/completions/stream`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(request),
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
    async listDrafts(filters?: { type?: string | string[]; status?: string | string[]; search?: string; }): Promise<UserDraftListResponse> {
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
        return this.request<UserDraftListResponse>(`/api/v1/drafts?${params.toString()}`);
    }

    async createDraft(draftData: UserDraftRequest): Promise<UserDraftResponse> {
        return this.request<UserDraftResponse>('/api/v1/drafts', {
            method: 'POST',
            body: draftData,
        });
    }

    async updateDraft(draftId: string, draftData: Partial<UserDraftRequest>): Promise<UserDraftResponse> {
        return this.request<UserDraftResponse>(`/api/v1/drafts/${draftId}`, {
            method: 'PUT',
            body: draftData,
        });
    }

    async deleteDraft(draftId: string): Promise<DeleteUserDraftResponse> {
        return this.request<DeleteUserDraftResponse>(`/api/v1/drafts/${draftId}`, {
            method: 'DELETE',
        });
    }

    async getDraft(draftId: string): Promise<UserDraftResponse> {
        return this.request<UserDraftResponse>(`/api/v1/drafts/${draftId}`);
    }

    // Helper method for gateway URL - use the validated env from base class
    private getGatewayUrl(): string {
        return env.GATEWAY_URL;
    }
}
