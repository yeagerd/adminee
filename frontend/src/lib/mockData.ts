import { CalendarEvent, Task, UserSettings, Attendee } from './types';

// Helper to generate Date objects for today at a specific time
const todayAt = (hours: number, minutes: number = 0): Date => {
  const d = new Date();
  d.setHours(hours, minutes, 0, 0);
  return d;
};

const tomorrowAt = (hours: number, minutes: number = 0): Date => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(hours, minutes, 0, 0);
  return d;
}

const yesterdayAt = (hours: number, minutes: number = 0): Date => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  d.setHours(hours, minutes, 0, 0);
  return d;
}

export const mockAttendees: Attendee[] = [
  { name: 'Alice Wonderland', email: 'alice@example.com', status: 'accepted' },
  { name: 'Bob The Builder', email: 'bob@example.com', status: 'tentative' },
  { name: 'Charlie Brown', email: 'charlie@example.com', status: 'declined' },
  { name: 'Diana Prince', email: 'diana@example.com', status: 'needsAction' },
];

export const mockCalendarEvents: CalendarEvent[] = [
  {
    id: 'event-1',
    title: 'Morning Standup',
    startTime: todayAt(9, 0),
    endTime: todayAt(9, 30),
    location: 'Virtual (Zoom)',
    attendees: [mockAttendees[0].name, mockAttendees[1].name],
    color: 'bg-blue-500',
  },
  {
    id: 'event-2',
    title: 'Project Phoenix - Deep Dive',
    startTime: todayAt(11, 0),
    endTime: todayAt(12, 30),
    description: 'Detailed discussion about an upcoming project. Bring your thinking caps!',
    attendees: mockAttendees.map(a => a.name),
    color: 'bg-green-500',
  },
  {
    id: 'event-3',
    title: 'Lunch with Client',
    startTime: todayAt(13, 0),
    endTime: todayAt(14, 0),
    location: 'The Fancy Restaurant downtown',
    attendees: [mockAttendees[0].name],
    color: 'bg-purple-500',
  },
  {
    id: 'event-4',
    title: 'Team Retrospective',
    startTime: todayAt(15, 0),
    endTime: todayAt(16, 30),
    attendees: mockAttendees.slice(0,3).map(a => a.name),
    color: 'bg-yellow-500',
  },
  {
    id: 'event-5',
    title: 'All-Day Conference',
    startTime: todayAt(0,0),
    endTime: tomorrowAt(0,0),
    isAllDay: true,
    location: 'Convention Center Hall A',
    color: 'bg-red-500',
  },
  {
    id: 'event-6',
    title: 'Doctor Appointment',
    startTime: tomorrowAt(10,0),
    endTime: tomorrowAt(10,45),
    location: 'City Clinic',
    color: 'bg-indigo-500',
  },
  {
    id: 'event-7',
    title: 'Yesterday\'s Wrap-up',
    startTime: yesterdayAt(17,0),
    endTime: yesterdayAt(17,30),
    location: 'Office',
    color: 'bg-pink-500',
  },
];

export const mockTasks: Task[] = [
  {
    id: 'task-1',
    title: 'Prepare slides for Project Phoenix Deep Dive',
    completed: false,
    dueDate: todayAt(10, 0),
    priority: 'high',
    relatedEventId: 'event-2',
    source: 'ai',
  },
  {
    id: 'task-2',
    title: 'Follow up with Bob regarding standup notes',
    completed: true,
    priority: 'medium',
    source: 'user',
    notes: 'Sent email on Monday.'
  },
  {
    id: 'task-3',
    title: 'Book flights for Q3 offsite',
    completed: false,
    dueDate: tomorrowAt(17,0),
    priority: 'high',
  },
  {
    id: 'task-4',
    title: 'Review PR #123',
    completed: false,
    priority: 'medium',
    notes: 'Check for performance regressions.'
  },
  {
    id: 'task-5',
    title: 'Draft initial meeting agenda for client lunch',
    completed: true,
    relatedEventId: 'event-3',
    source: 'meeting:event-3',
  },
  {
    id: 'task-6',
    title: 'Submit expense report for last month',
    completed: false,
    dueDate: todayAt(23,59),
    priority: 'low',
  },
];

export const mockUserSettings: UserSettings = {
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  showWeekends: true,
  defaultView: 'week',
};

// Utility function to get events for a specific day
export const getEventsForDay = (date: Date): CalendarEvent[] => {
  return mockCalendarEvents.filter(event => {
    const eventDate = new Date(event.startTime);
    return eventDate.getFullYear() === date.getFullYear() &&
           eventDate.getMonth() === date.getMonth() &&
           eventDate.getDate() === date.getDate();
  });
};