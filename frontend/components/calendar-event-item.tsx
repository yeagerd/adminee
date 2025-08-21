"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
    AlertCircle,
    Building2,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock,
    Crown,
    FileText,
    Globe,
    Mail,
    MailQuestion,
    MapPin,
    Plus,
    Users,
    XCircle,
} from "lucide-react"
import { useState } from "react"

import { useUserPreferences } from '@/contexts/settings-context'
import type { CalendarEvent } from "@/types/api/office"
import { DateTime } from 'luxon'

interface EventItemProps {
    event: CalendarEvent
    effectiveTimezone?: string
}

const attendanceIconSize = "h-4 w-4"

function parseUtcDate(dateString: string): Date {
    if (dateString.match(/(Z|[+-][0-9]{2}:[0-9]{2})$/)) {
        return new Date(dateString);
    }
    return new Date(dateString + 'Z');
}

export function CalendarEventItem({ event, effectiveTimezone: propTimezone }: EventItemProps) {
    const [isExpanded, setIsExpanded] = useState(false)
    const context = useUserPreferences();
    const effectiveTimezone = propTimezone || context.effectiveTimezone;

    // Parse dates from ISO strings, always as UTC
    const startTime = parseUtcDate(event.start_time)
    const endTime = parseUtcDate(event.end_time)

    // Date/time logic
    const now = new Date()
    let borderClass = "border-primary"
    if (endTime < now) {
        borderClass = "border-secondary"
    } else if (startTime < now && now < endTime) {
        borderClass = "border-[#800020]" // burgundy-red
    }

    // Determine if user is organizer (simplified logic - could be enhanced with session data)
    const isUserOrganizer = event.organizer?.email === event.account_email
    const organizerIsInternal = event.organizer?.email?.includes('@company.com') || false

    // Process attendees - convert from EmailAddress to internal format
    const processedAttendees = (event.attendees || []).map((attendee, index) => ({
        id: `${event.id}_attendee_${index}`,
        name: attendee.name || attendee.email.split('@')[0],
        email: attendee.email,
        status: "accepted" as const, // Default status since office service doesn't provide this
        isInternal: attendee.email.includes('@company.com') || false
    }))

    const internalAttendees = processedAttendees.filter((a) => a.isInternal)
    const externalAttendees = processedAttendees.filter((a) => !a.isInternal)
    const hasExternalAttendees = externalAttendees.length > 0
    // Since office service doesn't provide attendee status, we'll show all as accepted for now
    const noResponseAttendees: typeof processedAttendees = []
    const acceptedCount = processedAttendees.length

    // Mock notes found (could be enhanced with real data)
    const notesFound: { title: string; source: "Drive" | "OneNote" | "Notion"; lastModified: string }[] = []

    // Format times using Luxon for robust timezone support
    const startLuxon = DateTime.fromJSDate(startTime).setZone(effectiveTimezone);
    const endLuxon = DateTime.fromJSDate(endTime).setZone(effectiveTimezone);

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
                                <h3 className="font-semibold text-sm truncate">{event.title}</h3>
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
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Badge variant="outline" className="text-xs">
                                            {event.provider}
                                        </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {event.provider === 'google' ? 'Google Calendar' : 'Microsoft Calendar'} - {event.calendar_name}
                                    </TooltipContent>
                                </Tooltip>
                            </div>

                            {/* Make time/location row a flex row to use full width */}
                            <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2 w-full">
                                <div className="flex items-center gap-1 min-w-0">
                                    <Clock className="h-3 w-3" />
                                    <span className="truncate">
                                        {event.all_day ? (
                                            `${startLuxon.toLocaleString({ month: 'short', day: 'numeric', year: 'numeric', timeZoneName: 'short' })} (All Day)`
                                        ) : (
                                            `${startLuxon.toFormat('MMM d')} ${startLuxon.toLocaleString(DateTime.TIME_SIMPLE)} – ${endLuxon.toLocaleString(DateTime.TIME_SIMPLE)} ${endLuxon.offsetNameShort}`
                                        )}
                                    </span>
                                </div>
                                {event.location && (
                                    <div className="flex items-center gap-1 min-w-0 flex-1">
                                        <MapPin className="h-3 w-3" />
                                        <span className="truncate">{event.location}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Right-side: attendee count and expand button */}
                        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Users className="h-3 w-3" />
                                <span>
                                    {acceptedCount}/{processedAttendees.length}
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
                                <Collapsible open={true} onOpenChange={() => { }}>
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


