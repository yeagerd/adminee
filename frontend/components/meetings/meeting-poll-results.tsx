'use client';

import { meetingsApi } from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { PollResponse } from '@/types/api/meetings';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronRight, Plus, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

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
    duration_minutes?: number;
    participants: Participant[];
    time_slots: TimeSlot[];
    responses?: PollResponse[];
    scheduled_slot_id?: string;
}

type SortColumn = 'time_slot' | 'available' | 'maybe' | 'unavailable' | null;
type SortDirection = 'asc' | 'desc';

// Utility functions
const getSlotStats = (poll: Poll) => {
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
};

const formatTimeSlot = (startTime: string, endTime: string, timezone: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);

    const dateFormatted = start.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });

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

    const timezoneAbbr = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        timeZoneName: 'short'
    }).formatToParts(new Date()).find(part => part.type === 'timeZoneName')?.value || timezone;

    return `${dateFormatted}, ${startFormatted} - ${endFormatted} ${timezoneAbbr}`;
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

// Header Component
interface PollHeaderProps {
    onBack: () => void;
}

function PollHeader({ onBack }: PollHeaderProps) {
    return (
        <div className="flex items-center gap-4 mb-6">
            <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                className="flex items-center gap-2"
            >
                Back to List
            </Button>
            <h1 className="text-2xl font-bold">Meeting Poll Results</h1>
        </div>
    );
}

// Poll Info Component
interface PollInfoProps {
    poll: Poll;
    onEdit: () => void;
}

function PollInfo({ poll, onEdit }: PollInfoProps) {
    const totalParticipants = poll?.participants?.length || 0;
    const responded = poll?.participants?.filter((p) => p.status === "responded").length || 0;

    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-semibold">{poll.title}</h2>
                <Button onClick={onEdit} variant="outline" size="sm">
                    Edit Poll
                </Button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                <div>Status: <span className="capitalize font-medium">{poll.status}</span></div>
                <div>Created: {poll.created_at?.slice(0, 10) || ""}</div>
                <div>Location: {poll.location || "-"}</div>
                <div>Responses: {responded} of {totalParticipants}</div>
            </div>
        </div>
    );
}

// Participant Table Component
interface ParticipantTableProps {
    participants: Participant[];
    onResendEmail: (participantId: string) => void;
    resendingEmails: Set<string>;
}

