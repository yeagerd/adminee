import { Draft } from '@/types/draft';
import { GatewayClient } from './gateway-client';

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
    private gatewayClient: GatewayClient;

    constructor(config: OfficeIntegrationConfig) {
        this.config = config;
        this.gatewayClient = new GatewayClient();
    }

    async sendEmail(request: EmailSendRequest): Promise<{ success: boolean; messageId?: string; error?: string }> {
        try {
            const result = await this.gatewayClient.request<{ messageId: string }>(
                '/api/email/send',
                {
                    method: 'POST',
                    body: {
                        ...request,
                        provider: this.config.provider,
                    },
                }
            );
            return { success: true, messageId: result.messageId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async createCalendarEvent(request: CalendarEventRequest): Promise<{ success: boolean; eventId?: string; error?: string }> {
        try {
            const result = await this.gatewayClient.request<{ eventId: string }>(
                '/api/calendar/events',
                {
                    method: 'POST',
                    body: {
                        ...request,
                        provider: this.config.provider,
                    },
                }
            );
            return { success: true, eventId: result.eventId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async saveDocument(request: DocumentSaveRequest): Promise<{ success: boolean; documentId?: string; error?: string }> {
        try {
            const result = await this.gatewayClient.request<{ documentId: string }>(
                '/api/documents',
                {
                    method: 'POST',
                    body: {
                        ...request,
                        provider: this.config.provider,
                    },
                }
            );
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
                    bcc: draft.metadata.bcc,
                    subject: draft.metadata.subject || 'No Subject',
                    body: draft.content,
                });

            case 'calendar':
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