"use client"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { gatewayClient } from "@/lib/gateway-client"
import { CalendarEvent } from "@/types/office-service"
import { AlertCircle, RefreshCw } from "lucide-react"
import { useSession } from "next-auth/react"
import { useEffect, useState } from "react"
import { CalendarEventItem } from "./calendar-event-item"

interface ScheduleListProps {
    dateRange?: 'today' | 'week' | 'month'
    providers?: string[]
    limit?: number
}

export default function ScheduleList({
    dateRange = 'week',
    providers = ['google', 'microsoft'],
    limit = 50
}: ScheduleListProps) {
    const { data: session } = useSession()
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [refreshing, setRefreshing] = useState(false)

    const getDateRange = () => {
        const now = new Date()
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

        switch (dateRange) {
            case 'today':
                return {
                    start_date: today.toISOString().split('T')[0],
                    end_date: today.toISOString().split('T')[0]
                }
            case 'week':
                const weekStart = new Date(today)
                weekStart.setDate(today.getDate() - today.getDay())
                const weekEnd = new Date(weekStart)
                weekEnd.setDate(weekStart.getDate() + 6)
                return {
                    start_date: weekStart.toISOString().split('T')[0],
                    end_date: weekEnd.toISOString().split('T')[0]
                }
            case 'month':
                const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
                const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0)
                return {
                    start_date: monthStart.toISOString().split('T')[0],
                    end_date: monthEnd.toISOString().split('T')[0]
                }
            default:
                return {
                    start_date: today.toISOString().split('T')[0],
                    end_date: new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
                }
        }
    }

    const fetchEvents = async (retryCount = 0) => {
        if (!session?.user?.id) {
            setError('User session not available')
            setLoading(false)
            return
        }

        // Validate user ID format
        const userId = session.user.id
        if (!userId || userId.trim() === '') {
            setError('Invalid user ID')
            setLoading(false)
            return
        }

        try {
            setError(null)
            const { start_date, end_date } = getDateRange()

            const response = await gatewayClient.getCalendarEvents(
                userId,
                providers,
                limit,
                start_date,
                end_date
            )

            if (response.success && response.data) {
                setEvents(response.data.events || [])

                // Log provider information for debugging
                if (response.data.providers_used && response.data.providers_used.length > 0) {
                    console.log('Calendar events fetched from providers:', response.data.providers_used)
                }

                if (response.data.provider_errors && Object.keys(response.data.provider_errors).length > 0) {
                    console.warn('Some providers had errors:', response.data.provider_errors)
                }
            } else {
                setError('Failed to fetch calendar events')
            }
        } catch (err) {
            console.error('Error fetching calendar events:', err)
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch calendar events'

            // Retry logic for network errors
            if (retryCount < 2 && errorMessage.includes('network') || errorMessage.includes('fetch')) {
                console.log(`Retrying calendar fetch (attempt ${retryCount + 1})`)
                setTimeout(() => fetchEvents(retryCount + 1), 1000 * (retryCount + 1))
                return
            }

            setError(errorMessage)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }

    // Handle service unavailability
    const handleServiceUnavailable = () => {
        setError('Calendar service is currently unavailable. Please try again later.')
        setLoading(false)
        setRefreshing(false)
    }

    const handleRefresh = () => {
        setRefreshing(true)
        fetchEvents()
    }

    useEffect(() => {
        fetchEvents()
    }, [session?.user?.id, dateRange, providers.join(','), limit])

    if (loading) {
        return (
            <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="space-y-2">
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-3 w-1/2" />
                            <Skeleton className="h-3 w-1/3" />
                        </div>
                    ))}
                </div>
            </ScrollArea>
        )
    }

    if (error) {
        return (
            <ScrollArea className="h-[400px] pr-4">
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                        {error}
                        <Button
                            variant="outline"
                            size="sm"
                            className="ml-2"
                            onClick={handleRefresh}
                            disabled={refreshing}
                        >
                            <RefreshCw className={`h-3 w-3 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
                            Retry
                        </Button>
                    </AlertDescription>
                </Alert>
            </ScrollArea>
        )
    }

    if (events.length === 0) {
        return (
            <ScrollArea className="h-[400px] pr-4">
                <div className="text-center text-muted-foreground py-8">
                    <p>No calendar events found for this time period.</p>
                    <Button
                        variant="outline"
                        size="sm"
                        className="mt-2"
                        onClick={handleRefresh}
                        disabled={refreshing}
                    >
                        <RefreshCw className={`h-3 w-3 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </ScrollArea>
        )
    }

    return (
        <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
                {events.map((event) => (
                    <CalendarEventItem key={event.id} event={event} />
                ))}
            </div>
        </ScrollArea>
    )
}
