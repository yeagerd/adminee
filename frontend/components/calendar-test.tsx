"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { gatewayClient } from "@/lib/gateway-client"
import { CalendarEvent } from "@/types/office-service"
import { useSession } from "next-auth/react"
import { useState } from "react"

export function CalendarTest() {
    const { data: session } = useSession()
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const testCalendarAPI = async () => {
        if (!session?.user?.id) {
            setError('No user session')
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await gatewayClient.getCalendarEvents(
                session.user.id,
                session.provider ? [session.provider] : ['google', 'microsoft'],
                5,
                new Date().toISOString().split('T')[0],
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
            )

            if (response.success && response.data) {
                setEvents(response.data.events || [])
                console.log('Calendar test response:', response)
            } else {
                setError('API call failed')
            }
        } catch (err) {
            console.error('Calendar test error:', err)
            setError(err instanceof Error ? err.message : 'Unknown error')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Calendar API Test</CardTitle>
            </CardHeader>
            <CardContent>
                <Button onClick={testCalendarAPI} disabled={loading}>
                    {loading ? 'Testing...' : 'Test Calendar API'}
                </Button>

                {error && (
                    <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
                        Error: {error}
                    </div>
                )}

                {events.length > 0 && (
                    <div className="mt-4">
                        <h4 className="font-medium mb-2">Found {events.length} events:</h4>
                        <div className="space-y-2">
                            {events.map((event) => (
                                <div key={event.id} className="p-2 bg-gray-50 rounded text-sm">
                                    <div className="font-medium">{event.title}</div>
                                    <div className="text-gray-600">
                                        {new Date(event.start_time).toLocaleString(undefined, { timeZoneName: 'short' })} - {event.provider}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    )
} 