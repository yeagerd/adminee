'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { gatewayClient, PollResponse } from '@/lib/gateway-client';
import { ArrowDown, ArrowLeft, ArrowUp, ArrowUpDown, ChevronDown, ChevronRight, Mail, Users } from 'lucide-react';
import React, { useEffect, useState } from 'react'; // Added missing import for React

interface Participant {
    id: string;
    email: string;
    name?: string;
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
    responses?: PollResponse[];
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

type SortColumn = 'time_slot' | 'available' | 'maybe' | 'unavailable' | null;
type SortDirection = 'asc' | 'desc';

export function MeetingPollResults({ pollId }: MeetingPollResultsProps) {
    const { setMeetingSubView } = useToolStateUtils();
    const [poll, setPoll] = useState<Poll | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortColumn, setSortColumn] = useState<SortColumn>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
    const [showParticipantDetails, setShowParticipantDetails] = useState(false);
    const [resendingEmails, setResendingEmails] = useState<Set<string>>(new Set());

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

    const handleSort = (column: SortColumn) => {
        if (sortColumn === column) {
            // Reverse direction if clicking the same column
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            // Set new column and default to desc
            setSortColumn(column);
            setSortDirection('desc');
        }
    };

    const getSortIcon = (column: SortColumn) => {
        if (sortColumn !== column) {
            return <ArrowUpDown className="h-4 w-4" />;
        }
        return sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />;
    };

    const sortTimeSlotsByColumn = (timeSlots: TimeSlot[], slotStats: Record<string, { available: number; maybe: number; unavailable: number }>) => {
        if (!sortColumn) {
            return timeSlots;
        }

        return [...timeSlots].sort((a, b) => {
            const statsA = slotStats[a.id] || { available: 0, maybe: 0, unavailable: 0 };
            const statsB = slotStats[b.id] || { available: 0, maybe: 0, unavailable: 0 };

            let primaryA: number;
            let primaryB: number;
            let secondaryA: number;
            let secondaryB: number;

            switch (sortColumn) {
                case 'time_slot':
                    // Sort by start time chronologically
                    const startTimeA = new Date(a.start_time).getTime();
                    const startTimeB = new Date(b.start_time).getTime();
                    const result = startTimeA - startTimeB; // Ascending by default (earliest first)
                    return sortDirection === 'asc' ? result : -result;
                case 'available':
                    primaryA = statsA.available;
                    primaryB = statsB.available;
                    secondaryA = statsA.maybe;
                    secondaryB = statsB.maybe;
                    break;
                case 'maybe':
                    primaryA = statsA.maybe;
                    primaryB = statsB.maybe;
                    secondaryA = statsA.available;
                    secondaryB = statsB.available;
                    break;
                case 'unavailable':
                    primaryA = statsA.unavailable;
                    primaryB = statsB.unavailable;
                    secondaryA = -statsA.maybe; // Negative of maybe as secondary
                    secondaryB = -statsB.maybe;
                    break;
                default:
                    return 0;
            }

            // Primary sort
            if (primaryA !== primaryB) {
                const result = primaryB - primaryA; // Descending by default
                return sortDirection === 'asc' ? -result : result;
            }

            // Secondary sort
            const result = secondaryB - secondaryA; // Descending by default
            return sortDirection === 'asc' ? -result : result;
        });
    };

    const getParticipantResponsesForSlot = (slotId: string) => {
        if (!poll?.responses || !poll?.participants) return [];

        const slotResponses = poll.responses.filter(r => r.time_slot_id === slotId);
        return slotResponses.map(response => {
            const participant = poll.participants.find(p => p.id === response.participant_id);
            return {
                participant,
                response: response.response,
                comment: response.comment,
                respondedAt: response.updated_at
            };
        }).filter(item => item.participant); // Only include responses with valid participants
    };

    const toggleRowExpansion = (slotId: string) => {
        const newExpandedRows = new Set(expandedRows);
        if (newExpandedRows.has(slotId)) {
            newExpandedRows.delete(slotId);
        } else {
            newExpandedRows.add(slotId);
        }
        setExpandedRows(newExpandedRows);
    };

    const getResponseColor = (response: string) => {
        switch (response) {
            case 'available':
                return 'text-green-600 bg-green-50';
            case 'maybe':
                return 'text-yellow-600 bg-yellow-50';
            case 'unavailable':
                return 'text-red-600 bg-red-50';
            default:
                return 'text-gray-600 bg-gray-50';
        }
    };

    const getResponseLabel = (response: string) => {
        switch (response) {
            case 'available':
                return 'Available';
            case 'maybe':
                return 'Maybe';
            case 'unavailable':
                return 'Unavailable';
            default:
                return response;
        }
    };

    const handleResendEmail = async (participantId: string) => {
        if (!pollId) return;

        setResendingEmails(prev => new Set(prev).add(participantId));

        try {
            await gatewayClient.resendMeetingInvitation(pollId, participantId);
            // Optionally refresh the poll data to update participant status
            const updatedPoll = await gatewayClient.getMeetingPoll(pollId);
            setPoll(updatedPoll as Poll);
        } catch (error) {
            console.error('Failed to resend invitation:', error);
            // You could add a toast notification here
        } finally {
            setResendingEmails(prev => {
                const newSet = new Set(prev);
                newSet.delete(participantId);
                return newSet;
            });
        }
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
                                <div>Responses: {responded} of {totalParticipants}</div>
                            </div>
                        </div>

                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <h3 className="font-semibold">Participant Responses:</h3>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setShowParticipantDetails(!showParticipantDetails)}
                                    className="flex items-center gap-1"
                                >
                                    {showParticipantDetails ? (
                                        <ChevronDown className="h-4 w-4" />
                                    ) : (
                                        <ChevronRight className="h-4 w-4" />
                                    )}
                                    <Users className="h-4 w-4" />
                                </Button>
                            </div>