function ParticipantTable({ participants, onResendEmail, resendingEmails }: ParticipantTableProps) {
    return (
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
                    {participants.map((participant) => (
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
                                        onClick={() => onResendEmail(participant.id)}
                                        disabled={resendingEmails.has(participant.id)}
                                        className="flex items-center gap-1"
                                    >
                                        Mail
                                        {resendingEmails.has(participant.id) ? 'Sending...' : 'Resend'}
                                    </Button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// Participant Section Component
interface ParticipantSectionProps {
    poll: Poll;
    onResendEmail: (participantId: string) => void;
    resendingEmails: Set<string>;
    onAddParticipant: () => void;
}

function ParticipantSection({ poll, onResendEmail, resendingEmails, onAddParticipant }: ParticipantSectionProps) {
    const [showParticipantDetails, setShowParticipantDetails] = useState(false);

    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <h3 className="font-semibold">Participant Responses:</h3>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowParticipantDetails(!showParticipantDetails)}
                        className="flex items-center gap-1"
                    >
                        {showParticipantDetails ? (
                            ChevronDown
                        ) : (
                            ChevronRight
                        )}
                        <Users className="h-4 w-4" />
                    </Button>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onAddParticipant}
                    className="flex items-center gap-1"
                >
                    <Plus className="h-4 w-4" />
                    Add Participant
                </Button>
            </div>

            {showParticipantDetails && (
                <ParticipantTable
                    participants={poll?.participants || []}
                    onResendEmail={onResendEmail}
                    resendingEmails={resendingEmails}
                />
            )}
        </div>
    );
}

// Sortable Header Component
interface SortableHeaderProps {
    column: SortColumn;
    currentSort: SortColumn;
    direction: SortDirection;
    onSort: (column: SortColumn) => void;
    children: React.ReactNode;
    align?: 'left' | 'center' | 'right';
}

function SortableHeader({ column, currentSort, direction, onSort, children, align = 'left' }: SortableHeaderProps) {
    const getSortIcon = () => {
        if (currentSort !== column) {
            return <ArrowUpDown className="h-4 w-4" />;
        }
        return direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />;
    };

    const alignClass = align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : 'justify-start';

    return (
        <th
            className="px-3 py-2 border cursor-pointer hover:bg-gray-100 select-none"
            onClick={() => onSort(column)}
        >
            <div className={`flex items-center gap-1 ${alignClass}`}>
                {children}
                {getSortIcon()}
            </div>
        </th>
    );
}

// Participant Response Item Component
interface ParticipantResponseItemProps {
    participant: Participant;
    response: string;
    comment?: string;
    respondedAt: string;
}

function ParticipantResponseItem({ participant, response, comment, respondedAt }: ParticipantResponseItemProps) {
    return (
        <div className="flex items-start justify-between p-3 bg-white rounded-lg border">
            <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-gray-900">
                        {participant?.name || 'No name'}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getResponseColor(response)}`}>
                        {getResponseLabel(response)}
                    </span>
                </div>
                <div className="text-sm text-gray-600">
                    {participant?.email}
                </div>
                {comment && (
                    <p className="text-sm text-gray-600 mt-1">
                        "{comment}"
                    </p>
                )}
            </div>
            <div className="text-xs text-gray-500 ml-4">
                {new Date(respondedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                })}
            </div>
        </div>
    );
}

// Time Slot Row Component
interface TimeSlotRowProps {
    slot: TimeSlot;
    stats: { available: number; maybe: number; unavailable: number };
    isExpanded: boolean;
    isScheduled: boolean;
    poll: Poll;
    participantResponses: Array<{
        participant: Participant;
        response: string;
        comment?: string;
        respondedAt: string;
    }>;
    onToggleExpansion: () => void;
}

function TimeSlotRow({ slot, stats, isExpanded, isScheduled, poll, participantResponses, onToggleExpansion }: TimeSlotRowProps) {
    return (
        <>
            <tr className={`${isScheduled ? 'bg-green-50' : 'hover:bg-gray-50'} transition-colors`}>
                <td className="px-3 py-2 border cursor-pointer" onClick={onToggleExpansion}>
                    <div className="flex items-center gap-2">
                        {isExpanded ? (
                            ChevronDown
                        ) : (
                            ChevronRight
                        )}
                        <span className="font-medium">{formatTimeSlot(slot.start_time, slot.end_time, slot.timezone)}</span>
                        {isScheduled && (
                            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 border border-green-300">Scheduled</span>
                        )}
                    </div>
                </td>
                <td className="px-3 py-2 border text-center">{stats.available || 0}</td>
                <td className="px-3 py-2 border text-center">{stats.maybe || 0}</td>
                <td className="px-3 py-2 border text-center">{stats.unavailable || 0}</td>
                <td className="px-3 py-2 border text-center">
                    <ScheduleActionButton slotId={slot.id} poll={poll} isScheduled={isScheduled} />
                </td>
            </tr>
            {isExpanded && (
                <tr>
                    <td colSpan={5} className="px-3 py-2 border bg-gray-50">
                        <div className="space-y-3">
                            {participantResponses.length > 0 ? (
                                <div className="space-y-2">
                                    {participantResponses.map((item, index) => (
                                        <ParticipantResponseItem
                                            key={index}
                                            participant={item.participant}
                                            response={item.response}
                                            comment={item.comment}
                                            respondedAt={item.respondedAt}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500 text-sm">No responses yet for this time slot.</p>
                            )}
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}

// Time Slots Table Component
interface TimeSlotsTableProps {
    poll: Poll;
    slotStats: Record<string, { available: number; maybe: number; unavailable: number }>;
    sortColumn: SortColumn;
    sortDirection: SortDirection;
    expandedRows: Set<string>;
    onSort: (column: SortColumn) => void;
    onToggleExpansion: (slotId: string) => void;
    onAddTime: () => void;
}

function TimeSlotsTable({ poll, slotStats, sortColumn, sortDirection, expandedRows, onSort, onToggleExpansion, onAddTime }: TimeSlotsTableProps) {
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
                    const startTimeA = new Date(a.start_time).getTime();
                    const startTimeB = new Date(b.start_time).getTime();
                    const result = startTimeA - startTimeB;
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
                    secondaryA = -statsA.maybe;
                    secondaryB = -statsB.maybe;
                    break;
                default:
                    return 0;
            }

            if (primaryA !== primaryB) {
                const result = primaryB - primaryA;
                return sortDirection === 'asc' ? -result : result;
            }

            const result = secondaryB - secondaryA;
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
        }).filter(item => item.participant).map(item => ({
            participant: item.participant!,
            response: item.response,
            comment: item.comment,
            respondedAt: item.respondedAt
        }));
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">Time Slots:</h3>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onAddTime}
                    className="flex items-center gap-1"
                >
                    <Plus className="h-4 w-4" />
                    Add Time
                </Button>
            </div>
            <p className="text-sm text-gray-600 mb-3">
                Click on any row to see detailed participant responses for that time slot.
            </p>
            <div className="overflow-x-auto">
                <table className="min-w-full text-sm border">
                    <thead>
                        <tr className="bg-gray-50">
                            <SortableHeader
                                column="time_slot"
                                currentSort={sortColumn}
                                direction={sortDirection}
                                onSort={onSort}
                            >
                                Time Slot
                            </SortableHeader>
                            <SortableHeader
                                column="available"
                                currentSort={sortColumn}
                                direction={sortDirection}
                                onSort={onSort}
                                align="center"
                            >
                                Available
                            </SortableHeader>
                            <SortableHeader
                                column="maybe"
                                currentSort={sortColumn}
                                direction={sortDirection}
                                onSort={onSort}
                                align="center"
                            >
                                Maybe
                            </SortableHeader>
                            <SortableHeader
                                column="unavailable"
                                currentSort={sortColumn}
                                direction={sortDirection}
                                onSort={onSort}
                                align="center"
                            >
                                Unavailable
                            </SortableHeader>
                            <th className="px-3 py-2 border text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortTimeSlotsByColumn(poll?.time_slots || [], slotStats).map((slot) => {
                            const participantResponses = getParticipantResponsesForSlot(slot.id);
                            const isExpanded = expandedRows.has(slot.id);
                            const isScheduled = poll?.scheduled_slot_id === slot.id;

                            return (
                                <TimeSlotRow
                                    key={slot.id}
                                    slot={slot}
                                    stats={slotStats[slot.id] || { available: 0, maybe: 0, unavailable: 0 }}
                                    isExpanded={isExpanded}
                                    isScheduled={!!isScheduled}
                                    poll={poll}
                                    participantResponses={participantResponses}
                                    onToggleExpansion={() => onToggleExpansion(slot.id)}
                                />
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

interface ScheduleActionButtonProps {
    poll: Poll;
    slotId: string;
    isScheduled: boolean;
}

function ScheduleActionButton({ poll, slotId, isScheduled }: ScheduleActionButtonProps) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const actionLabel = isScheduled ? 'Unschedule' : (poll?.scheduled_slot_id ? 'Reschedule' : 'Send Invite');

    const handleConfirm = async () => {
        setLoading(true);
        setError(null);
        try {
            if (isScheduled) {
                await meetingsApi.unscheduleMeeting(poll.id);
            } else {
                await meetingsApi.scheduleMeeting(poll.id, slotId);
            }
            // After action, refresh current view by reloading the poll via a custom event
            window.dispatchEvent(new CustomEvent('meeting-poll-refresh', { detail: { pollId: poll.id } }));
            setOpen(false);
        } catch (e: unknown) {
            if (e && typeof e === 'object' && 'message' in e) {
                setError((e as { message?: string }).message || (isScheduled ? 'Failed to unschedule' : 'Failed to schedule'));
            } else {
                setError(isScheduled ? 'Failed to unschedule' : 'Failed to schedule');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <Button
                variant={isScheduled ? 'destructive' : 'default'}
                size="sm"
                onClick={() => setOpen(true)}
            >
                {actionLabel}
            </Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>{isScheduled ? 'Unschedule this meeting?' : (poll?.scheduled_slot_id ? 'Change meeting time?' : 'Send calendar invites for this time?')}</DialogTitle>
                    </DialogHeader>
                    <div className="text-sm text-gray-700">
                        {isScheduled
                            ? 'This will remove the scheduled time and cancel the calendar event for all participants.'
                            : (poll?.scheduled_slot_id
                                ? 'This will update the existing calendar event to the new time and notify participants.'
                                : 'This will create a calendar event and send invites to all participants.')}
                    </div>
                    {error && <div className="text-red-600 text-sm">{error}</div>}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={loading}>Cancel</Button>
                        <Button onClick={handleConfirm} disabled={loading}>{loading ? 'Working...' : (isScheduled ? 'Unschedule' : 'Confirm')}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

// Add Participant Modal Component
interface AddParticipantModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onAdd: (email: string, name: string) => Promise<void>;
    loading: boolean;
}

function AddParticipantModal({ open, onOpenChange, onAdd, loading }: AddParticipantModalProps) {
    const [email, setEmail] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email || !name.trim()) {
            setError('Please fill in all fields');
            return;
        }

        if (!/.+@.+\..+/.test(email)) {
            setError('Please enter a valid email address');
            return;
        }

        try {
            await onAdd(email, name.trim());
            setEmail('');
            setName('');
            onOpenChange(false);
        } catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError('Failed to add participant');
            }
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Add Participant</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter participant name"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter participant email"
                            required
                        />
                    </div>
                    {error && (
                        <div className="text-red-600 text-sm">{error}</div>
                    )}
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading}>
                            {loading ? 'Adding...' : 'Add Participant'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// Add Time Slot Modal Component
interface AddTimeSlotModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onAdd: (startTime: string, endTime: string, timezone: string, resendInvitations: boolean) => Promise<void>;
    loading: boolean;
    pollDuration?: number;
    pollTimezone?: string;
}

function AddTimeSlotModal({ open, onOpenChange, onAdd, loading, pollDuration = 60, pollTimezone = 'UTC' }: AddTimeSlotModalProps) {
    const [date, setDate] = useState('');
    const [startTime, setStartTime] = useState('');
    const [endTime, setEndTime] = useState('');
    const [resendInvitations, setResendInvitations] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Auto-calculate end time based on start time and poll duration
    useEffect(() => {
        if (date && startTime) {
            const startDateTime = new Date(`${date}T${startTime}`);
            const endDateTime = new Date(startDateTime.getTime() + pollDuration * 60 * 1000);
            const endTimeString = endDateTime.toTimeString().slice(0, 5);
            setEndTime(endTimeString);
        }
    }, [date, startTime, pollDuration]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!date || !startTime || !endTime) {
            setError('Please fill in all fields');
            return;
        }

        const startDateTime = new Date(`${date}T${startTime}`);
        const endDateTime = new Date(`${date}T${endTime}`);

        if (startDateTime >= endDateTime) {
            setError('End time must be after start time');
            return;
        }

        try {
            await onAdd(
                startDateTime.toISOString(),
                endDateTime.toISOString(),
                pollTimezone,
                resendInvitations
            );
            setDate('');
            setStartTime('');
            setEndTime('');
            setResendInvitations(false);
            onOpenChange(false);
        } catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError('Failed to add time slot');
            }
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Add Time Slot</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Date</label>
                        <input
                            type="date"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="w-full border rounded px-3 py-2"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Start Time</label>
                        <input
                            type="time"
                            value={startTime}
                            onChange={(e) => setStartTime(e.target.value)}
                            className="w-full border rounded px-3 py-2"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">End Time</label>
                        <input
                            type="time"
                            value={endTime}
                            onChange={(e) => setEndTime(e.target.value)}
                            className="w-full border rounded px-3 py-2"
                            required
                        />
                    </div>
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="resend-invitations"
                            checked={resendInvitations}
                            onCheckedChange={(checked) => setResendInvitations(checked as boolean)}
                        />
                        <label htmlFor="resend-invitations" className="text-sm">
                            Resend invitations to all participants
                        </label>
                    </div>
                    {error && (
                        <div className="text-red-600 text-sm">{error}</div>
                    )}
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading}>
                            {loading ? 'Adding...' : 'Add Time Slot'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// Main Component
interface MeetingPollResultsProps {
    pollId: string;
}

export function MeetingPollResults({ pollId }: MeetingPollResultsProps) {
    const { setMeetingSubView } = useToolStateUtils();
    const [poll, setPoll] = useState<Poll | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortColumn, setSortColumn] = useState<SortColumn>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
    const [resendingEmails, setResendingEmails] = useState<Set<string>>(new Set());

    // Modal states
    const [addParticipantOpen, setAddParticipantOpen] = useState(false);
    const [addTimeSlotOpen, setAddTimeSlotOpen] = useState(false);
    const [modalLoading, setModalLoading] = useState(false);

    useEffect(() => {
        const listener = (e: CustomEvent<{ pollId: string }>) => {
            if (e?.detail?.pollId === pollId) {
                meetingsApi.getMeetingPoll(pollId)
                    .then((data) => setPoll(data as Poll))
                    .catch((e: unknown) => {
                        if (e && typeof e === 'object' && 'message' in e) {
                            setError((e as { message?: string }).message || 'Failed to refresh poll');
                        } else {
                            setError('Failed to refresh poll');
                        }
                    });
            }
        };
        // Cast to EventListener to satisfy TS
        const handler = listener as unknown as EventListener;
        window.addEventListener('meeting-poll-refresh', handler);
        return () => window.removeEventListener('meeting-poll-refresh', handler);
    }, [pollId]);

    useEffect(() => {
        if (!pollId) return;
        setLoading(true);
        meetingsApi.getMeetingPoll(pollId)
            .then((data) => setPoll(data as Poll))
            .catch((e: unknown) => {
                if (e && typeof e === 'object' && 'message' in e) {
                    setError((e as { message?: string }).message || 'Failed to load poll');
                } else {
                    setError('Failed to load poll');
                }
            })
            .finally(() => setLoading(false));
    }, [pollId]);

    const handleBackToList = () => {
        setMeetingSubView('list');
    };

    const handleEdit = () => {
        setMeetingSubView('edit', pollId);
    };

    const handleSort = (column: SortColumn) => {
        if (sortColumn === column) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection('desc');
        }
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

    const handleResendEmail = async (participantId: string) => {
        if (!pollId) return;

        setResendingEmails(prev => new Set(prev).add(participantId));

        try {
            await meetingsApi.resendMeetingInvitation(pollId, participantId);
            const updatedPoll = await meetingsApi.getMeetingPoll(pollId);
            setPoll(updatedPoll as Poll);
        } catch (error) {
            console.error('Failed to resend invitation:', error);
        } finally {
            setResendingEmails(prev => {
                const newSet = new Set(prev);
                newSet.delete(participantId);
                return newSet;
            });
        }
    };

    const handleAddParticipant = async (email: string, name: string) => {
        if (!pollId) return;

        setModalLoading(true);
        try {
            // Add the participant to the poll
            await meetingsApi.addMeetingParticipant(pollId, email, name);

            // Refresh the poll data
            const refreshedPoll = await meetingsApi.getMeetingPoll(pollId);
            setPoll(refreshedPoll as Poll);
        } catch (err) {
            console.error('Failed to add participant:', err);
            throw err;
        } finally {
            setModalLoading(false);
        }
    };

    const handleAddTimeSlot = async (startTime: string, endTime: string, timezone: string, resendInvitations: boolean) => {
        if (!pollId) return;

        setModalLoading(true);
        try {
            // Add the time slot
            await meetingsApi.request(`/api/v1/meetings/polls/${pollId}/slots`, {
                method: 'POST',
                body: {
                    start_time: startTime,
                    end_time: endTime,
                    timezone: timezone
                }
            });

            // If requested, resend invitations
            if (resendInvitations) {
                await meetingsApi.sendMeetingInvitations(pollId);
            }

            // Refresh the poll data
            const refreshedPoll = await meetingsApi.getMeetingPoll(pollId);
            setPoll(refreshedPoll as Poll);
        } catch (err) {
            console.error('Failed to add time slot:', err);
            throw err;
        } finally {
            setModalLoading(false);
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

    const slotStats = getSlotStats(poll);

    return (
        <div className="p-8">
            <PollHeader onBack={handleBackToList} />

            <Card>
                <CardContent className="pt-6">
                    <div className="space-y-4">
                        <PollInfo poll={poll} onEdit={handleEdit} />
                        <ParticipantSection
                            poll={poll}
                            onResendEmail={handleResendEmail}
                            resendingEmails={resendingEmails}
                            onAddParticipant={() => setAddParticipantOpen(true)}
                        />
                        <TimeSlotsTable
                            poll={poll}
                            slotStats={slotStats}
                            sortColumn={sortColumn}
                            sortDirection={sortDirection}
                            expandedRows={expandedRows}
                            onSort={handleSort}
                            onToggleExpansion={toggleRowExpansion}
                            onAddTime={() => setAddTimeSlotOpen(true)}
                        />
                    </div>
                </CardContent>
            </Card>

            <AddParticipantModal
                open={addParticipantOpen}
                onOpenChange={setAddParticipantOpen}
                onAdd={handleAddParticipant}
                loading={modalLoading}
            />

            <AddTimeSlotModal
                open={addTimeSlotOpen}
                onOpenChange={setAddTimeSlotOpen}
                onAdd={handleAddTimeSlot}
                loading={modalLoading}
                pollDuration={poll?.duration_minutes}
                pollTimezone={poll?.time_slots?.[0]?.timezone || 'UTC'}
            />
        </div>
    );
} 