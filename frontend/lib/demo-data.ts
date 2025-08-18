import { CalendarEvent } from "@/types/api/office";

// Demo data for the demos page
export interface DemoUser {
    id: string;
    name: string;
    email: string;
    image?: string;
}

export interface DemoIntegration {
    id: number;
    user_id: string;
    provider: string;
    status: string;
    scopes: string[];
    external_user_id?: string;
    external_email?: string;
    external_name?: string;
    has_access_token: boolean;
    has_refresh_token: boolean;
    token_expires_at?: string;
    token_created_at?: string;
    last_sync_at?: string;
    last_error?: string;
    error_count: number;
    created_at: string;
    updated_at: string;
}

export interface DemoTask {
    id: string;
    title: string;
    description?: string;
    completed: boolean;
    priority: 'low' | 'medium' | 'high';
    dueDate?: Date;
    category?: string;
}

export interface DemoCalendarEvent {
    id: string;
    title: string;
    startTime: Date;
    endTime: Date;
    location?: string;
    isUserOrganizer: boolean;
    organizerIsInternal: boolean;
    attendees: DemoAttendee[];
    hasExternalAttendees: boolean;
    notesFound?: {
        title: string;
        source: "Drive" | "OneNote" | "Notion";
        lastModified: string;
    }[];
}

export interface DemoAttendee {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    status: "accepted" | "declined" | "tentative" | "no-response";
    isInternal: boolean;
}

// Demo user data
export const demoUser: DemoUser = {
    id: "demo-user-123",
    name: "Demo User",
    email: "demo@briefly.com",
    image: "/placeholder-user.jpg"
};

// Demo integrations data
export const demoIntegrations: DemoIntegration[] = [
    {
        id: 1,
        user_id: "demo-user-123",
        provider: "google",
        status: "ACTIVE",
        scopes: ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.readonly"],
        external_user_id: "demo-google-user",
        external_email: "demo@gmail.com",
        external_name: "Demo Google User",
        has_access_token: true,
        has_refresh_token: true,
        token_expires_at: "2025-12-31T23:59:59Z",
        token_created_at: "2025-01-01T00:00:00Z",
        last_sync_at: "2025-01-15T10:30:00Z",
        error_count: 0,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-15T10:30:00Z"
    },
    {
        id: 2,
        user_id: "demo-user-123",
        provider: "microsoft",
        status: "ACTIVE",
        scopes: ["https://graph.microsoft.com/Calendars.ReadWrite", "https://graph.microsoft.com/Mail.Read"],
        external_user_id: "demo-ms-user",
        external_email: "demo@outlook.com",
        external_name: "Demo Microsoft User",
        has_access_token: true,
        has_refresh_token: true,
        token_expires_at: "2025-12-31T23:59:59Z",
        token_created_at: "2025-01-01T00:00:00Z",
        last_sync_at: "2025-01-15T10:30:00Z",
        error_count: 0,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-15T10:30:00Z"
    }
];

// Demo calendar events (extracted from calendar-event-item.tsx)
export const demoCalendarEvents: DemoCalendarEvent[] = [
    {
        id: "1",
        title: "Project Kickoff Meeting",
        startTime: new Date("2025-01-15T14:00:00"),
        endTime: new Date("2025-01-15T15:30:00"),
        location: "Conference Room A / Teams",
        isUserOrganizer: true,
        organizerIsInternal: true,
        hasExternalAttendees: true,
        attendees: [
            {
                id: "1",
                name: "Sarah Johnson",
                email: "sarah.johnson@company.com",
                status: "accepted" as const,
                isInternal: true,
            },
            {
                id: "2",
                name: "Mike Chen",
                email: "mike.chen@company.com",
                status: "tentative" as const,
                isInternal: true,
            },
            {
                id: "3",
                name: "Alex Rivera",
                email: "alex@clientcompany.com",
                status: "no-response" as const,
                isInternal: false,
            },
            {
                id: "4",
                name: "Emma Davis",
                email: "emma@partner.com",
                status: "declined" as const,
                isInternal: false,
            },
        ],
        notesFound: [
            {
                title: "Q4 Strategy Draft",
                source: "Drive" as const,
                lastModified: "2 days ago",
            },
        ],
    },
    {
        id: "2",
        title: "Team Standup",
        startTime: new Date("2025-01-15T15:30:00"),
        endTime: new Date("2025-01-15T16:00:00"),
        location: "Zoom Meeting",
        isUserOrganizer: true,
        organizerIsInternal: true,
        hasExternalAttendees: false,
        attendees: [
            {
                id: "1",
                name: "Sarah Johnson",
                email: "sarah.johnson@company.com",
                status: "accepted" as const,
                isInternal: true,
            },
            {
                id: "2",
                name: "Mike Chen",
                email: "mike.chen@company.com",
                status: "tentative" as const,
                isInternal: true,
            },
        ],
        notesFound: [
            {
                title: "Standup Notes",
                source: "Drive" as const,
                lastModified: "2 days ago",
            },
        ],
    },
    {
        id: "3",
        title: "Project Update",
        startTime: new Date("2025-01-15T17:00:00"),
        endTime: new Date("2025-01-15T17:30:00"),
        location: "Conference Room A / Teams",
        isUserOrganizer: false,
        organizerIsInternal: false,
        hasExternalAttendees: true,
        attendees: [
            {
                id: "1",
                name: "Sarah Johnson",
                email: "sarah.johnson@company.com",
                status: "accepted" as const,
                isInternal: true,
            },
            {
                id: "2",
                name: "Mike Chen",
                email: "mike.chen@company.com",
                status: "tentative" as const,
                isInternal: true,
            },
            {
                id: "3",
                name: "Alex Rivera",
                email: "alex@clientcompany.com",
                status: "no-response" as const,
                isInternal: false,
            },
            {
                id: "4",
                name: "Emma Davis",
                email: "emma@partner.com",
                status: "declined" as const,
                isInternal: false,
            },
        ],
        notesFound: [
            {
                title: "Q4 Strategy Draft",
                source: "Drive" as const,
                lastModified: "2 days ago",
            },
        ],
    },
    {
        id: "4",
        title: "Quarterly Business Review",
        startTime: new Date("2025-01-15T09:00:00"),
        endTime: new Date("2025-01-15T10:00:00"),
        location: "Conference Room C / Teams",
        isUserOrganizer: false,
        organizerIsInternal: true,
        hasExternalAttendees: false,
        attendees: [
            {
                id: "1",
                name: "Sarah Johnson",
                email: "sarah.johnson@company.com",
                status: "accepted" as const,
                isInternal: true,
            },
            {
                id: "2",
                name: "Mike Chen",
                email: "mike.chen@company.com",
                status: "tentative" as const,
                isInternal: true,
            },
            {
                id: "3",
                name: "Alex Rivera",
                email: "alex@clientcompany.com",
                status: "no-response" as const,
                isInternal: false,
            },
            {
                id: "4",
                name: "Emma Davis",
                email: "emma@partner.com",
                status: "declined" as const,
                isInternal: false,
            },
        ],
        notesFound: [
            {
                title: "Q4 Strategy Draft",
                source: "Drive" as const,
                lastModified: "2 days ago",
            },
        ],
    },
].sort((a, b) => a.startTime.getTime() - b.startTime.getTime());

