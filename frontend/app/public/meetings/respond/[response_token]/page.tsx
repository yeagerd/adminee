"use client";
import { meetingsApi } from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import type { 
    MeetingPoll, 
    PollParticipant, 
    TimeSlot, 
    PollResponseCreate 
} from '@/types/api/meetings';
import { ArrowLeft, Calendar, Clock, MapPin, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Legacy types for backward compatibility - these should be removed once all components are updated
type Participant = 
    PollParticipant & {
    reminder_sent_count: number;
    response_token: string;
};

type Poll = MeetingPoll;

type PollResponse = PollResponseCreate;

export default function PollResponsePage() {
    // next/navigation does not have router.query, so use URLSearchParams or params prop if available
    // For now, get response_token from window.location as a workaround
    let response_token: string | undefined = undefined;
    if (typeof window !== 'undefined') {
        const match = window.location.pathname.match(/\/respond\/(.+)$/);
        response_token = match ? match[1] : undefined;
    }
    const [poll, setPoll] = useState<Poll | null>(null);
    const [responses, setResponses] = useState<PollResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState(false);
    const [expandedComments, setExpandedComments] = useState<Set<string>>(new Set());

    useEffect(() => {
        if (!response_token) return;
        meetingsApi.publicPolls.getPollResponse(response_token)
            .then(data => {
                setPoll(data.poll);
                // Initialize responses for all time slots
                const initialResponses = data.poll.time_slots.map((slot: TimeSlot) => {
                    // Check if there's an existing response for this time slot
                    const existingResponse = data.responses?.find((r: { time_slot_id: string; response: string; comment?: string }) => r.time_slot_id === slot.id);

                    if (existingResponse) {
                        // Use existing response
                        return {
                            time_slot_id: slot.id,
                            response: existingResponse.response as 'available' | 'unavailable' | 'maybe',
                            comment: existingResponse.comment || ''
                        };
                    } else {
                        // Default to unavailable
                        return {
                            time_slot_id: slot.id,
                            response: 'unavailable' as const,
                            comment: ''
                        };
                    }
                });
                setResponses(initialResponses);

                // Auto-expand comment sections that have content
                const commentSectionsToExpand = new Set<string>();
                initialResponses.forEach((response: PollResponse) => {
                    if (response.comment && response.comment.trim()) {
                        commentSectionsToExpand.add(response.time_slot_id);
                    }
                });
                setExpandedComments(commentSectionsToExpand);

                setLoading(false);
            })
            .catch((error) => {
                console.error('Error fetching poll:', error);
                setError('Invalid or expired link.');
                setLoading(false);
            });
    }, [response_token]);

    const handleResponseChange = (timeSlotId: string, response: 'available' | 'unavailable' | 'maybe') => {
        setResponses(prev =>
            prev.map(r =>
                r.time_slot_id === timeSlotId
                    ? { ...r, response }
                    : r
            )
        );
    };

    const handleCommentChange = (timeSlotId: string, comment: string) => {
        setResponses(prev =>
            prev.map(r =>
                r.time_slot_id === timeSlotId
                    ? { ...r, comment }
                    : r
            )
        );
    };

    const toggleCommentSection = (timeSlotId: string) => {
        setExpandedComments(prev => {
            const newSet = new Set(prev);
            if (newSet.has(timeSlotId)) {
                newSet.delete(timeSlotId);
            } else {
                newSet.add(timeSlotId);
            }
            return newSet;
        });
    };

    const formatDateTimeWithRange = (startTime: string, endTime: string) => {
        const start = new Date(startTime);
        const end = new Date(endTime);

        // Format the date part
        const dateFormatted = start.toLocaleString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
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
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const timezoneAbbr = new Intl.DateTimeFormat('en-US', {
            timeZone: timezone,
            timeZoneName: 'short'
        }).formatToParts(new Date()).find(part => part.type === 'timeZoneName')?.value || '';

        return `${dateFormatted}, ${startFormatted} - ${endFormatted} ${timezoneAbbr}`;
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true);
        const res = await meetingsApi.publicPolls.updatePollResponse(response_token, { responses });
        if (res.ok) {
            setSubmitted(true);
        } else {
            setError('Failed to submit response.');
        }
        setLoading(false);
    };

    if (loading) return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading poll...</p>
            </div>
        </div>
    );

    if (error) return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <div className="text-red-600 text-6xl mb-4">⚠️</div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
                <p className="text-gray-600">{error}</p>
            </div>
        </div>
    );

    if (submitted) return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <div className="text-green-600 text-6xl mb-4">✅</div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Thank you!</h1>
                <p className="text-gray-600">Your response has been submitted successfully.</p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-2xl mx-auto px-4">
                <div className="bg-white rounded-lg shadow-lg p-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Meeting Poll Response</h1>
                    <h2 className="text-xl font-semibold text-gray-700 mb-4">{poll?.title}</h2>

                    {poll?.description && (
                        <p className="text-gray-600 mb-6">{poll.description}</p>
                    )}

                    <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                        <div className="flex items-center text-blue-800">
                            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <span className="font-medium">Meeting Details</span>
                        </div>
                        <div className="mt-2 text-sm text-blue-700">
                            <p><strong>Duration:</strong> {poll?.duration_minutes} minutes</p>
                            {poll?.location && <p><strong>Location:</strong> {poll.location}</p>}
                            <p><strong>Type:</strong> {poll?.meeting_type.replace('_', ' ')}</p>
                        </div>
                    </div>

                    {poll?.reveal_participants && poll?.participants && poll.participants.length > 0 && (
                        <div className="mb-6 p-4 bg-green-50 rounded-lg">
                            <div className="flex items-center text-green-800">
                                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
                                </svg>
                                <span className="font-medium">Other Participants</span>
                            </div>
                            <div className="mt-2 text-sm text-green-700">
                                <ul className="space-y-1">
                                    {poll.participants.map((participant) => (
                                        <li key={participant.id} className="flex items-center">
                                            <span className="font-medium">{participant.name || 'Unknown'}</span>
                                            <span className="mx-2">•</span>
                                            <span className="text-green-600">{participant.email}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Select your availability for each time slot:</h3>

                            <div className="space-y-6">
                                {poll?.time_slots.map((slot) => {
                                    const currentResponse = responses.find(r => r.time_slot_id === slot.id)?.response || 'unavailable';
                                    const isCommentExpanded = expandedComments.has(slot.id);
                                    const hasComment = responses.find(r => r.time_slot_id === slot.id)?.comment;

                                    return (
                                        <div key={slot.id} className="border border-gray-200 rounded-lg p-6">
                                            <div className="mb-4">
                                                <h4 className="text-lg font-medium text-gray-900">
                                                    {formatDateTimeWithRange(slot.start_time, slot.end_time)}
                                                </h4>
                                            </div>

                                            <div className="space-y-4">
                                                <div className="flex flex-wrap gap-3">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleResponseChange(slot.id, 'available')}
                                                        className={`flex items-center gap-3 px-6 py-4 rounded-lg border-2 transition-all duration-200 font-medium ${currentResponse === 'available'
                                                            ? 'border-green-500 bg-green-50 text-green-700 shadow-md'
                                                            : 'border-gray-300 bg-white text-gray-700 hover:border-green-300 hover:bg-green-25'
                                                            }`}
                                                    >
                                                        <Check className={`h-5 w-5 ${currentResponse === 'available' ? 'text-green-600' : 'text-gray-400'}`} />
                                                        <span>Available</span>
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() => handleResponseChange(slot.id, 'maybe')}
                                                        className={`flex items-center gap-3 px-6 py-4 rounded-lg border-2 transition-all duration-200 font-medium ${currentResponse === 'maybe'
                                                            ? 'border-yellow-500 bg-yellow-50 text-yellow-700 shadow-md'
                                                            : 'border-gray-300 bg-white text-gray-700 hover:border-yellow-300 hover:bg-yellow-25'
                                                            }`}
                                                    >
                                                        <HelpCircle className={`h-5 w-5 ${currentResponse === 'maybe' ? 'text-yellow-600' : 'text-gray-400'}`} />
                                                        <span>Maybe</span>
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() => handleResponseChange(slot.id, 'unavailable')}
                                                        className={`flex items-center gap-3 px-6 py-4 rounded-lg border-2 transition-all duration-200 font-medium ${currentResponse === 'unavailable'
                                                            ? 'border-red-500 bg-red-50 text-red-700 shadow-md'
                                                            : 'border-gray-300 bg-white text-gray-700 hover:border-red-300 hover:bg-red-25'
                                                            }`}
                                                    >
                                                        <X className={`h-5 w-5 ${currentResponse === 'unavailable' ? 'text-red-600' : 'text-gray-400'}`} />
                                                        <span>Unavailable</span>
                                                    </button>
                                                </div>

                                                <div className="border-t pt-4">
                                                    <button
                                                        type="button"
                                                        onClick={() => toggleCommentSection(slot.id)}
                                                        className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                                                    >
                                                        {isCommentExpanded ? (
                                                            <ChevronUp className="h-4 w-4" />
                                                        ) : (
                                                            <ChevronDown className="h-4 w-4" />
                                                        )}
                                                        <span>
                                                            Comments {hasComment && !isCommentExpanded && '(has content)'} (optional)
                                                        </span>
                                                    </button>

                                                    {isCommentExpanded && (
                                                        <div className="mt-3">
                                                            <textarea
                                                                value={responses.find(r => r.time_slot_id === slot.id)?.comment || ''}
                                                                onChange={(e) => handleCommentChange(slot.id, e.target.value)}
                                                                placeholder="Add any comments about this time slot..."
                                                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                                                rows={2}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="flex justify-end space-x-4">
                            <button
                                type="submit"
                                disabled={loading}
                                className="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {loading ? 'Submitting...' : 'Submit Response'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
} 