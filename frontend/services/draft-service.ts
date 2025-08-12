import { gatewayClient } from '@/lib/gateway-client';
import { officeIntegration } from '@/lib/office-integration';
import { Draft, DraftStatus, DraftType } from '@/types/draft';

export interface CreateDraftRequest {
    type: DraftType;
    content: string;
    metadata?: any;
    threadId?: string;
}

// Provider email draft helpers
export interface CreateEmailProviderDraftArgs {
    action?: 'new' | 'reply' | 'reply_all' | 'forward';
    provider: 'google' | 'microsoft';
    threadId?: string;
    replyToMessageId?: string;
    to?: { email: string; name?: string }[];
    cc?: { email: string; name?: string }[];
    bcc?: { email: string; name?: string }[];
    subject?: string;
    body?: string;
}

export interface UpdateEmailProviderDraftArgs {
    provider: 'google' | 'microsoft';
    draftId: string;
    to?: { email: string; name?: string }[];
    cc?: { email: string; name?: string }[];
    bcc?: { email: string; name?: string }[];
    subject?: string;
    body?: string;
}

export interface UpdateDraftRequest {
    content?: string;
    metadata?: any;
    status?: DraftStatus;
}

export interface DraftActionResult {
    success: boolean;
    result?: any;
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

        return this.mapDraftFromApi(data);
    }

    async createEmailProviderDraft(args: CreateEmailProviderDraftArgs) {
        const resp = await gatewayClient.createEmailDraft({
            action: args.action,
            to: args.to,
            cc: args.cc,
            bcc: args.bcc,
            subject: args.subject,
            body: args.body,
            thread_id: args.threadId,
            reply_to_message_id: args.replyToMessageId,
            provider: args.provider,
        });
        return resp;
    }

    async updateEmailProviderDraft(args: UpdateEmailProviderDraftArgs) {
        const resp = await gatewayClient.updateEmailDraft(args.draftId, {
            to: args.to,
            cc: args.cc,
            bcc: args.bcc,
            subject: args.subject,
            body: args.body,
            provider: args.provider,
        });
        return resp;
    }

    async deleteEmailProviderDraft(draftId: string, provider: 'google' | 'microsoft') {
        return gatewayClient.deleteEmailDraft(draftId, provider);
    }

    async listProviderDraftsForThread(threadId: string) {
        return gatewayClient.listThreadDrafts(threadId);
    }

    async updateDraft(draftId: string, request: UpdateDraftRequest): Promise<Draft> {
        const data = await gatewayClient.updateDraft(draftId, {
            content: request.content,
            metadata: request.metadata,
            status: request.status,
        });

        return this.mapDraftFromApi(data);
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
        return this.mapDraftFromApi(data);
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
            drafts: data.drafts.map((draft: any) => this.mapDraftFromApi(draft)),
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
            if (draft.type === 'email') {
                const provider = draft.metadata.provider as 'google' | 'microsoft' | undefined;
                if (!provider) {
                    return { success: false, error: 'Missing provider', draftId: draft.id };
                }
                const to = (draft.metadata.recipients || []).map((email: string) => ({ email }));
                const cc = (draft.metadata.cc || []).map((email: string) => ({ email }));
                const bcc = (draft.metadata.bcc || []).map((email: string) => ({ email }));
                const subject = draft.metadata.subject || '';
                const body = draft.content || '';

                if (draft.metadata.providerDraftId) {
                    const resp = await this.updateEmailProviderDraft({
                        provider,
                        draftId: draft.metadata.providerDraftId,
                        to,
                        cc,
                        bcc,
                        subject,
                        body,
                    });
                    if (!resp.success) {
                        return { success: false, error: resp.error?.message || 'Failed to update provider draft', draftId: draft.id };
                    }
                } else {
                    const resp = await this.createEmailProviderDraft({
                        action: 'new',
                        provider,
                        threadId: draft.threadId,
                        replyToMessageId: draft.metadata.replyToMessageId,
                        to,
                        cc,
                        bcc,
                        subject,
                        body,
                    });
                    if (!resp.success) {
                        return { success: false, error: resp.error?.message || 'Failed to create provider draft', draftId: draft.id };
                    }
                    let providerDraftId: string | undefined;
                    const dataObj = resp.data as { draft?: Record<string, unknown> } | { deleted?: boolean } | { drafts?: unknown[] } | undefined;
                    if (dataObj && 'draft' in dataObj) {
                        const draftObj = (dataObj as { draft?: Record<string, unknown> }).draft;
                        if (draftObj && typeof draftObj.id === 'string') {
                            providerDraftId = draftObj.id as string;
                        }
                    }
                    if (providerDraftId) {
                        await this.updateDraft(draft.id, { metadata: { ...draft.metadata, providerDraftId } });
                    }
                }
                // Update chat draft status too
                await this.updateDraft(draft.id, { status: 'ready' });
                return { success: true, draftId: draft.id };
            }

            // For documents and calendar, use previous logic
            if (draft.type === 'document') {
                const result = await officeIntegration.saveDocument({
                    title: draft.metadata.title || 'Untitled Document',
                    content: draft.content,
                    type: 'document',
                });
                if (result.success) {
                    await this.updateDraft(draft.id, { status: 'ready' });
                }
                return {
                    success: result.success,
                    result: result.documentId,
                    error: result.error,
                    draftId: draft.id,
                };
            }

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

    async discardDraft(draftId: string, provider?: 'google' | 'microsoft', providerDraftId?: string): Promise<boolean> {
        try {
            if (provider && providerDraftId) {
                try {
                    await this.deleteEmailProviderDraft(providerDraftId, provider);
                } catch (e) {
                    console.warn('Failed to delete provider draft:', e);
                }
            }
            await this.deleteDraft(draftId);
            return true;
        } catch (error) {
            console.error('Failed to discard draft:', error);
            return false;
        }
    }

    private mapDraftFromApi(apiDraft: any): Draft {
        return {
            id: apiDraft.id,
            type: apiDraft.type,
            status: apiDraft.status,
            content: apiDraft.content,
            metadata: apiDraft.metadata,
            isAIGenerated: apiDraft.is_ai_generated ?? false,
            createdAt: apiDraft.created_at,
            updatedAt: apiDraft.updated_at,
            userId: apiDraft.user_id,
            threadId: apiDraft.thread_id,
        };
    }
}

// Default draft service instance
export const draftService = new DraftService(); 