"use client";
import { env } from '@/lib/env';
import { Check, ChevronDown, ChevronUp, HelpCircle, X } from 'lucide-react';
import { useEffect, useState } from 'react';

type TimeSlot = {
    id: string;
    start_time: string;
    end_time: string;
    timezone: string;
    is_available: boolean;
};

type Poll = {
    title: string;
    description?: string;
    duration_minutes: number;
    location?: string;
    meeting_type: string;
    time_slots: TimeSlot[];
};

type PollResponse = {
    time_slot_id: string;
    response: 'available' | 'unavailable' | 'maybe';
    comment?: string
};

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
        fetch(`${env.GATEWAY_URL}/api/v1/public/polls/response/${response_token}`)
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }
                return res.json();
            })
            .then(data => {
                setPoll(data.poll);
                // Initialize responses for all time slots
                const initialResponses = data.poll.time_slots.map((slot: TimeSlot) => ({
                    time_slot_id: slot.id,
                    response: 'unavailable' as const,
                    comment: ''
                }));
                setResponses(initialResponses);
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

    const formatDateTime = (dateTimeStr: string) => {
        const date = new Date(dateTimeStr);
        return date.toLocaleString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        });
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true);
        const res = await fetch(`${env.GATEWAY_URL}/api/v1/public/polls/response/${response_token}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ responses }),
        });
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
                                                    {formatDateTime(slot.start_time)}
                                                </h4>
                                                <p className="text-sm text-gray-500">
                                                    Duration: {poll.duration_minutes} minutes
                                                </p>
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