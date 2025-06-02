"use client"

import { useState } from "react"
import { Clock, MapPin, Users, MoreVertical } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

// Sample schedule data
const initialSchedule = [
  {
    id: 1,
    title: "Team Standup",
    startTime: "09:00 AM",
    endTime: "09:30 AM",
    location: "Zoom Meeting",
    attendees: ["Alex", "Jamie", "Taylor"],
    category: "Meeting",
  },
  {
    id: 2,
    title: "Product Review",
    startTime: "11:00 AM",
    endTime: "12:00 PM",
    location: "Conference Room A",
    attendees: ["Morgan", "Casey", "Riley"],
    category: "Meeting",
  },
  {
    id: 3,
    title: "Lunch with Client",
    startTime: "12:30 PM",
    endTime: "01:30 PM",
    location: "Bistro Downtown",
    attendees: ["Client", "Manager"],
    category: "External",
  },
  {
    id: 4,
    title: "Project Planning",
    startTime: "02:00 PM",
    endTime: "03:30 PM",
    location: "Main Office",
    attendees: ["Team", "Stakeholders"],
    category: "Planning",
  },
  {
    id: 5,
    title: "One-on-One with Manager",
    startTime: "04:00 PM",
    endTime: "04:30 PM",
    location: "Manager's Office",
    attendees: ["You", "Manager"],
    category: "Meeting",
  },
]

export default function ScheduleList() {
  const [schedule, setSchedule] = useState(initialSchedule)

  // Function to get badge color based on category
  const getBadgeVariant = (category: string) => {
    switch (category.toLowerCase()) {
      case "meeting":
        return "default"
      case "external":
        return "secondary"
      case "planning":
        return "outline"
      default:
        return "default"
    }
  }

  return (
    <ScrollArea className="h-[400px] pr-4">
      <div className="space-y-4">
        {schedule.map((event, index) => (
          <div key={event.id} className="relative">
            {/* Time indicator */}
            <div className="absolute left-0 top-0 w-1 h-full bg-gray-200 rounded-full">
              <div
                className="absolute w-3 h-3 bg-teal-500 rounded-full -left-1 top-6"
                style={{ transform: "translateY(-50%)" }}
              ></div>
            </div>

            <div className="pl-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{event.title}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                    <Clock className="h-3.5 w-3.5" />
                    <span>
                      {event.startTime} - {event.endTime}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                    <MapPin className="h-3.5 w-3.5" />
                    <span>{event.location}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                    <Users className="h-3.5 w-3.5" />
                    <span>{event.attendees.join(", ")}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={getBadgeVariant(event.category)}>{event.category}</Badge>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>Edit</DropdownMenuItem>
                      <DropdownMenuItem>Reschedule</DropdownMenuItem>
                      <DropdownMenuItem className="text-red-600">Cancel</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </div>

            {index < schedule.length - 1 && <Separator className="my-4" />}
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