// Utility function to convert demo events to unified CalendarEvent format
export function convertDemoEventsToUnified(demoEvents: DemoCalendarEvent[]): CalendarEvent[] {
    return demoEvents.map((demoEvent) => ({
        id: demoEvent.id,
        calendar_id: "primary",
        title: demoEvent.title,
        description: undefined,
        start_time: demoEvent.startTime.toISOString(),
        end_time: demoEvent.endTime.toISOString(),
        all_day: false,
        location: demoEvent.location,
        attendees: demoEvent.attendees.map((attendee) => ({
            email: attendee.email,
            name: attendee.name
        })),
        organizer: demoEvent.isUserOrganizer ? {
            email: "demo@briefly.com",
            name: "Demo User"
        } : {
            email: "organizer@company.com",
            name: "Meeting Organizer"
        },
        status: "confirmed",
        visibility: "default",
        provider: "google" as const,
        provider_event_id: `demo_${demoEvent.id}`,
        account_email: "demo@briefly.com",
        account_name: "Demo User",
        calendar_name: "Primary Calendar",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    }))
}

// Demo tasks data
export const demoTasks: DemoTask[] = [
    {
        id: "1",
        title: "Review Q4 budget proposal",
        description: "Go through the proposed budget for Q4 and provide feedback",
        completed: false,
        priority: "high",
        dueDate: new Date("2025-01-16T17:00:00"),
        category: "Finance"
    },
    {
        id: "2",
        title: "Prepare presentation for client meeting",
        description: "Create slides for the upcoming client presentation",
        completed: false,
        priority: "high",
        dueDate: new Date("2025-01-15T16:00:00"),
        category: "Client"
    },
    {
        id: "3",
        title: "Update project documentation",
        description: "Review and update technical documentation for the current project",
        completed: true,
        priority: "medium",
        dueDate: new Date("2025-01-14T17:00:00"),
        category: "Development"
    },
    {
        id: "4",
        title: "Schedule team retrospective",
        description: "Set up the monthly team retrospective meeting",
        completed: false,
        priority: "medium",
        dueDate: new Date("2025-01-17T17:00:00"),
        category: "Team"
    },
    {
        id: "5",
        title: "Review pull requests",
        description: "Go through pending pull requests and provide feedback",
        completed: false,
        priority: "low",
        dueDate: new Date("2025-01-16T17:00:00"),
        category: "Development"
    }
];

// Demo chat messages
export interface DemoChatMessage {
    id: string;
    content: string;
    isUser: boolean;
    timestamp: Date;
}

export const demoChatMessages: DemoChatMessage[] = [
    {
        id: "demo-msg-1",
        content: "Hello! I'm your AI assistant. I can help you manage your calendar, tasks, and emails. What would you like to do today?",
        isUser: false,
        timestamp: new Date("2025-01-15T09:00:00")
    },
    {
        id: "demo-msg-2",
        content: "Can you help me prepare for my 2pm meeting?",
        isUser: true,
        timestamp: new Date("2025-01-15T09:05:00")
    },
    {
        id: "demo-msg-3",
        content: "I'd be happy to help! I can see you have a Project Kickoff Meeting at 2:00 PM today. I found some related documents in your Drive. Would you like me to summarize the key points from the Q4 Strategy Draft?",
        isUser: false,
        timestamp: new Date("2025-01-15T09:06:00")
    }
]; 