                            {showParticipantDetails && (
                                <div className="overflow-x-auto mb-4">
                                    <table className="min-w-full text-sm border">
                                        <thead>
                                            <tr className="bg-gray-50">
                                                <th className="px-3 py-2 border text-left">Name</th>
                                                <th className="px-3 py-2 border text-left">Email</th>
                                                <th className="px-3 py-2 border text-center">Status</th>
                                                <th className="px-3 py-2 border text-center">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(poll?.participants || []).map((participant) => (
                                                <tr key={participant.id} className="hover:bg-gray-50">
                                                    <td className="px-3 py-2 border">
                                                        {participant.name || 'No name'}
                                                    </td>
                                                    <td className="px-3 py-2 border">
                                                        {participant.email}
                                                    </td>
                                                    <td className="px-3 py-2 border text-center">
                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${participant.status === 'responded'
                                                            ? 'text-green-600 bg-green-50'
                                                            : 'text-red-600 bg-red-50'
                                                            }`}>
                                                            {participant.status === 'responded' ? 'Responded' : 'Not Responded'}
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2 border text-center">
                                                        {participant.status !== 'responded' && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleResendEmail(participant.id, participant.email)}
                                                                disabled={resendingEmails.has(participant.id)}
                                                                className="flex items-center gap-1"
                                                            >
                                                                <Mail className="h-3 w-3" />
                                                                {resendingEmails.has(participant.id) ? 'Sending...' : 'Resend'}
                                                            </Button>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        <div>
                            <h3 className="font-semibold mb-2">Time Slots:</h3>
                            <p className="text-sm text-gray-600 mb-3">
                                Click on any row to see detailed participant responses for that time slot.
                            </p>
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm border">
                                    <thead>
                                        <tr className="bg-gray-50">
                                            <th
                                                className="px-3 py-2 border text-left cursor-pointer hover:bg-gray-100 select-none"
                                                onClick={() => handleSort('time_slot')}
                                            >
                                                <div className="flex items-center gap-1">
                                                    Time Slot
                                                    {getSortIcon('time_slot')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-3 py-2 border text-center cursor-pointer hover:bg-gray-100 select-none"
                                                onClick={() => handleSort('available')}
                                            >
                                                <div className="flex items-center justify-center gap-1">
                                                    Available
                                                    {getSortIcon('available')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-3 py-2 border text-center cursor-pointer hover:bg-gray-100 select-none"
                                                onClick={() => handleSort('maybe')}
                                            >
                                                <div className="flex items-center justify-center gap-1">
                                                    Maybe
                                                    {getSortIcon('maybe')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-3 py-2 border text-center cursor-pointer hover:bg-gray-100 select-none"
                                                onClick={() => handleSort('unavailable')}
                                            >
                                                <div className="flex items-center justify-center gap-1">
                                                    Unavailable
                                                    {getSortIcon('unavailable')}
                                                </div>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sortTimeSlotsByColumn(poll?.time_slots || [], slotStats).map((slot) => {
                                            const participantResponses = getParticipantResponsesForSlot(slot.id);
                                            const isExpanded = expandedRows.has(slot.id);

                                            return (
                                                <React.Fragment key={slot.id}>
                                                    <tr
                                                        className="hover:bg-gray-50 cursor-pointer"
                                                        onClick={() => toggleRowExpansion(slot.id)}
                                                    >
                                                        <td className="px-3 py-2 border">
                                                            <div className="flex items-center gap-2">
                                                                {isExpanded ? (
                                                                    <ChevronDown className="h-4 w-4 text-gray-500" />
                                                                ) : (
                                                                    <ChevronRight className="h-4 w-4 text-gray-500" />
                                                                )}
                                                                {formatTimeSlot(slot.start_time, slot.end_time, slot.timezone)}
                                                            </div>
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
                                                    {isExpanded && (
                                                        <tr>
                                                            <td colSpan={4} className="px-3 py-2 border bg-gray-50">
                                                                <div className="space-y-3">
                                                                    {participantResponses.length > 0 ? (
                                                                        <div className="space-y-2">
                                                                            {participantResponses.map((item, index) => (
                                                                                <div key={index} className="flex items-start justify-between p-3 bg-white rounded-lg border">
                                                                                    <div className="flex-1">
                                                                                        <div className="flex items-center gap-2 mb-1">
                                                                                            <span className="font-medium text-gray-900">
                                                                                                {item.participant?.name || 'No name'}
                                                                                            </span>
                                                                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getResponseColor(item.response)}`}>
                                                                                                {getResponseLabel(item.response)}
                                                                                            </span>
                                                                                        </div>
                                                                                        <div className="text-sm text-gray-600">
                                                                                            {item.participant?.email}
                                                                                        </div>
                                                                                        {item.comment && (
                                                                                            <p className="text-sm text-gray-600 mt-1">
                                                                                                "{item.comment}"
                                                                                            </p>
                                                                                        )}
                                                                                    </div>
                                                                                    <div className="text-xs text-gray-500 ml-4">
                                                                                        {new Date(item.respondedAt).toLocaleDateString('en-US', {
                                                                                            month: 'short',
                                                                                            day: 'numeric',
                                                                                            hour: 'numeric',
                                                                                            minute: '2-digit',
                                                                                            hour12: true
                                                                                        })}
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    ) : (
                                                                        <p className="text-gray-500 text-sm">No responses yet for this time slot.</p>
                                                                    )}
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    )}
                                                </React.Fragment>
                                            );
                                        })}
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