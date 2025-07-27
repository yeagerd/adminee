'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { gatewayClient } from '@/lib/gateway-client';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';

interface Participant {
    id: string;
    email: string;
    status: string;
}

interface TimeSlot {
    id: string;
    start_time: string;
    end_time: string;
    timezone: string;
}

interface Poll {
    id: string;
    title: string;
    status: string;
    created_at: string;
    location?: string;
    participants: Participant[];
    time_slots: TimeSlot[];
    responses?: Array<{
        id: string;
        participant_id: string;
        time_slot_id: string;
        response: string;
        comment?: string;
        created_at: string;
        updated_at: string;
    }>;
}

function getSlotStats(poll: Poll) {
    // Returns {slotId: {available: n, maybe: n, unavailable: n}}
    const stats: Record<string, { available: number; maybe: number; unavailable: number }> = {};
    (poll.time_slots || []).forEach((slot) => {
        stats[slot.id] = { available: 0, maybe: 0, unavailable: 0 };
    });
    (poll.responses || []).forEach((resp) => {
        if (stats[resp.time_slot_id]) {
            stats[resp.time_slot_id][resp.response as 'available' | 'maybe' | 'unavailable']++;
        }
    });
    return stats;
}

const formatTimeSlot = (startTime: string, endTime: string, timezone: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);

    // Format the date part
    const dateFormatted = start.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });

    // Format the time range
    const startFormatted = start.toLocaleString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });

    const endFormatted = end.toLocaleString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });

    // Get timezone abbreviation
    const timezoneAbbr = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        timeZoneName: 'short'
    }).formatToParts(new Date()).find(part => part.type === 'timeZoneName')?.value || timezone;

    return `${dateFormatted}, ${startFormatted} - ${endFormatted} ${timezoneAbbr}`;
};

interface MeetingPollResultsProps {
    pollId: string;
}

export function MeetingPollResults({ pollId }: MeetingPollResultsProps) {
    const { setMeetingSubView } = useToolStateUtils();
    const [poll, setPoll] = useState<Poll | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!pollId) return;
        setLoading(true);
        gatewayClient.getMeetingPoll(pollId)
            .then((data) => setPoll(data as Poll))
            .catch((e: unknown) => {
                if (e && typeof e === 'object' && 'message' in e) {
                    setError((e as { message?: string }).message || "Failed to load poll");
                } else {
                    setError("Failed to load poll");
                }
            })
            .finally(() => setLoading(false));
    }, [pollId]);

    const slotStats = poll ? getSlotStats(poll) : {};
    const totalParticipants = poll?.participants?.length || 0;
    const responded = poll?.participants?.filter((p) => p.status === "responded").length || 0;

    const handleBackToList = () => {
        setMeetingSubView('list');
    };

    const handleEdit = () => {
        setMeetingSubView('edit', pollId);
    };

    if (loading) {
        return (
            <div className="p-8">
                <div className="flex items-center justify-center py-8">
                    <div className="text-gray-500">Loading...</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8">
                <div className="text-red-600">{error}</div>
            </div>
        );
    }

    if (!poll) {
        return (
            <div className="p-8">
                <div className="text-gray-500">Poll not found</div>
            </div>
        );
    }

    return (
        <div className="p-8">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBackToList}
                        className="flex items-center gap-2"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Back to List
                    </Button>
                    <h1 className="text-2xl font-bold">Meeting Poll Results</h1>
                </div>
                <Button onClick={handleEdit} variant="outline">
                    Edit Poll
                </Button>
            </div>

            <Card>
                <CardContent className="pt-6">
                    <div className="space-y-4">
                        <div>
                            <h2 className="text-xl font-semibold mb-2">{poll.title}</h2>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                                <div>Status: <span className="capitalize font-medium">{poll.status}</span></div>
                                <div>Created: {poll.created_at?.slice(0, 10) || ""}</div>
                                <div>Location: {poll.location || "-"}</div>
                                <div>Participants: {totalParticipants} (Responded: {responded})</div>
                            </div>
                        </div>

                        <div>
                            <h3 className="font-semibold mb-2">Participant Status:</h3>
                            <ul className="space-y-1">
                                {(poll?.participants || []).map((p) => (
                                    <li key={p.id} className="text-sm">
                                        {p.email} <span className="text-xs text-gray-500">({p.status})</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div>
                            <h3 className="font-semibold mb-2">Time Slot Popularity:</h3>
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm border">
                                    <thead>
                                        <tr className="bg-gray-50">
                                            <th className="px-3 py-2 border text-left">Time Slot</th>
                                            <th className="px-3 py-2 border text-center">Available</th>
                                            <th className="px-3 py-2 border text-center">Maybe</th>
                                            <th className="px-3 py-2 border text-center">Unavailable</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(poll?.time_slots || []).map((slot) => (
                                            <tr key={slot.id} className="hover:bg-gray-50">
                                                <td className="px-3 py-2 border">
                                                    {formatTimeSlot(slot.start_time, slot.end_time, slot.timezone)}
                                                </td>
                                                <td className="px-3 py-2 border text-center">
                                                    {slotStats[slot.id]?.available || 0}
                                                </td>
                                                <td className="px-3 py-2 border text-center">
                                                    {slotStats[slot.id]?.maybe || 0}
                                                </td>
                                                <td className="px-3 py-2 border text-center">
                                                    {slotStats[slot.id]?.unavailable || 0}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 