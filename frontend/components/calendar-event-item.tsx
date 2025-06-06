"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Clock,
  MapPin,
  Users,
  ChevronDown,
  ChevronRight,
  Crown,
  Building2,
  Globe,
  Mail,
  FileText,
  Plus,
  AlertCircle,
  CheckCircle2,
  XCircle,
  MailQuestion,
} from "lucide-react"

interface Attendee {
  id: string
  name: string
  email: string
  avatar?: string
  status: "accepted" | "declined" | "tentative" | "no-response"
  isInternal: boolean
}

interface EventItemProps {
  id: string
  title: string
  startTime: Date
  endTime: Date
  location?: string
  isUserOrganizer: boolean
  organizerName: string
  organizerIsInternal: boolean
  attendees: Attendee[]
  hasExternalAttendees: boolean
  notesFound?: {
    title: string
    source: "Drive" | "OneNote" | "Notion"
    lastModified: string
  }[]
}

const attendanceIconSize = "h-4 w-4"

export function CalendarEventItem({
  id,
  title,
  startTime,
  endTime,
  location,
  isUserOrganizer,
  organizerName,
  organizerIsInternal,
  attendees,
  hasExternalAttendees,
  notesFound = [],
}: EventItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Date/time logic
  const now = new Date()
  let borderClass = "border-primary"
  if (endTime < now) {
    borderClass = "border-secondary"
  } else if (startTime < now && now < endTime) {
    borderClass = "border-[#800020]" // burgundy-red
  }

  const internalAttendees = attendees.filter((a) => a.isInternal)
  const externalAttendees = attendees.filter((a) => !a.isInternal)
  const noResponseAttendees = attendees.filter((a) => a.status === "no-response")
  const acceptedCount = attendees.filter((a) => a.status === "accepted").length
  const declinedCount = attendees.filter((a) => a.status === "declined").length

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "accepted":
        return <CheckCircle2 className={`${attendanceIconSize} text-green-500 text`} />
      case "declined":
        return <XCircle className={`${attendanceIconSize} text-red-500 text`} />
      case "tentative":
        return <MailQuestion className={`${attendanceIconSize} text-yellow-500 text`} />
      default:
        return <AlertCircle className={`${attendanceIconSize} text-gray-400 text`} />
    }
  }

  return (
    <TooltipProvider>
      <Card className={`w-full border-l-4 ${borderClass} hover:shadow-md transition-shadow`}>
        <CardHeader
          className="pb-2 pt-3"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-3">
                <h3 className="font-semibold text-sm truncate">{title}</h3>
                {isUserOrganizer && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Crown className="h-4 w-4 text-amber-500" />
                    </TooltipTrigger>
                    <TooltipContent>You're the organizer</TooltipContent>
                  </Tooltip>
                )}
                {!isUserOrganizer && organizerIsInternal && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Building2 className="h-4 w-4 text-primary" />
                    </TooltipTrigger>
                    <TooltipContent>Internal Organizer</TooltipContent>
                  </Tooltip>
                )}
                {!isUserOrganizer && !organizerIsInternal && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Globe className="h-4 w-4 text-amber-500" />
                    </TooltipTrigger>
                    <TooltipContent>External Organizer</TooltipContent>
                  </Tooltip>
                )}
                {organizerIsInternal && hasExternalAttendees && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Globe className="h-4 w-4 text-black" />
                    </TooltipTrigger>
                    <TooltipContent>External Attendees</TooltipContent>
                  </Tooltip>
                )}
              </div>

              {/* Make time/location row a flex row to use full width */}
              <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2 w-full">
                <div className="flex items-center gap-1 min-w-0">
                  <Clock className="h-3 w-3" />
                  <span className="truncate">{startTime.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} - {endTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                {location && (
                  <div className="flex items-center gap-1 min-w-0 flex-1">
                    <MapPin className="h-3 w-3" />
                    <span className="truncate">{location}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Right-side: attendee count and expand button */}
            <div className="flex items-center gap-1 ml-2 flex-shrink-0">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="h-3 w-3" />
                <span>
                  {acceptedCount}/{attendees.length}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
              >
                {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              </Button>
            </div>
          </div>
        </CardHeader>

        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleContent>
            <CardContent className="pt-0">
              <div className="space-y-4">

                {/* Attendees List - Always Show */}
                <Collapsible open={true} onOpenChange={() => {}}>
                  <CollapsibleContent>
                    <div className="grid grid-cols-2 gap-4">
                      {/* Internal Attendees */}
                      {internalAttendees.length > 0 && (
                        <div>
                          <h4 className="text-xs font-medium text-muted-foreground gap-2 mb-2 flex items-center gap-1">
                            <Building2 className={attendanceIconSize} />
                            Internal ({internalAttendees.length})
                          </h4>
                          <div className="grid grid-cols-1 gap-1">
                            {internalAttendees.map((attendee) => (
                              <div key={attendee.id} className="flex items-center gap-2 text-xs">
                                {getStatusIcon(attendee.status)}
                                <span className="flex-1 truncate">{attendee.name}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* External Attendees */}
                      {externalAttendees.length > 0 && (
                        <div>
                          <h4 className="text-xs font-medium text-muted-foreground gap-2 mb-2 flex items-center gap-1">
                            <Globe className={attendanceIconSize} />
                            External ({externalAttendees.length})
                          </h4>
                          <div className="grid grid-cols-1 gap-1">
                            {externalAttendees.map((attendee) => (
                              <div key={attendee.id} className="flex items-center gap-2 text-xs">
                                {getStatusIcon(attendee.status)}
                                <span className="flex-1 truncate">{attendee.name}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Attendee Summary */}
                      <div className="flex items-center justify-between">
                      {noResponseAttendees.length > 0 && (
                          <Button variant="outline" size="sm" className="text-xs">
                          <Mail className="h-3 w-3 mr-1" />
                          Follow up ({noResponseAttendees.length})
                          </Button>
                      )}
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>

                <Separator />

                {/* Notes Section */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      Meeting Notes
                    </h4>
                    <Button variant="ghost" size="sm" className="text-xs h-6">
                      <Plus className="h-3 w-3 mr-1" />
                      Create
                    </Button>
                  </div>

                  {notesFound.length > 0 ? (
                    <div className="space-y-1">
                      {notesFound.map((note, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-muted/50 rounded text-xs">
                          <div className="flex items-center gap-2">
                            <FileText className="h-3 w-3" />
                            <span className="font-medium">{note.title}</span>
                            <Badge variant="outline" className="text-xs">
                              {note.source}
                            </Badge>
                          </div>
                          <span className="text-muted-foreground">{note.lastModified}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded">
                      No notes found. AI will search your Drive, OneNote, and other sources.
                    </div>
                  )}
                </div>

                {/* Quick Actions */}
                {isUserOrganizer && (
                  <>
                    <Separator />
                    <div className="flex gap-2 flex-wrap">
                      <Button variant="outline" size="sm" className="text-xs">
                        <Mail className="h-3 w-3 mr-1" />
                        Send Reminder
                      </Button>
                      <Button variant="outline" size="sm" className="text-xs">
                        <FileText className="h-3 w-3 mr-1" />
                        Create Agenda
                      </Button>
                      <Button variant="outline" size="sm" className="text-xs">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Add TODO
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    </TooltipProvider>
  )
}

// Example usage with sample data
export const sampleEvent1 = {
  id: "1",
  title: "Project Kickoff Meeting",
  startTime: new Date("2025-06-02T14:00:00"),
  endTime: new Date("2025-06-02T15:30:00"),
  location: "Conference Room A / Teams",
  isUserOrganizer: true,
  organizerName: "You",
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
}


// Example usage with sample data
export const sampleEvent2 = {
  id: "2",
  title: "Team Standup",
  startTime: new Date("2025-06-02T15:30:00"),
  endTime: new Date("2025-06-02T16:00:00"),
  location: "Zoom Meeting",
  isUserOrganizer: true,
  organizerName: "You",
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
}


// Example usage with sample data
export const sampleEvent3 = {
  id: "3",
  title: "Project Update",
  startTime: new Date("2025-06-02T17:00:00"),
  endTime: new Date("2025-06-02T17:30:00"),
  location: "Conference Room A / Teams",
  isUserOrganizer: false,
  organizerName: "Emma Davis",
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
}

// Example usage with sample data
export const sampleEvent4 = {
  id: "3",
  title: "Quarterly Business Review",
  startTime: new Date("2025-06-02T09:00:00"),
  endTime: new Date("2025-06-02T10:00:00"),
  location: "Conference Room C / Teams",
  isUserOrganizer: false,
  organizerName: "Emma Davis",
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
}

export const sampleEvents = [
  sampleEvent1,
  sampleEvent2,
  sampleEvent3,
  sampleEvent4,
].sort((a, b) => a.startTime.getTime() - b.startTime.getTime())
