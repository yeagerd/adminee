// Booking API service for frontend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export interface CreateBookingLinkData {
  title: string;
  description: string;
  duration: number;
  buffer_before: number;
  buffer_after: number;
  max_per_day: number;
  max_per_week: number;
  advance_days: number;
  max_advance_days: number;
  business_hours: Record<string, { start: string; end: string; enabled: boolean }>;
  holiday_exclusions: string[];
  last_minute_cutoff: number;
  template_name?: string;
  questions?: Array<{ id: string; label: string; required: boolean; type: string }>;
  emailFollowup?: boolean;
}

export interface OneTimeLinkData {
  recipient_email: string;
  recipient_name: string;
  expires_in_days: number;
}

export interface BookingLink {
  id: string;
  owner_user_id: string;
  slug: string;
  is_active: boolean;
  settings: Record<string, unknown>;
  template_id: string | null;
  created_at: string;
  updated_at: string;
  total_views: number;
  total_bookings: number;
  conversion_rate: string;
}

export interface Booking {
  id: string;
  link_id: string;
  one_time_link_id: string | null;
  start_at: string;
  end_at: string;
  attendee_email: string;
  answers: Record<string, string> | null;
  calendar_event_id: string | null;
  created_at: string;
}

export interface AnalyticsData {
  link_id: string;
  views: number;
  bookings: number;
  conversion_rate: string;
  last_viewed: string | null;
  top_referrers: string[];
  recent_activity: Array<{ type: string; timestamp: string | null }>;
}

class BookingAPI {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}/api/v1/bookings${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      // In production, these would come from auth context
      'X-API-Key': 'frontend-meetings-key', // This should be from environment
      'X-User-Id': 'current-user-id', // This should come from auth context
    };

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Create a new evergreen booking link
  async createBookingLink(data: CreateBookingLinkData): Promise<{ data: { id: string; slug: string; public_url: string; message: string } }> {
    return this.request('/links', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // List all booking links for the authenticated user
  async listBookingLinks(): Promise<{ data: BookingLink[]; total: number }> {
    return this.request('/links');
  }

  // Get a specific booking link
  async getBookingLink(linkId: string): Promise<{ data: BookingLink }> {
    return this.request(`/links/${linkId}`);
  }

  // Update a booking link's settings
  async updateBookingLink(linkId: string, updates: Partial<CreateBookingLinkData>): Promise<{ data: BookingLink; message: string }> {
    return this.request(`/links/${linkId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  // Duplicate an existing booking link
  async duplicateBookingLink(linkId: string): Promise<{ data: { id: string; slug: string; message: string } }> {
    return this.request(`/links/${linkId}:duplicate`, {
      method: 'POST',
    });
  }

  // Toggle a booking link's active status
  async toggleBookingLink(linkId: string): Promise<{ data: { id: string; is_active: boolean; message: string } }> {
    return this.request(`/links/${linkId}:toggle`, {
      method: 'POST',
    });
  }

  // Create a one-time link for a specific recipient
  async createOneTimeLink(linkId: string, data: OneTimeLinkData): Promise<{ data: { token: string; public_url: string; expires_at: string; message: string } }> {
    return this.request(`/links/${linkId}/one-time`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Get analytics for a specific booking link
  async getLinkAnalytics(linkId: string): Promise<{ data: AnalyticsData }> {
    return this.request(`/links/${linkId}/analytics`);
  }

  // Get public link metadata
  async getPublicLink(token: string): Promise<{ data: { title: string; description: string; template_questions: Array<{ id: string; label: string; required: boolean; type: string; options?: string[]; placeholder?: string; validation?: string }>; duration_options: number[]; is_active: boolean } }> {
    return this.request(`/public/${token}`);
  }

  // Get available time slots for a public link
  async getPublicAvailability(token: string, duration: number = 30): Promise<{ data: { slots: Array<{ start: string; end: string; available: boolean }>; duration: number; timezone: string } }> {
    return this.request(`/public/${token}/availability?duration=${duration}`);
  }

  // Create a booking from a public link
  async createPublicBooking(token: string, bookingData: { start: string; end: string; attendeeEmail: string; answers?: Record<string, string> }): Promise<{ data: { id: string; message: string; calendar_event_id: string | null } }> {
    return this.request(`/public/${token}/book`, {
      method: 'POST',
      body: JSON.stringify(bookingData),
    });
  }
}

export const bookingAPI = new BookingAPI();
