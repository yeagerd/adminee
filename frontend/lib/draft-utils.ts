import { chatApi, officeApi } from '@/api';
import type { 
    UserDraftResponse, 
    UserDraftListResponse,
    UserDraftRequest 
} from '@/types/api/chat';
import { Draft, DraftStatus, DraftType } from '@/types/draft';

// Import DraftData types from chat interface
type DraftEmail = {
    id?: string;
    type: "email";
    to?: string;
    cc?: string;
    bcc?: string;
    subject?: string;
    body?: string;
    thread_id: string;
    created_at: string;
    updated_at?: string;
};

type DraftCalendarEvent = {
    id?: string;
    type: "calendar_event";
    title?: string;
    start_time?: string;
    end_time?: string;
    location?: string;
    description?: string;
    attendees?: string[];
    thread_id: string;
    created_at: string;
    updated_at?: string;
};

type DraftCalendarChange = {
    id?: string;
    type: "calendar_change";
    event_id?: string;
    change_type?: string;
    new_title?: string;
    new_start_time?: string;
    new_end_time?: string;
    new_attendees?: string;
    new_location?: string;
    new_description?: string;
    thread_id: string;
    created_at: string;
    updated_at?: string;
};

type DraftData = DraftEmail | DraftCalendarEvent | DraftCalendarChange;

// Simple utility functions
export function formatDraftDate(date: string): string {
    return new Date(date).toLocaleString();
}

export function filterDraftsBySearch(drafts: Draft[], search: string): Draft[] {
    if (!search) return drafts;
    return drafts.filter((draft: Draft) =>
        draft.content?.toLowerCase().includes(search.toLowerCase()) ||
        draft.metadata?.subject?.toLowerCase().includes(search.toLowerCase())
    );
}

export function sortDraftsByUpdated(drafts: Draft[]): Draft[] {
    return [...drafts].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}

