import type { DraftApiResponse } from '@/lib/gateway-client';
import { gatewayClient } from '@/lib/gateway-client';
import { officeIntegration } from '@/lib/office-integration';
import { Draft, DraftStatus, DraftType } from '@/types/draft';

export interface CreateDraftRequest {
    type: DraftType;
    content: string;
    metadata?: Record<string, unknown>;
    threadId?: string;
}

export interface UpdateDraftRequest {
    content?: string;
    metadata?: Record<string, unknown>;
    status?: DraftStatus;
}

export interface DraftActionResult {
    success: boolean;
    result?: unknown;
    error?: string;
    draftId?: string;
}

export class DraftService {
    async createDraft(request: CreateDraftRequest): Promise<Draft> {
        const data = await gatewayClient.createDraft({
            type: request.type,
            content: request.content,
            metadata: request.metadata,
            threadId: request.threadId,
        });

        return this.mapDraftFromApi(data as DraftApiResponse);
    }

    async updateDraft(draftId: string, request: UpdateDraftRequest): Promise<Draft> {
        const data = await gatewayClient.updateDraft(draftId, {
            content: request.content,
            metadata: request.metadata,
            status: request.status,
        });

        return this.mapDraftFromApi(data as DraftApiResponse);
    }

    async deleteDraft(draftId: string): Promise<boolean> {
        // Add logging to debug deletion logic
        console.log('[DraftService] Attempting to delete draft:', draftId);
        // Only call backend if draftId is an integer
        if (/^\d+$/.test(draftId)) {
            console.log('[DraftService] draftId is integer, calling backend to delete.');
            await gatewayClient.deleteDraft(draftId);
            return true;
        } else {
            console.log('[DraftService] draftId is not integer, treating as local/unsaved draft. No backend call.');
            // Local/unsaved draft, just remove from UI/state
            return true;
        }
    }

    async getDraft(draftId: string): Promise<Draft> {
        const data = await gatewayClient.getDraft(draftId);
        return this.mapDraftFromApi(data as DraftApiResponse);
    }

    async listDrafts(filters?: { type?: DraftType; status?: DraftStatus; search?: string }): Promise<{
        drafts: Draft[];
        totalCount: number;
        hasMore: boolean;
    }> {
        const data = await gatewayClient.listDrafts({
            type: filters?.type,
            status: filters?.status,
            search: filters?.search,
        });

        return {
            drafts: data.drafts.map((draft) => this.mapDraftFromApi(draft as DraftApiResponse)),
            totalCount: data.total_count,
            hasMore: data.has_more,
        };
    }

    async sendDraft(draft: Draft): Promise<DraftActionResult> {
        try {
            // Execute the draft action through office integration
            const result = await officeIntegration.executeDraftAction(draft);

            if (result.success) {
                // Update draft status to 'sent'
                await this.updateDraft(draft.id, { status: 'sent' });
            }

            return {
                success: result.success,
                result: result.result,
                error: result.error,
                draftId: draft.id,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error',
                draftId: draft.id,
            };
        }
    }

    async saveDraft(draft: Draft): Promise<DraftActionResult> {
        try {
            // For documents, save to cloud storage
            if (draft.type === 'document') {
                const result = await officeIntegration.saveDocument({
                    title: draft.metadata.title || 'Untitled Document',
                    content: draft.content,
                    type: 'document',
                });

                if (result.success) {
                    // Update draft status to 'ready'
                    await this.updateDraft(draft.id, { status: 'ready' });
                }

                return {
                    success: result.success,
                    result: result.documentId,
                    error: result.error,
                    draftId: draft.id,
                };
            }

            // For other types, just update the draft
            await this.updateDraft(draft.id, { status: 'ready' });
            return {
                success: true,
                draftId: draft.id,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error',
                draftId: draft.id,
            };
        }
    }

    async discardDraft(draftId: string): Promise<boolean> {
        try {
            await this.deleteDraft(draftId);
            return true;
        } catch (error) {
            console.error('Failed to discard draft:', error);
            return false;
        }
    }

    private mapDraftFromApi(apiDraft: DraftApiResponse): Draft {
        const obj = apiDraft as DraftApiResponse;
        return {
            id: obj.id as string,
            type: obj.type as DraftType,
            status: obj.status as DraftStatus,
            content: obj.content as string,
            metadata: (obj.metadata as Record<string, unknown>) ?? {},
            isAIGenerated: (obj.is_ai_generated as boolean | undefined) ?? false,
            createdAt: obj.created_at as string,
            updatedAt: obj.updated_at as string,
            userId: obj.user_id as string,
            threadId: obj.thread_id as string | undefined,
        };
    }
}

// Default draft service instance
export const draftService = new DraftService(); 