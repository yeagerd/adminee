/**
 * Contacts Service API Client
 * 
 * Provides methods to interact with the Contacts Service API endpoints
 * for contact discovery, management, and search functionality.
 */

import { ApiClient } from './api-client';

export interface Contact {
  id: string;
  user_id: string;
  email_address: string;
  display_name?: string;
  given_name?: string;
  family_name?: string;
  event_counts: Record<string, ContactEventCount>;
  total_event_count: number;
  last_seen: string;
  first_seen: string;
  relevance_score: number;
  relevance_factors: Record<string, number>;
  source_services: string[];
  tags: string[];
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ContactEventCount {
  event_type: string;
  count: number;
  last_seen: string;
  first_seen: string;
}

export interface ContactCreate {
  user_id: string;
  email_address: string;
  display_name?: string;
  given_name?: string;
  family_name?: string;
  tags?: string[];
  notes?: string;
}

export interface ContactUpdate {
  display_name?: string;
  given_name?: string;
  family_name?: string;
  tags?: string[];
  notes?: string;
}

export interface ContactSearchRequest {
  query?: string;
  user_id: string;
  limit?: number;
  offset?: number;
  tags?: string[];
  source_services?: string[];
}

export interface ContactListResponse {
  contacts: Contact[];
  total: number;
  limit: number;
  offset: number;
  success: boolean;
  message?: string;
}

export interface ContactResponse {
  contact: Contact;
  success: boolean;
  message?: string;
}

export interface ContactStatsResponse {
  total_contacts: number;
  total_events: number;
  by_service: Record<string, number>;
  success: boolean;
  message?: string;
}

export class ContactsClient extends ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_CONTACTS_SERVICE_URL || 'http://localhost:8007') {
    super();
    this.baseUrl = baseUrl;
  }

  /**
   * List contacts for a user with optional filtering
   */
  async listContacts(
    userId: string,
    options: {
      limit?: number;
      offset?: number;
      tags?: string[];
      source_services?: string[];
    } = {}
  ): Promise<ContactListResponse> {
    const params = new URLSearchParams({
      user_id: userId,
      ...(options.limit && { limit: options.limit.toString() }),
      ...(options.offset && { offset: options.offset.toString() }),
      ...(options.tags && { tags: options.tags.join(',') }),
      ...(options.source_services && { source_services: options.source_services.join(',') }),
    });

    return this.get<ContactListResponse>(`${this.baseUrl}/v1/contacts?${params}`);
  }

  /**
   * Get a specific contact by ID
   */
  async getContact(contactId: string, userId: string): Promise<ContactResponse> {
    const params = new URLSearchParams({ user_id: userId });
    return this.get<ContactResponse>(`${this.baseUrl}/v1/contacts/${contactId}?${params}`);
  }

  /**
   * Create a new contact
   */
  async createContact(contactData: ContactCreate): Promise<ContactResponse> {
    return this.post<ContactResponse>(`${this.baseUrl}/v1/contacts`, contactData);
  }

  /**
   * Update an existing contact
   */
  async updateContact(
    contactId: string,
    userId: string,
    updateData: ContactUpdate
  ): Promise<ContactResponse> {
    const params = new URLSearchParams({ user_id: userId });
    return this.put<ContactResponse>(`${this.baseUrl}/v1/contacts/${contactId}?${params}`, updateData);
  }

  /**
   * Delete a contact
   */
  async deleteContact(contactId: string, userId: string): Promise<{ success: boolean; message: string }> {
    const params = new URLSearchParams({ user_id: userId });
    return this.delete<{ success: boolean; message: string }>(`${this.baseUrl}/v1/contacts/${contactId}?${params}`);
  }

  /**
   * Search contacts for a user
   */
  async searchContacts(
    userId: string,
    query: string,
    options: {
      limit?: number;
      tags?: string[];
      source_services?: string[];
    } = {}
  ): Promise<Contact[]> {
    const params = new URLSearchParams({
      user_id: userId,
      query,
      ...(options.limit && { limit: options.limit.toString() }),
      ...(options.tags && { tags: options.tags.join(',') }),
      ...(options.source_services && { source_services: options.source_services.join(',') }),
    });

    return this.get<Contact[]>(`${this.baseUrl}/v1/contacts/search?${params}`);
  }

  /**
   * Get contact statistics for a user
   */
  async getContactStats(userId: string): Promise<ContactStatsResponse> {
    const params = new URLSearchParams({ user_id: userId });
    return this.get<ContactStatsResponse>(`${this.baseUrl}/v1/contacts/stats?${params}`);
  }

  /**
   * Get contacts by relevance score (most relevant first)
   */
  async getRelevantContacts(userId: string, limit: number = 20): Promise<Contact[]> {
    return this.listContacts(userId, { limit }).then(response => response.contacts);
  }

  /**
   * Get contacts by source service
   */
  async getContactsByService(userId: string, sourceService: string, limit: number = 100): Promise<Contact[]> {
    return this.listContacts(userId, { 
      source_services: [sourceService], 
      limit 
    }).then(response => response.contacts);
  }

  /**
   * Get contacts by tags
   */
  async getContactsByTags(userId: string, tags: string[], limit: number = 100): Promise<Contact[]> {
    return this.listContacts(userId, { tags, limit }).then(response => response.contacts);
  }

  /**
   * Add tags to a contact
   */
  async addTagsToContact(contactId: string, userId: string, tags: string[]): Promise<ContactResponse> {
    // First get the current contact to see existing tags
    const currentContact = await this.getContact(contactId, userId);
    const existingTags = currentContact.contact.tags || [];
    const newTags = [...new Set([...existingTags, ...tags])]; // Remove duplicates
    
    return this.updateContact(contactId, userId, { tags: newTags });
  }

  /**
   * Remove tags from a contact
   */
  async removeTagsFromContact(contactId: string, userId: string, tagsToRemove: string[]): Promise<ContactResponse> {
    // First get the current contact to see existing tags
    const currentContact = await this.getContact(contactId, userId);
    const existingTags = currentContact.contact.tags || [];
    const newTags = existingTags.filter(tag => !tagsToRemove.includes(tag));
    
    return this.updateContact(contactId, userId, { tags: newTags });
  }

  /**
   * Get contacts that have been seen recently (within last N days)
   */
  async getRecentContacts(userId: string, days: number = 30, limit: number = 50): Promise<Contact[]> {
    // This would require a backend endpoint that supports date filtering
    // For now, we'll get all contacts and filter by last_seen
    const allContacts = await this.listContacts(userId, { limit: 1000 });
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    
    return allContacts.contacts
      .filter(contact => new Date(contact.last_seen) >= cutoffDate)
      .sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime())
      .slice(0, limit);
  }

  /**
   * Get contacts with high relevance scores
   */
  async getHighRelevanceContacts(userId: string, minScore: number = 0.7, limit: number = 50): Promise<Contact[]> {
    // This would require a backend endpoint that supports score filtering
    // For now, we'll get all contacts and filter by relevance_score
    const allContacts = await this.listContacts(userId, { limit: 1000 });
    
    return allContacts.contacts
      .filter(contact => contact.relevance_score >= minScore)
      .sort((a, b) => b.relevance_score - a.relevance_score)
      .slice(0, limit);
  }
}

// Export a default instance
export const contactsClient = new ContactsClient();

// Export the class for custom instances
export default ContactsClient;
