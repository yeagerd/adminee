import { chatApi, officeApi } from '@/api';
import type { DraftApiResponse } from '@/api/types/common';
import { officeIntegration } from '@/lib/office-integration';
import { Draft, DraftStatus, DraftType } from '@/types/draft';

export interface CreateDraftRequest {
    type: DraftType;
    content: string;
    metadata?: Record<string, unknown>;
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
        const data = await chatApi.createDraft({
            type: request.type,
            content: request.content,
            metadata: request.metadata,
            threadId: request.threadId,
        });

        return this.mapDraftFromApi(data as DraftApiResponse);
    }

    async createEmailProviderDraft(args: CreateEmailProviderDraftArgs) {
        const resp = await officeApi.createEmailDraft({
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
        const resp = await officeApi.updateEmailDraft(args.draftId, {
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
        return officeApi.deleteEmailDraft(draftId, provider);
    }

    async listProviderDraftsForThread(threadId: string) {
        return officeApi.listThreadDrafts(threadId);
    }

    async updateDraft(draftId: string, request: UpdateDraftRequest): Promise<Draft> {
        const data = await chatApi.updateDraft(draftId, {
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
            await chatApi.deleteDraft(draftId);
            return true;
        } else {
            console.log('[DraftService] draftId is not integer, treating as local/unsaved draft. No backend call.');
            // Local/unsaved draft, just remove from UI/state
            return true;
        }
    }

    async getDraft(draftId: string): Promise<Draft> {
        const data = await chatApi.getDraft(draftId);
        return this.mapDraftFromApi(data as DraftApiResponse);
    }

    async listDrafts(filters?: { type?: DraftType; status?: DraftStatus; search?: string }): Promise<{
        drafts: Draft[];
        totalCount: number;
        hasMore: boolean;
    }> {
        const data = await chatApi.listDrafts({
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
            // For emails, prefer sending via provider using provider draft context if available
            if (draft.type === 'email') {
                const provider = draft.metadata.provider as 'google' | 'microsoft' | undefined;
                const providerDraftId = draft.metadata.providerDraftId as string | undefined;

                // If we have a provider, let the send endpoint know to avoid account mismatches
                const result = await officeIntegration.sendEmail({
                    to: draft.metadata.recipients || [],
                    cc: Array.isArray(draft.metadata.cc) ? draft.metadata.cc : (draft.metadata.cc ? [draft.metadata.cc] : []),
                    bcc: Array.isArray(draft.metadata.bcc) ? draft.metadata.bcc : (draft.metadata.bcc ? [draft.metadata.bcc] : []),
                    subject: draft.metadata.subject || 'No Subject',
                    body: draft.content,
                    reply_to_message_id: draft.metadata.replyToMessageId,
                    provider,
                });

                if (result.success) {
                    // Mark app draft as sent
                    if (/^\d+$/.test(draft.id)) {
                        await this.updateDraft(draft.id, { status: 'sent' });
                    }
                    // Best-effort cleanup of provider draft to avoid orphans
                    if (provider && providerDraftId) {
                        try {
                            await this.deleteEmailProviderDraft(providerDraftId, provider);
                        } catch (e) {
                            console.warn('Failed to delete provider draft post-send:', e);
                        }
                    }
                }

                return {
                    success: result.success,
                    result: result.messageId ? { messageId: result.messageId } : undefined,
                    error: result.error,
                    draftId: draft.id,
                };
            }

            // Non-email fallback: Execute through integration
            const result = await officeIntegration.executeDraftAction(draft);

            if (result.success) {
                // Update draft status to 'sent' or 'ready' depending on type
                if (/^\d+$/.test(draft.id)) {
                    await this.updateDraft(draft.id, { status: draft.type === 'document' ? 'ready' : 'sent' });
                }
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
                const to = (draft.metadata.recipients || []).map((email: string) => ({ email }));
                const cc = (draft.metadata.cc || []).map((email: string) => ({ email }));
                const bcc = (draft.metadata.bcc || []).map((email: string) => ({ email }));
                const subject = draft.metadata.subject || '';
                const body = draft.content || '';

                // Only attempt provider draft operations if provider is known
                if (provider) {
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
                        // Determine action based on thread context and reply metadata
                        let action: 'new' | 'reply' | 'reply_all' | 'forward' = 'new';
                        const hasThread = Boolean(draft.threadId);
                        const hasReplyMessage = Boolean(draft.metadata.replyToMessageId);
                        if (hasReplyMessage) {
                            // Heuristic: if there are multiple recipients or any CC, treat as reply_all
                            const recipientCount = (draft.metadata.recipients?.length || 0);
                            const ccCount = (draft.metadata.cc?.length || 0);
                            if (ccCount > 0 || recipientCount > 1) {
                                action = 'reply_all';
                            } else {
                                action = 'reply';
                            }
                        } else if (hasThread) {
                            // If in a thread without a specific message to reply to, default to reply
                            action = 'reply';
                        }
                        // If subject indicates forwarding, override
                        const subj = subject.toLowerCase();
                        if (subj.startsWith('fwd:') || subj.startsWith('fwd')) {
                            action = 'forward';
                        }

                        const resp = await this.createEmailProviderDraft({
                            action,
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
                            if (/^\d+$/.test(draft.id)) {
                                await this.updateDraft(draft.id, { metadata: { ...draft.metadata, providerDraftId } });
                            } else {
                                // Local draft: update in-place
                                draft.metadata = { ...draft.metadata, providerDraftId };
                            }
                        }
                    }
                }
                // Update chat draft status too
                if (/^\d+$/.test(draft.id)) {
                    await this.updateDraft(draft.id, { status: 'ready' });
                }
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
                    if (/^\d+$/.test(draft.id)) {
                        await this.updateDraft(draft.id, { status: 'ready' });
                    }
                }
                return {
                    success: result.success,
                    result: result.documentId,
                    error: result.error,
                    draftId: draft.id,
                };
            }

            if (/^\d+$/.test(draft.id)) {
                await this.updateDraft(draft.id, { status: 'ready' });
            }
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