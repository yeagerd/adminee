export interface Attendee {
  name: string;
  email?: string;
  status?: 'accepted' | 'declined' | 'tentative' | 'needsAction';
}

export interface CalendarEvent {
  id: string;
  title: string;
  startTime: Date;
  endTime: Date;
  isAllDay?: boolean;
  location?: string;
  description?: string;
  attendees?: string[]; // emails or names
  color?: string; // Optional: for UI theming
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  dueDate?: Date;
  completed: boolean;
  priority?: 'low' | 'medium' | 'high';
  relatedEventId?: string; // Optional: link task to a calendar event
  source?: string; // Add source property
  notes?: string; // Add notes property
}

export interface UserSettings {
  timezone: string;
  showWeekends: boolean;
  defaultView: 'day' | 'week' | 'month';
  // Add other user-specific settings here
} 