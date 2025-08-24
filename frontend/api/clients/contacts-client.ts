import type {
    Contact,
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactStatsResponse,
    EmailContactSearchResult,
    EmailContactUpdate,
} from '../../types/api/contacts';
import { GatewayClient } from './gateway-client';

export class ContactsClient extends GatewayClient {
    /**
     * Get contacts for the current user with optional filtering
     */
    async getContacts(
        limit: number = 100,
        offset: number = 0,
        tags?: string[],
        source_services?: string[],
        query?: string
    ): Promise<ContactListResponse> {
        const params = new URLSearchParams();
        params.append('limit', limit.toString());
        params.append('offset', offset.toString());
        
        if (tags && tags.length > 0) {
            tags.forEach(tag => params.append('tags', tag));
        }
        
        if (source_services && source_services.length > 0) {
            source_services.forEach(service => params.append('source_services', service));
        }
        
        if (query) {
            params.append('query', query);
        }

        return this.request<ContactListResponse>(`/api/v1/contacts/me?${params.toString()}`);
    }

    /**
     * Search contacts for the current user
     */
    async searchContacts(
        query: string,
        limit: number = 20,
        tags?: string[],
        source_services?: string[]
    ): Promise<EmailContactSearchResult[]> {
        const params = new URLSearchParams();
        params.append('query', query);
        params.append('limit', limit.toString());
        
        if (tags && tags.length > 0) {
            tags.forEach(tag => params.append('tags', tag));
        }
        
        if (source_services && source_services.length > 0) {
            source_services.forEach(service => params.append('source_services', service));
        }

        return this.request<EmailContactSearchResult[]>(`/api/v1/contacts/me/search?${params.toString()}`);
    }

    /**
     * Create a new contact
     */
    async createContact(contactData: ContactCreate): Promise<ContactResponse> {
        return this.request<ContactResponse>('/api/v1/contacts/me', {
            method: 'POST',
            body: contactData,
        });
    }

    /**
     * Update an existing contact
     */
    async updateContact(id: string, contactData: EmailContactUpdate): Promise<ContactResponse> {
        return this.request<ContactResponse>(`/api/v1/contacts/me/${id}`, {
            method: 'PUT',
            body: contactData,
        });
    }

    /**
     * Delete a contact
     */
    async deleteContact(id: string): Promise<{ success: boolean; message?: string }> {
        return this.request<{ success: boolean; message?: string }>(`/api/v1/contacts/me/${id}`, {
            method: 'DELETE',
        });
    }

    /**
     * Get contact statistics
     */
    async getContactStats(): Promise<ContactStatsResponse> {
        return this.request<ContactStatsResponse>('/api/v1/contacts/me/stats');
    }

    /**
     * Get a specific contact by ID
     */
    async getContact(id: string): Promise<ContactResponse> {
        return this.request<ContactResponse>(`/api/v1/contacts/me/${id}`);
    }
}
