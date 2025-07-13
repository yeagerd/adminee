"use client"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { calendarCache } from "@/lib/calendar-cache"
import { CalendarErrorHandler, type CalendarError } from "@/lib/calendar-error-handler"
import { convertDemoEventsToUnified, demoCalendarEvents } from "@/lib/demo-data"
import { gatewayClient } from "@/lib/gateway-client"
import { CalendarEvent } from "@/types/office-service"
import { AlertCircle, Info, RefreshCw } from "lucide-react"
import { useSession } from "next-auth/react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { CalendarEventItem } from "./calendar-event-item"

interface ScheduleListProps {
    dateRange?: 'today' | 'week' | 'month'
    providers?: string[]
    limit?: number
    fallbackToDemo?: boolean
    showDemoIndicator?: boolean
}

export default function ScheduleList({
    dateRange = 'week',
    providers = ['google', 'microsoft'],
    limit = 50,
    fallbackToDemo = true,
    showDemoIndicator = false
}: ScheduleListProps) {
    const { data: session } = useSession()
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<CalendarError | null>(null)
    const [refreshing, setRefreshing] = useState(false)
    const [isUsingDemoData, setIsUsingDemoData] = useState(false)
    const [cacheHit, setCacheHit] = useState(false)

    // Memoize the providers array to prevent unnecessary re-renders
    const memoizedProviders = useMemo(() => providers, [providers.join(',')])

    // Memoize the fallbackToDemo value to prevent unnecessary re-renders
    const memoizedFallbackToDemo = useMemo(() => fallbackToDemo, [fallbackToDemo])

    const fetchEvents = useCallback(async (retryCount = 0) => {
        if (!session?.user?.id) {
            setError(CalendarErrorHandler.createError(new Error('User session not available')))
            setLoading(false)
            return
        }

        // Validate user ID format
        const userId = session.user.id
        if (!userId || userId.trim() === '') {
            setError(CalendarErrorHandler.createError(new Error('Invalid user ID')))
            setLoading(false)
            return
        }

        try {
            setError(null)
            setIsUsingDemoData(false)
            setCacheHit(false)

            // Calculate date range inside the callback
            const now = new Date()
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
            let start_date: string
            let end_date: string

            switch (dateRange) {
                case 'today':
                    start_date = today.toISOString().split('T')[0]
                    end_date = today.toISOString().split('T')[0]
                    break
                case 'week':
                    const weekStart = new Date(today)
                    weekStart.setDate(today.getDate() - today.getDay())
                    const weekEnd = new Date(weekStart)
                    weekEnd.setDate(weekStart.getDate() + 6)
                    start_date = weekStart.toISOString().split('T')[0]
                    end_date = weekEnd.toISOString().split('T')[0]
                    break
                case 'month':
                    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
                    const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0)
                    start_date = monthStart.toISOString().split('T')[0]
                    end_date = monthEnd.toISOString().split('T')[0]
                    break
                default:
                    start_date = today.toISOString().split('T')[0]
                    end_date = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
            }

            // Check cache first
            const cachedEvents = calendarCache.get(userId, memoizedProviders, dateRange, limit)
            if (cachedEvents) {
                setEvents(cachedEvents)
                setCacheHit(true)
                setLoading(false)
                setRefreshing(false)
                return
            }

            const response = await gatewayClient.getCalendarEvents(
                userId,
                memoizedProviders,
                limit,
                start_date,
                end_date
            )

            if (response.success && response.data) {
                const fetchedEvents = response.data.events || []
                setEvents(fetchedEvents)

                // Cache the successful response
                calendarCache.set(userId, memoizedProviders, dateRange, limit, fetchedEvents)

                // Log provider information for debugging
                if (response.data.providers_used && response.data.providers_used.length > 0) {
                    console.log('Calendar events fetched from providers:', response.data.providers_used)
                }

                if (response.data.provider_errors && Object.keys(response.data.provider_errors).length > 0) {
                    console.warn('Some providers had errors:', response.data.provider_errors)
                }
            } else {
                throw new Error('Failed to fetch calendar events')
            }
        } catch (err) {
            console.error('Error fetching calendar events:', err)
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch calendar events'

            // Retry logic for network errors
            if (retryCount < 2 && (errorMessage.includes('network') || errorMessage.includes('fetch'))) {
                console.log(`Retrying calendar fetch (attempt ${retryCount + 1})`)
                setTimeout(() => fetchEvents(retryCount + 1), 1000 * (retryCount + 1))
                return
            }

            // Fallback to demo data if enabled
            if (memoizedFallbackToDemo) {
                console.log('Falling back to demo data due to API error')
                const demoEvents = convertDemoEventsToUnified(demoCalendarEvents)
                setEvents(demoEvents)
                setIsUsingDemoData(true)
                setError(null) // Clear error since we're using demo data
            } else {
                setError(CalendarErrorHandler.createError(new Error(errorMessage)))
            }
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [session?.user?.id, memoizedProviders, limit, dateRange, memoizedFallbackToDemo])

    const handleRefresh = () => {
        setRefreshing(true)
        fetchEvents()
    }

    useEffect(() => {
        fetchEvents()
    }, [fetchEvents])

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
                        {error.userFriendlyMessage}
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
            {/* Demo/Cache Indicators */}
            {(isUsingDemoData || cacheHit || showDemoIndicator) && (
                <div className="mb-4 space-y-2">
                    {isUsingDemoData && (
                        <Alert>
                            <Info className="h-4 w-4" />
                            <AlertDescription className="flex items-center gap-2">
                                <span>Showing demo data due to connection issues</span>
                                <Badge variant="secondary" className="text-xs">
                                    Demo Mode
                                </Badge>
                            </AlertDescription>
                        </Alert>
                    )}
                    {cacheHit && !isUsingDemoData && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Info className="h-3 w-3" />
                            <span>Cached data</span>
                        </div>
                    )}
                </div>
            )}

            <div className="space-y-4">
                {events.map((event) => (
                    <CalendarEventItem key={event.id} event={event} />
                ))}
            </div>
        </ScrollArea>
    )
}
