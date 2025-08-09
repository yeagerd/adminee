'use client';

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { SmartTimeDurationInput } from "@/components/ui/smart-time-duration-input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToolState } from "@/contexts/tool-context";
import type { MeetingPoll, PollParticipant } from "@/lib/gateway-client";
import { gatewayClient } from "@/lib/gateway-client";
import { CalendarEvent } from "@/types/office-service";
import { ArrowLeft, LinkIcon, XCircle } from "lucide-react";
import { useSession } from 'next-auth/react';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from "react";
import { useUserPreferences } from '../../contexts/settings-context';
import { TimeSlotCalendar } from "./time-slot-calendar";

const getTimeZones = () =>
    Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : ["UTC"];

export function MeetingPollNew() {
    const { setMeetingSubView } = useToolState();
    const { data: session } = useSession();
    const { effectiveTimezone } = useUserPreferences();
    const searchParams = useSearchParams();

    // Get initial step from URL or default to 1
    const clampStep = (value: number): number => {
        const numeric = Number.isFinite(value) ? value : 1;
        return Math.max(1, Math.min(4, numeric));
    };
    const stepParamInitial = searchParams.get('step');
    const parsedInitialStep = stepParamInitial !== null ? parseInt(stepParamInitial, 10) : 1;
    const [step, setStep] = useState<number>(clampStep(parsedInitialStep));

    // Step 1: Basic Info
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState<number | null>(null);
    const [location, setLocation] = useState("");
    const [timeZone, setTimeZone] = useState(effectiveTimezone || "UTC");
    // Step 2: Time Slots
    const [timeSlots, setTimeSlots] = useState<{ start: string; end: string }[]>([]);
    // Calendar events for conflict detection
    const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
    const [calendarLoading, setCalendarLoading] = useState(false);
    // Step 3: Participants
    const [participants, setParticipants] = useState<Array<{ id: string; email: string; name: string }>>([]);
    const [personQuery, setPersonQuery] = useState("");
    const [suggestions, setSuggestions] = useState<Array<{ email: string; name?: string }>>([]);
    const [highlightIndex, setHighlightIndex] = useState<number>(-1);
    const [editing, setEditing] = useState<{ id: string; field: 'name' | 'email' } | null>(null);
    const [editingDraft, setEditingDraft] = useState<
        { id: string; field: 'name' | 'email'; initialValue: string; value: string } | null
    >(null);
    const [frozenOrder, setFrozenOrder] = useState<string[] | null>(null);

    const currentSortedOrderIds = (() => {
        const sorted = [...participants].sort((a, b) => {
            const an = (a.name || "").trim().toLowerCase();
            const bn = (b.name || "").trim().toLowerCase();
            if (an !== bn) return an.localeCompare(bn);
            const ae = (a.email || "").trim().toLowerCase();
            const be = (b.email || "").trim().toLowerCase();
            return ae.localeCompare(be);
        });
        return sorted.map(p => p.id);
    })();

    const getRenderedParticipants = (): Array<{ id: string; email: string; name: string }> => {
        if (editing && frozenOrder) {
            const byId = new Map(participants.map(p => [p.id, p] as const));
            const frozenList = frozenOrder.map(id => byId.get(id)).filter((p): p is { id: string; email: string; name: string } => Boolean(p));
            // Append any new participants not in frozen order, keeping their relative sorted order
            const missing = participants.filter(p => !frozenOrder.includes(p.id)).sort((a, b) => {
                const an = (a.name || "").trim().toLowerCase();
                const bn = (b.name || "").trim().toLowerCase();
                if (an !== bn) return an.localeCompare(bn);
                const ae = (a.email || "").trim().toLowerCase();
                const be = (b.email || "").trim().toLowerCase();
                return ae.localeCompare(be);
            });
            return [...frozenList, ...missing];
        }
        // Default: sorted order
        const sorted = [...participants].sort((a, b) => {
            const an = (a.name || "").trim().toLowerCase();
            const bn = (b.name || "").trim().toLowerCase();
            if (an !== bn) return an.localeCompare(bn);
            const ae = (a.email || "").trim().toLowerCase();
            const be = (b.email || "").trim().toLowerCase();
            return ae.localeCompare(be);
        });
        return sorted;
    };
    // Step 4: Review & Submit
    const [responseDeadline, setResponseDeadline] = useState("");
    const [sendEmails, setSendEmails] = useState(true);
    const [revealParticipants, setRevealParticipants] = useState(false);
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    // General
    const [loading, setLoading] = useState(false);
    const [createdPoll, setCreatedPoll] = useState<MeetingPoll | null>(null);
    const [showLinks, setShowLinks] = useState(false);

    const isNavigatingRef = useRef(false);
    const titleInputRef = useRef<HTMLInputElement>(null);
    const headerTitleInputRef = useRef<HTMLInputElement>(null);

    // Auto-focus title input when component mounts
    useEffect(() => {
        if (titleInputRef.current && step === 1) {
            titleInputRef.current.focus();
        }
    }, [step]);

    // Handle title editing
    const handleEditTitle = () => {
        setIsEditingTitle(true);
        // Focus the header title input after a brief delay to ensure it's rendered
        setTimeout(() => {
            if (headerTitleInputRef.current) {
                headerTitleInputRef.current.focus();
                headerTitleInputRef.current.select();
            }
        }, 0);
    };

    const handleTitleBlur = () => {
        setIsEditingTitle(false);
    };

    const handleTitleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            setIsEditingTitle(false);
        } else if (e.key === 'Escape') {
            setIsEditingTitle(false);
        }
    };

    // Helpers for manual link distribution
    const getResponseUrl = (token: string): string =>
        `${window.location.origin}/public/meetings/respond/${token}`;

    const copyToClipboard = async (text: string): Promise<void> => {
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
        } catch (err) {
            console.error('Failed to copy to clipboard', err);
        }
    };

    // Submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate required fields
        if (!title.trim()) {
            return;
        }

        if (timeSlots.length === 0) {
            return;
        }

        if (participants.length === 0) {
            return;
        }

        if (!responseDeadline) {
            return;
        }

        setLoading(true);

        try {
            const pollData = {
                title: title.trim(),
                description: description.trim(),
                duration_minutes: duration!,
                location: location.trim(),
                timezone: timeZone,
                meeting_type: "tbd",
                time_slots: timeSlots.map(slot => ({
                    start_time: slot.start,
                    end_time: slot.end,
                    timezone: timeZone
                })),
                participants: participants.map(p => ({
                    email: p.email.trim(),
                    name: p.name.trim() || undefined,
                })),
                response_deadline: responseDeadline,
                send_emails: sendEmails,
                reveal_participants: revealParticipants
            };

            const created = await gatewayClient.createMeetingPoll(pollData);
            setCreatedPoll(created);

            if (sendEmails) {
                // If emails are sent, return user to list
                const url = new URL(window.location.href);
                url.searchParams.delete('step');
                url.searchParams.delete('view');
                window.history.replaceState({}, '', url.toString());
                setMeetingSubView('list');
            } else {
                // Allow manual distribution: show individual response links
                setShowLinks(true);
            }
        } catch (e: unknown) {
            console.error('Failed to create meeting poll:', e);
        } finally {
            setLoading(false);
        }
    };

    // Validate and clamp step to bounds, also handle NaN
    useEffect(() => {
        const clamped = clampStep(step);
        if (clamped !== step) {
            setStep(clamped);
        }
    }, [step]);

    // Sync URL with step changes
    useEffect(() => {
        if (isNavigatingRef.current) {
            isNavigatingRef.current = false;
            return;
        }

        // Update URL when step changes
        const updateStepInURL = (newStep: number) => {
            const url = new URL(window.location.href);
            const currentStepParam = url.searchParams.get('step');

            // Always ensure the step param is set on the URL
            url.searchParams.set('step', newStep.toString());

            if (currentStepParam === newStep.toString()) {
                window.history.replaceState({ step: newStep }, '', url.toString());
            } else {
                window.history.pushState({ step: newStep }, '', url.toString());
            }
        };

        updateStepInURL(step);
    }, [step]);

    // Handle browser navigation (back/forward buttons)
    useEffect(() => {
        const handlePopState = () => {
            const url = new URL(window.location.href);
            const stepParam = url.searchParams.get('step');
            const parsed = stepParam !== null ? parseInt(stepParam, 10) : 1;
            isNavigatingRef.current = true; // prevent URL write-back
            setStep(clampStep(parsed));
        };

        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, []);

    // Stable callback for time slot changes
    const handleTimeSlotsChange = (newSlots: { start: string; end: string }[]) => {
        setTimeSlots(newSlots);
    };

    // Preserve selected starts when duration changes by recomputing ends
    const handleDurationChange = (newDuration: number) => {
        setDuration(newDuration);
        setTimeSlots(prev =>
            (prev || []).map(slot => {
                const startDate = new Date(slot.start);
                const newEnd = new Date(startDate.getTime() + newDuration * 60 * 1000).toISOString();
                return { start: slot.start, end: newEnd };
            })
        );
    };

    // Step navigation
    const nextStep = () => setStep((s) => clampStep((Number.isFinite(s) ? s : 1) + 1));
    const prevStep = () => setStep((s) => clampStep((Number.isFinite(s) ? s : 1) - 1));

    // Remove participant by stable id
    const removeParticipant = (id: string) =>
        setParticipants(prev => prev.filter(p => p.id !== id));

    const generateTempId = (): string => {
        try {
            // Prefer stable UUID when available
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const anyCrypto: any = (globalThis as unknown as { crypto?: Crypto }).crypto;
            if (anyCrypto && typeof anyCrypto.randomUUID === 'function') {
                return anyCrypto.randomUUID();
            }
        } catch {
            // ignore
        }
        return `p_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    };

    // ---- Step 3 helpers: parsing and adding people ----
    const EMAIL_REGEX = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;

    const parsePeopleFromText = (text: string): Array<{ email: string; name?: string }> => {
        const results: Array<{ email: string; name?: string }> = [];
        if (!text) return results;

        let remaining = text;

        // 1) Extract patterns like: First Last <email@domain.com>
        const nameEmailPattern = /\s*([^<>,;\n\r\t]+?)?\s*<\s*([^<>@\s,;]+@[^<>@\s,;]+)\s*>\s*/g;
        let match: RegExpExecArray | null;
        const consumedRanges: Array<{ start: number; end: number }> = [];
        while ((match = nameEmailPattern.exec(text)) !== null) {
            const nameRaw = (match[1] || "").trim();
            const emailRaw = (match[2] || "").trim();
            if (EMAIL_REGEX.test(emailRaw)) {
                results.push({ email: emailRaw, name: nameRaw || undefined });
                consumedRanges.push({ start: match.index, end: match.index + match[0].length });
            }
        }

        // Remove consumed ranges from remaining
        if (consumedRanges.length > 0) {
            let cursor = 0;
            let reduced = "";
            for (const r of consumedRanges) {
                reduced += text.slice(cursor, r.start);
                cursor = r.end;
            }
            reduced += text.slice(cursor);
            remaining = reduced;
        }

        // 2) Extract bare emails from remaining text
        const bareEmailPattern = /([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/gi;
        let m: RegExpExecArray | null;
        while ((m = bareEmailPattern.exec(remaining)) !== null) {
            const email = (m[1] || m[0]).trim();
            if (EMAIL_REGEX.test(email)) {
                results.push({ email });
            }
        }

        // 3) Also split on common delimiters and try to parse unit segments
        const segments = remaining
            .split(/[\n\r,;]+/)
            .map(s => s.trim())
            .filter(Boolean);
        for (const seg of segments) {
            if (EMAIL_REGEX.test(seg)) {
                const emailMatch = seg.match(bareEmailPattern);
                if (emailMatch && emailMatch[0]) {
                    results.push({ email: emailMatch[0].trim() });
                }
            }
        }

        // Dedupe by lowercased email
        const seen = new Set<string>();
        const deduped: Array<{ email: string; name?: string }> = [];
        for (const r of results) {
            const key = r.email.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            deduped.push(r);
        }
        return deduped;
    };

    const addPeople = (people: Array<{ email: string; name?: string }>) => {
        if (!people || people.length === 0) return;
        setParticipants(prev => {
            const existing = new Set(prev.map(p => p.email.toLowerCase()));
            const toAdd: { id: string; email: string; name: string }[] = [];
            for (const person of people) {
                const emailKey = person.email.toLowerCase();
                if (existing.has(emailKey)) continue;
                toAdd.push({ id: generateTempId(), email: person.email.trim(), name: (person.name || "").trim() });
                existing.add(emailKey);
            }
            return [...prev, ...toAdd];
        });
    };

    const confirmPersonQuery = () => {
        const text = personQuery.trim();
        if (!text) return;

        // If there is a highlighted suggestion, prefer that
        if (suggestions.length > 0 && highlightIndex >= 0 && highlightIndex < suggestions.length) {
            const selected = suggestions[highlightIndex];
            addPeople([{ email: selected.email, name: selected.name }]);
            setPersonQuery("");
            setSuggestions([]);
            setHighlightIndex(-1);
            return;
        }

        // Otherwise, parse emails from the text
        const parsed = parsePeopleFromText(text);
        if (parsed.length > 0) {
            addPeople(parsed);
            setPersonQuery("");
            setSuggestions([]);
            setHighlightIndex(-1);
        }
    };

    // Suggestions stub (to be replaced with contacts provider)
    useEffect(() => {
        if (!personQuery.trim()) {
            setSuggestions([]);
            setHighlightIndex(-1);
            return;
        }
        // TODO: integrate contacts search; for now, no results
        setSuggestions([]);
        setHighlightIndex(-1);
    }, [personQuery]);

    // Fetch calendar events for conflict detection
    useEffect(() => {
        if (step === 2 && session?.user?.id) {
            setCalendarLoading(true);
            gatewayClient.getCalendarEvents(
                ['google', 'microsoft'], // Try both providers
                50, // Get more events for better conflict detection
                new Date().toISOString().split('T')[0],
                new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 2 weeks
                undefined,
                undefined,
                timeZone
            )
                .then((response) => {
                    if (response.success && response.data) {
                        // Handle both array and object response formats
                        const events = Array.isArray(response.data)
                            ? response.data
                            : response.data.events || [];
                        setCalendarEvents(events);
                    }
                })
                .catch((err) => {
                    console.error('Failed to fetch calendar events:', err);
                    // Don't show error to user, just continue without conflict detection
                })
                .finally(() => {
                    setCalendarLoading(false);
                });
        }
    }, [step, session?.user?.id, timeZone]);

    // Auto-populate response deadline with the date of the first time slot
    useEffect(() => {
        if (timeSlots.length > 0 && timeSlots[0].start && !responseDeadline) {
            const firstSlotDate = new Date(timeSlots[0].start);
            const dateString = firstSlotDate.toISOString().split('T')[0];
            setResponseDeadline(dateString);
        }
    }, [timeSlots, responseDeadline]);

    // Update timezone when user preferences change
    useEffect(() => {
        setTimeZone(effectiveTimezone);
    }, [effectiveTimezone]);

    // Validation helpers
    const isStep1Valid = title && (typeof duration === 'number' && duration > 0) && timeZone;
    const isStep2Valid = timeSlots.length > 0 && timeSlots.every(s => s.start && s.end);
    const isStep3Valid = participants.length > 0 && participants.every(p => /.+@.+\..+/.test(p.email));

    return (
        <div className="px-8 pb-8">
            {/* Sticky header bar */}
            <div className="sticky top-0 z-20 -mx-8 px-8 py-2 bg-white/95 backdrop-blur border-b">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            onClick={() => {
                                if (window.confirm('Delete this poll draft? This action cannot be undone.')) {
                                    const url = new URL(window.location.href);
                                    url.searchParams.delete('step');
                                    url.searchParams.delete('view');
                                    window.history.replaceState({}, '', url.toString());
                                    setMeetingSubView('list');
                                }
                            }}
                        >
                            Delete Poll
                        </Button>
                        {step > 1 && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={prevStep}
                                className="flex items-center gap-2"
                            >
                                <ArrowLeft className="h-4 w-4" />
                                Back
                            </Button>
                        )}
                    </div>
                    <div
                        className={
                            isEditingTitle
                                ? "flex items-center gap-2 flex-1 min-w-0 px-4"
                                : "flex items-center justify-center flex-1"
                        }
                    >
                        {isEditingTitle ? (
                            <div className="flex items-center gap-2 w-full min-w-0">
                                <input
                                    ref={headerTitleInputRef}
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    onBlur={handleTitleBlur}
                                    onKeyDown={handleTitleKeyDown}
                                    className="text-lg sm:text-xl font-semibold bg-transparent border-b border-gray-300 focus:border-teal-500 focus:outline-none px-1 py-0 flex-1 w-full min-w-0"
                                    placeholder="Enter meeting title..."
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={handleTitleBlur}
                                    className="p-1 text-green-600 border-green-500 hover:bg-green-50"
                                    aria-label="Save title"
                                >
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </Button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 w-auto">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleEditTitle}
                                    className="h-6 w-6 p-0 hover:bg-gray-100"
                                >
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                </Button>
                                <h1 className="text-lg sm:text-xl font-semibold leading-none inline-block">
                                    {title || "Create New Meeting Poll"}
                                </h1>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {step < 4 ? (
                            <Button
                                type="button"
                                size="sm"
                                onClick={nextStep}
                                disabled={
                                    (step === 1 && !isStep1Valid) ||
                                    (step === 2 && !isStep2Valid) ||
                                    (step === 3 && !isStep3Valid)
                                }
                            >
                                Next
                            </Button>
                        ) : (
                            <Button
                                type="submit"
                                size="sm"
                                form="new-poll-form"
                                disabled={loading}
                            >
                                {loading ? "Creating..." : (sendEmails ? "Create & Send" : "Generate Poll")}
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            <Card className="mt-6">
                <CardContent className="pt-6">
                    {showLinks && createdPoll ? (
                        <div className="space-y-6">
                            <Alert>
                                <LinkIcon className="h-4 w-4" />
                                <AlertDescription>
                                    I'll send the meeting link to the participants myself. Here are the individual response links for each participant:
                                </AlertDescription>
                            </Alert>

                            <div className="space-y-4">
                                {createdPoll.participants.map((participant: PollParticipant) => (
                                    <div key={participant.id} className="border rounded-lg p-4 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="font-medium">{participant.name || participant.email}</p>
                                                <p className="text-sm text-gray-600">{participant.email}</p>
                                            </div>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={async () => await copyToClipboard(getResponseUrl(participant.response_token))}
                                            >
                                                Copy Link
                                            </Button>
                                        </div>
                                        <div className="bg-gray-50 p-2 rounded text-sm font-mono break-all">
                                            {getResponseUrl(participant.response_token)}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="flex gap-2">
                                <Button onClick={() => {
                                    // Clean up URL by removing step and view parameters
                                    const url = new URL(window.location.href);
                                    url.searchParams.delete('step');
                                    url.searchParams.delete('view');
                                    window.history.replaceState({}, '', url.toString());
                                    setMeetingSubView('list');
                                }}>
                                    Back to Polls
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <form id="new-poll-form" onSubmit={handleSubmit} className="space-y-6">
                            {step === 1 && (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block font-semibold mb-1">Title</label>
                                        <input
                                            className="w-full border rounded px-3 py-2"
                                            value={title}
                                            onChange={e => setTitle(e.target.value)}
                                            required
                                            ref={titleInputRef}
                                            placeholder="e.g., Weekly Team Sync"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Description</label>
                                        <textarea
                                            className="w-full border rounded px-3 py-2 h-24"
                                            value={description}
                                            onChange={e => setDescription(e.target.value)}
                                            placeholder="Describe the meeting purpose..."
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Duration</label>
                                        <div className="flex items-center gap-2">
                                            <SmartTimeDurationInput
                                                valueMinutes={duration ?? undefined}
                                                onChangeMinutes={handleDurationChange}
                                                className="flex-1"
                                                inputClassName="w-full"
                                                showHintWhileEditingOnly
                                            />
                                            <div className="flex items-center gap-1">
                                                {[
                                                    { label: '15m', value: 15 },
                                                    { label: '30m', value: 30 },
                                                    { label: '1hr', value: 60 },
                                                    { label: '90m', value: 90 },
                                                    { label: '2hr', value: 120 },
                                                ].map((opt) => (
                                                    <button
                                                        type="button"
                                                        key={opt.label}
                                                        className="px-2 py-1 text-xs rounded border hover:bg-muted"
                                                        onClick={() => setDuration(opt.value)}
                                                        aria-label={`Set duration ${opt.label}`}
                                                    >
                                                        {opt.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Location</label>
                                        <input className="w-full border rounded px-3 py-2" value={location} onChange={e => setLocation(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Time Zone</label>
                                        <select className="w-full border rounded px-3 py-2" value={timeZone} onChange={e => setTimeZone(e.target.value)}>
                                            {getTimeZones().map(tz => (
                                                <option key={tz} value={tz}>{tz}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            )}
                            {step === 2 && (
                                <div className="space-y-4">
                                    {typeof duration !== 'number' ? (
                                        <div className="border rounded p-4 bg-muted/30">
                                            <div className="mb-2 font-medium">Set a meeting duration to continue</div>
                                            <div className="flex items-center gap-2">
                                                <SmartTimeDurationInput
                                                    valueMinutes={undefined}
                                                    onChangeMinutes={handleDurationChange}
                                                    className="flex-1"
                                                    inputClassName="w-full"
                                                    showHintWhileEditingOnly
                                                />
                                                <div className="flex items-center gap-1">
                                                    {[
                                                        { label: '15m', value: 15 },
                                                        { label: '30m', value: 30 },
                                                        { label: '1hr', value: 60 },
                                                        { label: '90m', value: 90 },
                                                        { label: '2hr', value: 120 },
                                                    ].map((opt) => (
                                                        <button
                                                            type="button"
                                                            key={opt.label}
                                                            className="px-2 py-1 text-xs rounded border hover:bg-muted"
                                                            onClick={() => setDuration(opt.value)}
                                                            aria-label={`Set duration ${opt.label}`}
                                                        >
                                                            {opt.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <>
                                            {calendarLoading && (
                                                <div className="text-center py-4 text-muted-foreground">
                                                    Loading calendar events for conflict detection...
                                                </div>
                                            )}
                                            <TimeSlotCalendar
                                                duration={duration}
                                                timeZone={timeZone}
                                                onTimeSlotsChange={handleTimeSlotsChange}
                                                selectedTimeSlots={timeSlots}
                                                calendarEvents={calendarEvents}
                                                onDurationChange={handleDurationChange}
                                            />
                                        </>
                                    )}
                                </div>
                            )}
                            {step === 3 && (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block font-semibold mb-1">Participants</label>
                                        <div className="relative">
                                            <input
                                                className="w-full border rounded px-3 py-2"
                                                value={personQuery}
                                                onChange={(e) => setPersonQuery(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') {
                                                        e.preventDefault();
                                                        confirmPersonQuery();
                                                    } else if (e.key === 'ArrowDown') {
                                                        e.preventDefault();
                                                        if (suggestions.length > 0) {
                                                            setHighlightIndex((prev) => {
                                                                const next = prev + 1;
                                                                return next >= suggestions.length ? suggestions.length - 1 : next;
                                                            });
                                                        }
                                                    } else if (e.key === 'ArrowUp') {
                                                        e.preventDefault();
                                                        if (suggestions.length > 0) {
                                                            setHighlightIndex((prev) => {
                                                                const next = prev - 1;
                                                                return next < 0 ? 0 : next;
                                                            });
                                                        }
                                                    } else if (e.key === 'Escape') {
                                                        setSuggestions([]);
                                                        setHighlightIndex(-1);
                                                    }
                                                }}
                                                onPaste={(e) => {
                                                    const text = e.clipboardData.getData('text');
                                                    const parsed = parsePeopleFromText(text);
                                                    if (parsed.length > 0) {
                                                        e.preventDefault();
                                                        addPeople(parsed);
                                                        setPersonQuery("");
                                                        setSuggestions([]);
                                                        setHighlightIndex(-1);
                                                    }
                                                }}
                                                placeholder="Type a name or paste emails (e.g., First Last <email@domain.com>)"
                                                type="text"
                                            />
                                            {suggestions.length > 0 && (
                                                <ul className="absolute z-10 mt-1 w-full bg-white border rounded shadow max-h-60 overflow-auto">
                                                    {suggestions.map((s, idx) => (
                                                        <li
                                                            key={`${s.email}-${idx}`}
                                                            className={
                                                                "px-3 py-2 cursor-pointer flex items-center justify-between " +
                                                                (idx === highlightIndex ? "bg-teal-50" : "hover:bg-gray-50")
                                                            }
                                                            onMouseEnter={() => setHighlightIndex(idx)}
                                                            onMouseDown={(e) => {
                                                                // Prevent input blur before click
                                                                e.preventDefault();
                                                            }}
                                                            onClick={() => {
                                                                addPeople([{ email: s.email, name: s.name }]);
                                                                setPersonQuery("");
                                                                setSuggestions([]);
                                                                setHighlightIndex(-1);
                                                            }}
                                                        >
                                                            <span className="truncate">{s.name || s.email}</span>
                                                            {s.name && (
                                                                <span className="ml-2 text-sm text-gray-600 truncate">{s.email}</span>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </div>

                                        {/* Participant table (tight grid), sorted by Name then Email */}
                                        <div className="mt-3">
                                            <Table className="text-sm">
                                                <TableHeader>
                                                    <TableRow>
                                                        <TableHead className="w-1/3 py-2">Name</TableHead>
                                                        <TableHead className="w-1/2 py-2">Email Address</TableHead>
                                                        <TableHead className="w-[60px] text-right py-2">Remove</TableHead>
                                                    </TableRow>
                                                </TableHeader>
                                                <TableBody>
                                                    {getRenderedParticipants().map((p) => (
                                                        <TableRow key={p.id}>
                                                            <TableCell className="py-1.5">
                                                                {editing && editing.id === p.id && editing.field === 'name' ? (
                                                                    <input
                                                                        className="w-full border rounded px-2 py-1"
                                                                        value={editingDraft?.id === p.id && editingDraft.field === 'name' ? editingDraft.value : p.name}
                                                                        autoFocus
                                                                        onChange={(e) => {
                                                                            const value = e.target.value;
                                                                            setEditingDraft(prev => prev && prev.id === p.id && prev.field === 'name' ? { ...prev, value } : prev);
                                                                        }}
                                                                        onBlur={() => {
                                                                            // Commit on blur
                                                                            if (editingDraft && editingDraft.id === p.id && editingDraft.field === 'name') {
                                                                                const commitValue = editingDraft.value;
                                                                                setParticipants(prev => prev.map(item => item.id === p.id ? { ...item, name: commitValue } : item));
                                                                            }
                                                                            setEditing(null);
                                                                            setEditingDraft(null);
                                                                            setFrozenOrder(null);
                                                                        }}
                                                                        onKeyDown={(e) => {
                                                                            if (e.key === 'Enter') {
                                                                                // Commit on Enter
                                                                                if (editingDraft && editingDraft.id === p.id && editingDraft.field === 'name') {
                                                                                    const commitValue = editingDraft.value;
                                                                                    setParticipants(prev => prev.map(item => item.id === p.id ? { ...item, name: commitValue } : item));
                                                                                }
                                                                                setEditing(null);
                                                                                setEditingDraft(null);
                                                                                setFrozenOrder(null);
                                                                            } else if (e.key === 'Escape') {
                                                                                // Cancel without saving (revert)
                                                                                setEditing(null);
                                                                                setEditingDraft(null);
                                                                                setFrozenOrder(null);
                                                                            }
                                                                        }}
                                                                        placeholder="Name (optional)"
                                                                        type="text"
                                                                    />
                                                                ) : (
                                                                    <div
                                                                        className="cursor-text hover:underline underline-offset-2"
                                                                        onClick={() => {
                                                                            setEditing({ id: p.id, field: 'name' });
                                                                            setEditingDraft({ id: p.id, field: 'name', initialValue: p.name || '', value: p.name || '' });
                                                                            setFrozenOrder(currentSortedOrderIds);
                                                                        }}
                                                                    >
                                                                        {p.name || <span className="text-muted-foreground">Click to add name</span>}
                                                                    </div>
                                                                )}
                                                            </TableCell>
                                                            <TableCell className="py-1.5">
                                                                {editing && editing.id === p.id && editing.field === 'email' ? (
                                                                    <input
                                                                        className="w-full border rounded px-2 py-1"
                                                                        value={editingDraft?.id === p.id && editingDraft.field === 'email' ? editingDraft.value : p.email}
                                                                        autoFocus
                                                                        onChange={(e) => {
                                                                            const value = e.target.value;
                                                                            setEditingDraft(prev => prev && prev.id === p.id && prev.field === 'email' ? { ...prev, value } : prev);
                                                                        }}
                                                                        onBlur={() => {
                                                                            // Commit on blur
                                                                            if (editingDraft && editingDraft.id === p.id && editingDraft.field === 'email') {
                                                                                const commitValue = editingDraft.value;
                                                                                setParticipants(prev => prev.map(item => item.id === p.id ? { ...item, email: commitValue } : item));
                                                                            }
                                                                            setEditing(null);
                                                                            setEditingDraft(null);
                                                                            setFrozenOrder(null);
                                                                        }}
                                                                        onKeyDown={(e) => {
                                                                            if (e.key === 'Enter') {
                                                                                // Commit on Enter
                                                                                if (editingDraft && editingDraft.id === p.id && editingDraft.field === 'email') {
                                                                                    const commitValue = editingDraft.value;
                                                                                    setParticipants(prev => prev.map(item => item.id === p.id ? { ...item, email: commitValue } : item));
                                                                                }
                                                                                setEditing(null);
                                                                                setEditingDraft(null);
                                                                                setFrozenOrder(null);
                                                                            } else if (e.key === 'Escape') {
                                                                                // Cancel without saving (revert)
                                                                                setEditing(null);
                                                                                setEditingDraft(null);
                                                                                setFrozenOrder(null);
                                                                            }
                                                                        }}
                                                                        placeholder="email@domain.com"
                                                                        type="email"
                                                                    />
                                                                ) : (
                                                                    <div
                                                                        className="cursor-text hover:underline underline-offset-2 truncate"
                                                                        onClick={() => {
                                                                            setEditing({ id: p.id, field: 'email' });
                                                                            setEditingDraft({ id: p.id, field: 'email', initialValue: p.email || '', value: p.email || '' });
                                                                            setFrozenOrder(currentSortedOrderIds);
                                                                        }}
                                                                        title={p.email}
                                                                    >
                                                                        {p.email || <span className="text-muted-foreground">Click to add email</span>}
                                                                    </div>
                                                                )}
                                                            </TableCell>
                                                            <TableCell className="py-1.5 text-right">
                                                                <button
                                                                    type="button"
                                                                    className="inline-flex items-center text-red-600 hover:text-red-700 p-1"
                                                                    aria-label="Remove participant"
                                                                    onClick={() => removeParticipant(p.id)}
                                                                >
                                                                    <XCircle className="w-5 h-5" />
                                                                </button>
                                                            </TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {step === 4 && (
                                <div className="space-y-4">
                                    <h2 className="text-lg font-semibold mb-2">Review & Submit</h2>
                                    <div><b>Title:</b> {title}</div>
                                    <div><b>Description:</b> {description}</div>
                                    <div><b>Duration:</b> {duration} min</div>
                                    <div><b>Location:</b> {location}</div>
                                    <div><b>Time Zone:</b> {timeZone}</div>
                                    <div><b>Participants:</b> {participants.map(p => `${p.name} (${p.email})`).join(", ")}</div>
                                    <div><b>Time Slots:</b>
                                        <ul className="ml-4 list-disc">
                                            {timeSlots.map((slot, idx) => (
                                                <li key={idx}>{slot.start.replace("T", " ")} - {slot.end.slice(11, 16)} ({timeZone})</li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div>
                                        <b>Response Deadline:</b>
                                        <input
                                            type="date"
                                            className="ml-2 border rounded px-3 py-1"
                                            value={responseDeadline}
                                            onChange={e => setResponseDeadline(e.target.value)}
                                            required
                                        />
                                    </div>

                                    <div className="flex items-center space-x-2 pt-4">
                                        <Checkbox
                                            id="send-emails"
                                            checked={sendEmails}
                                            onCheckedChange={(checked) => setSendEmails(checked as boolean)}
                                        />
                                        <label
                                            htmlFor="send-emails"
                                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                        >
                                            Send email survey to invitees
                                        </label>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        <Checkbox
                                            id="reveal-participants"
                                            checked={revealParticipants}
                                            onCheckedChange={(checked) => setRevealParticipants(checked as boolean)}
                                        />
                                        <label
                                            htmlFor="reveal-participants"
                                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                        >
                                            Show list of all participant names and emails to invitees
                                        </label>
                                    </div>

                                    {sendEmails && revealParticipants && (
                                        <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
                                            <p>✓ The list of all participant names and emails will be included in invitation emails</p>
                                        </div>
                                    )}

                                    {!sendEmails && revealParticipants && (
                                        <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
                                            <p>✓ Participant names and emails will be visible on the response page</p>
                                        </div>
                                    )}

                                    {!sendEmails && (
                                        <Alert>
                                            <LinkIcon className="h-4 w-4" />
                                            <AlertDescription>
                                                I'll send the meeting link to the participants myself. You'll get individual response links for each participant.
                                            </AlertDescription>
                                        </Alert>
                                    )}
                                </div>
                            )}

                            {/* Navigation controls moved to sticky header */}
                        </form>
                    )}
                </CardContent>
            </Card>
        </div>
    );
} 