export interface Attendee {
  name: string;
  email?: string;
  status?: 'accepted' | 'declined' | 'tentative' | 'needsAction';
}

export interface CalendarEvent {
  id: string;
  title: string;
  startTime: string; // ISO date-time string
  endTime: string;   // ISO date-time string
  description?: string;
  location?: string;
  attendees?: Attendee[];
  color?: string; // e.g., hex code or Tailwind CSS color class name
  isAllDay?: boolean;
}

export interface Task {
  id: string;
  title: string;
  completed: boolean;
  dueDate?: string; // ISO date-time string
  priority?: 'high' | 'medium' | 'low';
  notes?: string;
  source?: string; // e.g., 'user', 'ai', 'meeting:EVENT_ID'
  relatedEventId?: string; // ID of a calendar event this task is related to
} 