import { Draft } from '@/types/draft';

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

    constructor(config: OfficeIntegrationConfig) {
        this.config = config;
    }

    async sendEmail(request: EmailSendRequest): Promise<{ success: boolean; messageId?: string; error?: string }> {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/email/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...request,
                    provider: this.config.provider,
                }),
            });

            if (!response.ok) {
                throw new Error(`Failed to send email: ${response.statusText}`);
            }

            const result = await response.json();
            return { success: true, messageId: result.messageId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async createCalendarEvent(request: CalendarEventRequest): Promise<{ success: boolean; eventId?: string; error?: string }> {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/calendar/events`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...request,
                    provider: this.config.provider,
                }),
            });

            if (!response.ok) {
                throw new Error(`Failed to create calendar event: ${response.statusText}`);
            }

            const result = await response.json();
            return { success: true, eventId: result.eventId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async saveDocument(request: DocumentSaveRequest): Promise<{ success: boolean; documentId?: string; error?: string }> {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/documents`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...request,
                    provider: this.config.provider,
                }),
            });

            if (!response.ok) {
                throw new Error(`Failed to save document: ${response.statusText}`);
            }

            const result = await response.json();
            return { success: true, documentId: result.documentId };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
    }

    async executeDraftAction(draft: Draft): Promise<{ success: boolean; result?: any; error?: string }> {
        switch (draft.type) {
            case 'email':
                return this.sendEmail({
                    to: draft.metadata.recipients || [],
                    cc: draft.metadata.cc,
                    bcc: draft.metadata.bcc,
                    subject: draft.metadata.subject || 'No Subject',
                    body: draft.content,
                });

            case 'calendar':
                return this.createCalendarEvent({
                    title: draft.metadata.title || 'New Event',
                    startTime: draft.metadata.startTime || new Date().toISOString(),
                    endTime: draft.metadata.endTime || new Date(Date.now() + 3600000).toISOString(),
                    location: draft.metadata.location,
                    description: draft.content,
                    attendees: draft.metadata.attendees,
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
    apiBaseUrl: process.env.NEXT_PUBLIC_OFFICE_SERVICE_URL || 'http://localhost:8001',
}); 