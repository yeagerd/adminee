"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { demoCalendarEvents } from "@/lib/demo-data"
import type { CalendarEvent } from "@/types/api/office"
import { Provider } from "@/types/api/office"
import { useState } from "react"
import { CalendarEventItem } from "./calendar-event-item"

export function DemoScheduleList() {
    const [schedule] = useState(demoCalendarEvents)

    // Convert demo events to unified CalendarEvent format
    const convertToUnifiedEvents = (demoEvents: typeof demoCalendarEvents): CalendarEvent[] => {
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
            provider: Provider.GOOGLE,
            provider_event_id: `demo_${demoEvent.id}`,
            account_email: "demo@briefly.com",
            account_name: "Demo User",
            calendar_name: "Primary Calendar",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }))
    }

    const unifiedEvents = convertToUnifiedEvents(schedule)

    return (
        <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
                {unifiedEvents.map((event) => (
                    <CalendarEventItem key={event.id} event={event} />
                ))}
            </div>
        </ScrollArea>
    )
} 