// Convert DraftData from chat interface to Draft type
export function convertDraftDataToDraft(draftData: DraftData, userId: string): Draft {
    let content = '';
    let metadata: Record<string, unknown> = {};
    let type: DraftType = 'email';

    if (draftData.type === 'email') {
        type = 'email';
        content = draftData.body || '';
        metadata = {
            subject: draftData.subject,
            recipients: draftData.to ? draftData.to.split(',').map((s: string) => s.trim()).filter((s: string) => s) : [],
            cc: draftData.cc ? draftData.cc.split(',').map((s: string) => s.trim()).filter((s: string) => s) : [],
            bcc: draftData.bcc ? draftData.bcc.split(',').map((s: string) => s.trim()).filter((s: string) => s) : [],
        };
    } else if (draftData.type === 'calendar_event') {
        type = 'calendar';
        content = draftData.description || '';
        metadata = {
            title: draftData.title,
            startTime: draftData.start_time,
            endTime: draftData.end_time,
            location: draftData.location,
            attendees: draftData.attendees || [],
        };
    } else if (draftData.type === 'calendar_change') {
        type = 'calendar';
        content = draftData.new_description || '';
        metadata = {
            title: draftData.new_title,
            startTime: draftData.new_start_time,
            endTime: draftData.new_end_time,
            location: draftData.new_location,
            attendees: draftData.new_attendees || [],
        };
    } else {
        // For any unhandled types, preserve the original type instead of defaulting to 'email'
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const genericData = draftData as any;
        type = genericData.type as DraftType;
        content = genericData.description || genericData.body || '';
        metadata = {
            title: genericData.title,
            // Add any other generic metadata that might be available
        };
    }

    return {
        id: draftData.id ? draftData.id : `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type,
        status: 'draft',
        content,
        metadata,
        isAIGenerated: true,
        createdAt: draftData.created_at,
        updatedAt: draftData.updated_at || draftData.created_at,
        userId,
        threadId: draftData.thread_id || undefined,
    };
}

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

// Data mapping utility
export function mapDraftFromApi(apiDraft: UserDraftResponse): Draft {
    return {
        id: apiDraft.id,
        type: apiDraft.type as DraftType,
        status: apiDraft.status as DraftStatus,
        content: apiDraft.content,
        metadata: apiDraft.metadata ?? {},
        isAIGenerated: false, // This field is not in the generated type, defaulting to false
        createdAt: apiDraft.created_at,
        updatedAt: apiDraft.updated_at,
        userId: apiDraft.user_id,
        threadId: apiDraft.thread_id ?? undefined,
    };
}

// Draft CRUD operations
export async function createDraft(request: CreateDraftRequest): Promise<Draft> {
    const data = await chatApi.createDraft(request);
    return mapDraftFromApi(data);
}

export async function updateDraft(draftId: string, request: UpdateDraftRequest): Promise<Draft> {
    const data = await chatApi.updateDraft(draftId, request);
    return mapDraftFromApi(data);
}

export async function deleteDraft(draftId: string): Promise<void> {
    await chatApi.deleteDraft(draftId);
}

export async function getDraft(draftId: string): Promise<Draft> {
    const data = await chatApi.getDraft(draftId);
    return mapDraftFromApi(data);
}

export async function listDrafts(filters?: { type?: DraftType; status?: DraftStatus; search?: string }): Promise<{
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
        drafts: data.drafts.map((draft) => mapDraftFromApi(draft)),
        totalCount: data.total_count,
        hasMore: data.has_more,
    };
}

// Email provider draft operations
export async function createEmailProviderDraft(args: CreateEmailProviderDraftArgs) {
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

export async function updateEmailProviderDraft(args: UpdateEmailProviderDraftArgs) {
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

export async function deleteEmailProviderDraft(draftId: string, provider: 'google' | 'microsoft') {
    return officeApi.deleteEmailDraft(draftId, provider);
}

export async function listProviderDraftsForThread(threadId: string) {
    return officeApi.listThreadDrafts(threadId);
}

// Draft actions
export async function sendDraft(draft: Draft): Promise<DraftActionResult> {
    try {
        // For emails, prefer sending via provider using provider draft context if available
        if (draft.type === 'email') {
            const provider = draft.metadata.provider as 'google' | 'microsoft' | undefined;
            const providerDraftId = draft.metadata.providerDraftId as string | undefined;

            // If we have a provider, let the send endpoint know to avoid account mismatches
            const result = await officeApi.sendEmail({
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
                    await updateDraft(draft.id, { status: 'sent' });
                }
                // Best-effort cleanup of provider draft to avoid orphans
                if (provider && providerDraftId) {
                    try {
                        await deleteEmailProviderDraft(providerDraftId, provider);
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
        if (draft.type === 'calendar' || draft.type === 'calendar_event' || draft.type === 'calendar_change') {
            // Handle calendar event creation
            const startTime = typeof draft.metadata.startTime === 'function' ? draft.metadata.startTime() : draft.metadata.startTime;
            const endTime = typeof draft.metadata.endTime === 'function' ? draft.metadata.endTime() : draft.metadata.endTime;

            // Process attendees: handle arrays, strings, and comma-separated strings
            let processedAttendees: string[] = [];
            if (draft.metadata.attendees) {
                if (Array.isArray(draft.metadata.attendees)) {
                    processedAttendees = draft.metadata.attendees;
                } else if (typeof draft.metadata.attendees === 'string') {
                    // Handle comma-separated string or single email
                    processedAttendees = (draft.metadata.attendees as string).split(',').map((s: string) => s.trim()).filter((s: string) => s);
                }
            }

            const result = await officeApi.createCalendarEventWithValidation({
                title: draft.metadata.title || 'Untitled Event',
                startTime: startTime || new Date().toISOString(),
                endTime: endTime || new Date(Date.now() + 60 * 60 * 1000).toISOString(),
                location: draft.metadata.location,
                description: draft.content,
                attendees: processedAttendees,
            });

            if (result.success) {
                // Update draft status to 'sent' or 'ready' depending on type
                if (/^\d+$/.test(draft.id)) {
                    await updateDraft(draft.id, { status: 'sent' });
                }
            }

            return {
                success: result.success,
                result: result.eventId ? { eventId: result.eventId } : undefined,
                error: result.error,
                draftId: draft.id,
            };
        } else if (draft.type === 'document') {
            // Handle document creation
            const result = await officeApi.saveDocument({
                title: draft.metadata.title || 'Untitled Document',
                content: draft.content,
                type: 'document',
            });

            if (result.success) {
                // Update draft status to 'ready'
                if (/^\d+$/.test(draft.id)) {
                    await updateDraft(draft.id, { status: 'ready' });
                }
            }

            return {
                success: result.success,
                result: result.documentId ? { documentId: result.documentId } : undefined,
                error: result.error,
                draftId: draft.id,
            };
        }

        // Default fallback for unknown types
        return {
            success: false,
            error: `Unsupported draft type: ${draft.type}`,
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

export async function saveDraft(draft: Draft): Promise<DraftActionResult> {
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
                    const resp = await updateEmailProviderDraft({
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

                    const resp = await createEmailProviderDraft({
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
                            await updateDraft(draft.id, { metadata: { ...draft.metadata, providerDraftId } });
                        } else {
                            // Local draft: update in-place
                            draft.metadata = { ...draft.metadata, providerDraftId };
                        }
                    }
                }
            }
            // Update chat draft status too
            if (/^\d+$/.test(draft.id)) {
                await updateDraft(draft.id, { status: 'ready' });
            }
            return { success: true, draftId: draft.id };
        }

        // For documents and calendar, use previous logic
        if (draft.type === 'document') {
            const result = await officeApi.saveDocument({
                title: draft.metadata.title || 'Untitled Document',
                content: draft.content,
                type: 'document',
            });
            if (result.success) {
                if (/^\d+$/.test(draft.id)) {
                    await updateDraft(draft.id, { status: 'ready' });
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
            await updateDraft(draft.id, { status: 'ready' });
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

export async function discardDraft(draftId: string, provider?: 'google' | 'microsoft', providerDraftId?: string): Promise<boolean> {
    try {
        if (provider && providerDraftId) {
            try {
                await deleteEmailProviderDraft(providerDraftId, provider);
            } catch (e) {
                console.warn('Failed to delete provider draft:', e);
            }
        }
        await deleteDraft(draftId);
        return true;
    } catch (error) {
        console.error('Failed to discard draft:', error);
        return false;
    }
}