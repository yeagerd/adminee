'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { gatewayClient, MeetingPoll, PollParticipant } from '@/lib/gateway-client';
import { ArrowLeft, Link as LinkIcon, Mail } from 'lucide-react';
import React, { useState } from 'react';

const getTimeZones = () =>
    Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : ["UTC"];

export function MeetingPollNew() {
    const { setMeetingSubView } = useToolStateUtils();
    const [step, setStep] = useState(1);
    // Step 1: Basic Info
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState(60);
    const [location, setLocation] = useState("");
    const [timeZone, setTimeZone] = useState("UTC");
    // Step 2: Participants
    const [participants, setParticipants] = useState<{ email: string, name: string }[]>([]);
    const [participantEmailInput, setParticipantEmailInput] = useState("");
    const [participantNameInput, setParticipantNameInput] = useState("");
    // Step 3: Time Slots
    const [timeSlots, setTimeSlots] = useState<{ start: string; end: string }[]>([]);
    const [slotStart, setSlotStart] = useState("");
    const [slotEnd, setSlotEnd] = useState("");
    // Step 4: Review & Submit
    const [responseDeadline, setResponseDeadline] = useState("");
    const [sendEmails, setSendEmails] = useState(true);
    const [createdPoll, setCreatedPoll] = useState<MeetingPoll | null>(null);
    const [showLinks, setShowLinks] = useState(false);
    // General
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Validation helpers
    const isStep1Valid = title && duration > 0 && timeZone;
    const isStep2Valid = participants.length > 0 && participants.every(p => /.+@.+\..+/.test(p.email) && p.name.trim().length > 0);
    const isStep3Valid = timeSlots.length > 0 && timeSlots.every(s => s.start && s.end);

    // Step navigation
    const nextStep = () => setStep((s) => s + 1);
    const prevStep = () => setStep((s) => s - 1);

    // Add participant
    const addParticipant = () => {
        if (
            participantEmailInput &&
            /.+@.+\..+/.test(participantEmailInput) &&
            participantNameInput.trim().length > 0 &&
            !participants.some(p => p.email === participantEmailInput)
        ) {
            setParticipants([...participants, { email: participantEmailInput, name: participantNameInput }]);
            setParticipantEmailInput("");
            setParticipantNameInput("");
        }
    };

    const removeParticipant = (email: string) => setParticipants(participants.filter(p => p.email !== email));

    const addTimeSlot = () => {
        if (slotStart && slotEnd) {
            setTimeSlots([...timeSlots, { start: slotStart, end: slotEnd }]);
            setSlotStart("");
            setSlotEnd("");
        }
    };

    const removeTimeSlot = (idx: number) => setTimeSlots(timeSlots.filter((_, i) => i !== idx));

    // Submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const pollData = {
                title,
                description,
                duration_minutes: duration,
                location,
                meeting_type: "tbd",
                response_deadline: responseDeadline ? new Date(responseDeadline).toISOString() : undefined,
                time_slots: timeSlots.map((s) => ({ start_time: s.start, end_time: s.end, timezone: timeZone })),
                participants: participants.map((p) => ({ email: p.email, name: p.name })),
            };
            const createdPollData = await gatewayClient.createMeetingPoll(pollData);
            setCreatedPoll(createdPollData);

            if (sendEmails) {
                // Send invitations via email
                await gatewayClient.sendMeetingInvitations(createdPollData.id);
                setMeetingSubView('list');
            } else {
                // Show individual response links
                setShowLinks(true);
            }
        } catch (e: unknown) {
            if (e && typeof e === 'object' && 'message' in e) {
                setError((e as { message?: string }).message || "Failed to create poll");
            } else {
                setError("Failed to create poll");
            }
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        setMeetingSubView('list');
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const getResponseUrl = (responseToken: string) => {
        const baseUrl = window.location.origin;
        return `${baseUrl}/public/meetings/respond/${responseToken}`;
    };

    return (
        <div className="p-8">
            <div className="flex items-center gap-4 mb-6">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCancel}
                    className="flex items-center gap-2"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to List
                </Button>
                <h1 className="text-2xl font-bold">Create New Meeting Poll</h1>
            </div>

            <Card>
                <CardContent className="pt-6">
                    {error && (
                        <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
                            {error}
                        </div>
                    )}

                    {showLinks && createdPoll ? (
                        <div className="space-y-6">
                            <Alert>
                                <Mail className="h-4 w-4" />
                                <AlertDescription>
                                    I'll send the meeting link to the participants myself. Here are the individual response links for each participant:
                                </AlertDescription>
                            </Alert>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold">Individual Response Links</h3>
                                {createdPoll.participants.map((participant: PollParticipant) => (
                                    <div key={participant.id} className="border rounded-lg p-4 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="font-medium">{participant.name}</p>
                                                <p className="text-sm text-gray-600">{participant.email}</p>
                                            </div>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => copyToClipboard(getResponseUrl(participant.response_token))}
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
                                <Button onClick={() => setMeetingSubView('list')}>
                                    Back to Polls
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {step === 1 && (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block font-semibold mb-1">Title</label>
                                        <input className="w-full border rounded px-3 py-2" value={title} onChange={e => setTitle(e.target.value)} required />
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Description</label>
                                        <textarea className="w-full border rounded px-3 py-2" value={description} onChange={e => setDescription(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="block font-semibold mb-1">Duration (minutes)</label>
                                        <input type="number" className="w-full border rounded px-3 py-2" value={duration} onChange={e => setDuration(Number(e.target.value))} min={1} required />
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
                                    <div>
                                        <label className="block font-semibold mb-1">Participants</label>
                                        <div className="flex flex-col sm:flex-row gap-2 mb-2">
                                            <input
                                                className="border rounded px-3 py-2"
                                                value={participantNameInput}
                                                onChange={e => setParticipantNameInput(e.target.value)}
                                                placeholder="Name"
                                                type="text"
                                            />
                                            <input
                                                className="border rounded px-3 py-2"
                                                value={participantEmailInput}
                                                onChange={e => setParticipantEmailInput(e.target.value)}
                                                placeholder="Email"
                                                type="email"
                                            />
                                            <button type="button" className="bg-teal-600 text-white px-3 py-2 rounded" onClick={addParticipant} disabled={!(participantNameInput.trim().length > 0 && /.+@.+\..+/.test(participantEmailInput))}>Add</button>
                                        </div>
                                        <ul className="flex flex-wrap gap-2">
                                            {participants.map(p => (
                                                <li key={p.email} className="bg-gray-100 px-2 py-1 rounded flex items-center">
                                                    <span>{p.name} ({p.email})</span>
                                                    <button type="button" className="ml-2 text-red-600" onClick={() => removeParticipant(p.email)}>&times;</button>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            )}
                            {step === 3 && (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block font-semibold mb-1">Time Slots</label>
                                        <div className="flex flex-col sm:flex-row gap-2 mb-2">
                                            <input
                                                className="flex-1 border rounded px-3 py-2"
                                                type="datetime-local"
                                                value={slotStart}
                                                onChange={e => setSlotStart(e.target.value)}
                                            />
                                            <input
                                                className="flex-1 border rounded px-3 py-2"
                                                type="datetime-local"
                                                value={slotEnd}
                                                onChange={e => setSlotEnd(e.target.value)}
                                            />
                                            <button type="button" className="bg-teal-600 text-white px-3 py-2 rounded" onClick={addTimeSlot} disabled={!slotStart || !slotEnd}>Add</button>
                                        </div>
                                        <ul className="space-y-1">
                                            {timeSlots.map((slot, idx) => (
                                                <li key={idx} className="flex items-center gap-2">
                                                    <span className="font-mono text-xs">{slot.start.replace("T", " ")} - {slot.end.slice(11, 16)} ({timeZone})</span>
                                                    <button type="button" className="text-red-600" onClick={() => removeTimeSlot(idx)}>&times;</button>
                                                </li>
                                            ))}
                                        </ul>
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

                            <div className="flex gap-2 justify-between">
                                {step > 1 && <Button type="button" variant="outline" onClick={prevStep}>Back</Button>}
                                {step < 4 && <Button type="button" onClick={nextStep} disabled={
                                    (step === 1 && !isStep1Valid) ||
                                    (step === 2 && !isStep2Valid) ||
                                    (step === 3 && !isStep3Valid)
                                }>Next</Button>}
                                {step === 4 && <Button type="submit" disabled={loading}>
                                    {loading ? "Creating..." : (sendEmails ? "Create & Send" : "Generate Poll")}
                                </Button>}
                            </div>
                        </form>
                    )}
                </CardContent>
            </Card>
        </div>
    );
} 