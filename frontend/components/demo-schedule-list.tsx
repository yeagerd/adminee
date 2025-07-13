"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { demoCalendarEvents } from "@/lib/demo-data"
import { useState } from "react"
import { CalendarEventItem } from "./calendar-event-item"

export function DemoScheduleList() {
    const [schedule] = useState(demoCalendarEvents)

    return (
        <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
                {schedule.map((event) => (
                    <CalendarEventItem key={event.id} {...event} />
                ))}
            </div>
        </ScrollArea>
    )
} 