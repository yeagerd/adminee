import { getSession } from 'next-auth/react';
import { getUserId } from '../../lib/session-utils';
import type {
    ContactCreateResponse,
    ContactDeleteResponse,
    ContactList,
    ContactUpdateResponse,
    CreateCalendarEventRequest,
    EmailDraftResponse,
    EmailFolderList,
    EmailMessageList,
    EmailThreadList,
    SendEmailResponse,
    TypedApiResponse_CalendarEventResponse_,
    TypedApiResponse_List_CalendarEvent__
} from '../../types/api/office';
import { BulkActionType } from '@/types';
import { GatewayClient } from './gateway-client';

export class OfficeClient extends GatewayClient {
    // Calendar Service
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

        return this.request<TypedApiResponse_List_CalendarEvent__>(`/api/v1/calendar/events?${params.toString()}`);
    }

    async createCalendarEvent(payload: CreateCalendarEventRequest) {
        const session = await getSession();
        const userId = getUserId(session);

        if (!userId) {
            throw new Error('User ID is required for calendar event operations');
        }

        const params = new URLSearchParams();
        params.append('user_id', userId);

        return this.request<TypedApiResponse_CalendarEventResponse_>(`/api/v1/calendar/events?${params.toString()}`, {
            method: 'POST',
            body: payload,
        });
    }

    async updateCalendarEvent(eventId: string, payload: CreateCalendarEventRequest) {
        const session = await getSession();
        const userId = getUserId(session);

        if (!userId) {
            throw new Error('User ID is required for calendar event operations');
        }

        const params = new URLSearchParams();
        params.append('user_id', userId);

        return this.request<TypedApiResponse_CalendarEventResponse_>(`/api/v1/calendar/events/${encodeURIComponent(eventId)}?${params.toString()}`, {
            method: 'PUT',
            body: payload,
        });
    }

    async deleteCalendarEvent(eventId: string) {
        const session = await getSession();
        const userId = getUserId(session);

        if (!userId) {
            throw new Error('User ID is required for calendar event operations');
        }

        const params = new URLSearchParams();
        params.append('user_id', userId);

        return this.request<TypedApiResponse_CalendarEventResponse_>(`/api/v1/calendar/events/${encodeURIComponent(eventId)}?${params.toString()}`, {
            method: 'DELETE',
        });
    }

    // Email Service
    async getEmails(
        providers: string[],
        limit?: number,
        offset?: number,
        noCache?: boolean,
        labels?: string[],
        folderId?: string
    ): Promise<EmailMessageList> {
        const params = new URLSearchParams();

        providers.forEach(provider => params.append('providers', provider));

        if (limit) params.append('limit', limit.toString());
        if (offset) params.append('offset', offset.toString());
        if (noCache) params.append('no_cache', 'true');
        if (labels) labels.forEach(label => params.append('labels', label));
        if (folderId) params.append('folder_id', folderId);

        return this.request<EmailMessageList>(`/api/v1/email/messages?${params.toString()}`);
    }

    async getThreads(
        providers?: string[],
        limit?: number,
        includeBody?: boolean,
        labels?: string[],
        folderId?: string,
        q?: string,
        pageToken?: string,
        noCache?: boolean
    ): Promise<EmailThreadList> {
        const params = new URLSearchParams();

        if (providers) providers.forEach(provider => params.append('providers', provider));
        if (limit) params.append('limit', limit.toString());
        if (includeBody) params.append('include_body', 'true');
        if (labels) labels.forEach(label => params.append('labels', label));
        if (folderId) params.append('folder_id', folderId);
        if (q) params.append('q', q);
        if (pageToken) params.append('page_token', pageToken);
        if (noCache) params.append('no_cache', 'true');

        return this.request<EmailThreadList>(`/api/v1/email/threads?${params.toString()}`);
    }

    async getThread(
        threadId: string,
        includeBody?: boolean,
        noCache?: boolean
    ): Promise<EmailThreadList> {
        const params = new URLSearchParams();

        if (includeBody) params.append('include_body', 'true');
        if (noCache) params.append('no_cache', 'true');

        return this.request<EmailThreadList>(`/api/v1/email/threads/${threadId}?${params.toString()}`);
    }

    // Provider Email Drafts (Office Service)
    async createEmailDraft(payload: {
        action?: 'new' | 'reply' | 'reply_all' | 'forward';
        to?: { email: string; name?: string }[];
        cc?: { email: string; name?: string }[];
        bcc?: { email: string; name?: string }[];
        subject?: string;
        body?: string;
        thread_id?: string;
        reply_to_message_id?: string;
        provider?: 'google' | 'microsoft';
    }): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>(`/api/v1/email/drafts`, {
            method: 'POST',
            body: {
                action: payload.action || 'new',
                to: payload.to,
                cc: payload.cc,
                bcc: payload.bcc,
                subject: payload.subject,
                body: payload.body,
                thread_id: payload.thread_id,
                reply_to_message_id: payload.reply_to_message_id,
                provider: payload.provider,
            },
        });
    }

    async updateEmailDraft(draftId: string, payload: {
        to?: { email: string; name?: string }[];
        cc?: { email: string; name?: string }[];
        bcc?: { email: string; name?: string }[];
        subject?: string;
        body?: string;
        provider: 'google' | 'microsoft';
    }): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>(`/api/v1/email/drafts/${draftId}`, {
            method: 'PUT',
            body: {
                to: payload.to,
                cc: payload.cc,
                bcc: payload.bcc,
                subject: payload.subject,
                body: payload.body,
                provider: payload.provider,
            },
        });
    }

    async deleteEmailDraft(draftId: string, provider: 'google' | 'microsoft'): Promise<EmailDraftResponse> {
        const params = new URLSearchParams();
        params.append('provider', provider);
        return this.request<EmailDraftResponse>(`/api/v1/email/drafts/${draftId}?${params.toString()}`, { method: 'DELETE' });
    }

    async listThreadDrafts(threadId: string): Promise<EmailDraftResponse> {
        return this.request<EmailDraftResponse>(`/api/v1/email/threads/${threadId}/drafts`);
    }

    async getMessageThread(
        messageId: string,
        includeBody?: boolean,
        noCache?: boolean
    ): Promise<EmailThreadList> {
        const params = new URLSearchParams();

        if (includeBody) params.append('include_body', 'true');
        if (noCache) params.append('no_cache', 'true');

        return this.request<EmailThreadList>(`/api/v1/email/messages/${messageId}/thread?${params.toString()}`);
    }

    // Bulk email operations
    async bulkAction(
        actionType: BulkActionType,
        emailIds: string[],
        providers?: string[]
    ): Promise<{
        success: boolean;
        data?: {
            success_count: number;
            error_count: number;
            errors?: Array<{
                email_id: string;
                error: string;
            }>;
        };
        error?: string;
    }> {
        return this.request('/api/v1/email/bulk-action', {
            method: 'POST',
            body: {
                action_type: actionType,
                email_ids: emailIds,
                providers: providers || ['google', 'microsoft']
            },
        });
    }

    async getEmailFolders(
        providers?: string[],
        noCache?: boolean
    ): Promise<EmailFolderList> {
        const params = new URLSearchParams();
        if (noCache) params.append('no_cache', 'true');

        // Add providers as a list
        if (providers && providers.length > 0) {
            providers.forEach(provider => {
                params.append('providers', provider);
            });
        }

        return this.request<EmailFolderList>(`/api/v1/email/folders?${params.toString()}`);
    }

    async getFiles(provider: string, path?: string) {
        const params = new URLSearchParams();
        if (path) params.append('path', path);

        return this.request(`/api/v1/files?provider=${provider}&${params.toString()}`);
    }

    // Contacts Service
    async getContacts(providers?: string[], limit?: number, q?: string, company?: string, noCache?: boolean): Promise<ContactList> {
        const params = new URLSearchParams();
        if (providers) providers.forEach(p => params.append('providers', p));
        if (limit) params.append('limit', String(limit));
        if (q) params.append('q', q);
        if (company) params.append('company', company);
        if (noCache) params.append('no_cache', 'true');
        return this.request<ContactList>(`/api/v1/contacts?${params.toString()}`);
    }

    async updateContact(contactId: string, payload: Partial<ContactList>): Promise<ContactUpdateResponse> {
        return this.request<ContactUpdateResponse>(`/api/v1/contacts/${contactId}`, {
            method: 'PUT',
            body: payload,
        });
    }

    async createContact(payload: Partial<ContactList> & { provider?: 'google' | 'microsoft' }): Promise<ContactCreateResponse> {
        return this.request<ContactCreateResponse>(`/api/v1/contacts`, {
            method: 'POST',
            body: payload,
        });
    }

    async deleteContact(contactId: string): Promise<ContactDeleteResponse> {
        return this.request<ContactDeleteResponse>(`/api/v1/contacts/${contactId}`, {
            method: 'DELETE',
        });
    }

    // Additional methods for office integration
    async sendEmail(request: {
        to: string[];
        cc?: string[];
        bcc?: string[];
        subject: string;
        body: string;
        reply_to_message_id?: string;
        provider?: 'google' | 'microsoft';
    }): Promise<{ success: boolean; messageId?: string; error?: string }> {
        try {
            const result = await this.request<SendEmailResponse>('/api/v1/email/send', {
                method: 'POST',
                body: request,
            });

            // Ensure proper response structure validation
            if (!result || !result.success) {
                throw new Error('Invalid response structure from email sending');
            }

            // Extract messageId from the data if available
            const messageId = result.data && typeof result.data === 'object' && result.data !== null
                ? (result.data as any).messageId
                : undefined;
            return { success: true, messageId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async saveDocument(request: {
        title: string;
        content: string;
        type: 'document' | 'spreadsheet' | 'presentation';
        provider?: 'google' | 'microsoft';
    }): Promise<{ success: boolean; documentId?: string; error?: string }> {
        try {
            const result = await this.request<{ documentId: string }>('/api/v1/documents', {
                method: 'POST',
                body: request,
            });

            // Ensure proper response structure validation
            if (!result || !result.documentId) {
                throw new Error('Invalid response structure from document saving');
            }

            return { success: true, documentId: result.documentId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async createCalendarEventWithValidation(request: {
        title: string;
        startTime: string;
        endTime: string;
        location?: string;
        description?: string;
        attendees?: string[];
    }): Promise<{ success: boolean; eventId?: string; error?: string }> {
        try {
            const result = await this.createCalendarEvent({
                title: request.title,
                start_time: request.startTime,
                end_time: request.endTime,
                location: request.location,
                description: request.description,
                attendees: request.attendees?.map(email => ({ email, name: undefined })),
            });

            // Ensure proper response structure validation
            if (!result || !result.data || !result.data.event_id) {
                throw new Error('Invalid response structure from calendar event creation');
            }

            return { success: true, eventId: result.data.event_id };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

}
