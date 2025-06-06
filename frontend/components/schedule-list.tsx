"use client"

import { useState } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CalendarEventItem, sampleEvents } from "./calendar-event-item"


export default function ScheduleList() {
  const [schedule] = useState(sampleEvents)

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
