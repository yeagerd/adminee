"use client"

import { useState } from "react"
import { Clock, MapPin, Users, MoreVertical } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { CalendarEventItem, sampleEvent1, sampleEvent2, sampleEvent3, sampleEvents } from "./calendar-event-item"


export default function ScheduleList() {
  const [schedule, setSchedule] = useState(sampleEvents)

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
