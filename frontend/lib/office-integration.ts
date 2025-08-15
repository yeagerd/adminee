import { Draft } from '@/types/draft';
import { OfficeClient } from '@/api/clients/office-client';

export interface OfficeIntegrationConfig {
    provider: 'google' | 'microsoft';
    apiBaseUrl: string;
}

export interface EmailSendRequest {
    to: string[];
    cc?: string[];
    bcc?: string[];
    subject: string;
    body: string;
    reply_to_message_id?: string;
    provider?: 'google' | 'microsoft';
}

export interface CalendarEventRequest {
    title: string;
    startTime: string;
    endTime: string;
    location?: string;
    description?: string;
    attendees?: string[];
}

export interface DocumentSaveRequest {
    title: string;
    content: string;
    type: 'document' | 'spreadsheet' | 'presentation';
}

export class OfficeIntegrationService {
    private config: OfficeIntegrationConfig;
    private officeClient: OfficeClient;

    constructor(config: OfficeIntegrationConfig) {
        this.config = config;
        this.officeClient = new OfficeClient();
    }

    async sendEmail(request: EmailSendRequest): Promise<{ success: boolean; messageId?: string; error?: string }> {
        try {
            const result = await this.officeClient.sendEmail({
                ...request,
                provider: request.provider ?? this.config.provider,
            });
            
            // Ensure proper response structure validation
            if (!result || !result.messageId) {
                throw new Error('Invalid response structure from email sending');
            }
            
            return { success: true, messageId: result.messageId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async createCalendarEvent(request: CalendarEventRequest): Promise<{ success: boolean; eventId?: string; error?: string }> {
        try {
            const result = await this.officeClient.createCalendarEvent({
                title: request.title,
                start_time: request.startTime,
                end_time: request.endTime,
                location: request.location,
                description: request.description,
                attendees: request.attendees?.map(email => ({ email, name: undefined })),
                // Remove provider field as it's not part of CreateCalendarEventRequest interface
                // The provider is handled by the backend based on user's connected accounts
            });
            
            // Ensure proper response structure validation
            if (!result || !result.data || !result.data.id) {
                throw new Error('Invalid response structure from calendar event creation');
            }
            
            return { success: true, eventId: result.data.id };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async saveDocument(request: DocumentSaveRequest): Promise<{ success: boolean; documentId?: string; error?: string }> {
        try {
            const result = await this.officeClient.saveDocument({
                ...request,
                provider: this.config.provider,
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

    async executeDraftAction(draft: Draft): Promise<{ success: boolean; result?: Record<string, unknown>; error?: string }> {
        switch (draft.type) {
            case 'email':
                return this.sendEmail({
                    to: draft.metadata.recipients || [],
                    cc: Array.isArray(draft.metadata.cc) ? draft.metadata.cc : (draft.metadata.cc ? [draft.metadata.cc] : []),
                    bcc: Array.isArray(draft.metadata.bcc) ? draft.metadata.bcc : (draft.metadata.bcc ? [draft.metadata.bcc] : []),
                    subject: draft.metadata.subject || 'No Subject',
                    body: draft.content,
                    reply_to_message_id: draft.metadata.replyToMessageId,
                    provider: draft.metadata.provider,
                });

            case 'calendar':
            case 'calendar_event':
            case 'calendar_change':
                return this.createCalendarEvent({
                    title: draft.metadata.title || 'New Event',
                    startTime: typeof draft.metadata.startTime === 'function' ? draft.metadata.startTime() : draft.metadata.startTime || new Date().toISOString(),
                    endTime: typeof draft.metadata.endTime === 'function' ? draft.metadata.endTime() : draft.metadata.endTime || new Date(Date.now() + 3600000).toISOString(),
                    location: draft.metadata.location,
                    description: draft.content,
                    attendees: Array.isArray(draft.metadata.attendees) ? draft.metadata.attendees : (draft.metadata.attendees ? [draft.metadata.attendees] : []),
                });

            case 'document':
                return this.saveDocument({
                    title: draft.metadata.title || 'Untitled Document',
                    content: draft.content,
                    type: 'document',
                });

            default:
                return { success: false, error: `Unsupported draft type: ${draft.type}` };
        }
    }
}

// Default office integration instance
export const officeIntegration = new OfficeIntegrationService({
    provider: 'google', // Will be set based on user preferences
    apiBaseUrl: process.env.NEXT_PUBLIC_OFFICE_SERVICE_URL || 'http://localhost:8003',
}); 