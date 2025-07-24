"use client";
import gatewayClient from "@/lib/gateway-client";
import { useRouter } from "next/navigation";
import { useState } from "react";

const getTimeZones = () =>
    Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : ["UTC"];

export default function NewMeetingPollPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    // Step 1: Basic Info
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState(60);
    const [location, setLocation] = useState("");
    const [timeZone, setTimeZone] = useState("UTC");
    // Step 2: Participants
    const [participants, setParticipants] = useState<string[]>([]);
    const [participantInput, setParticipantInput] = useState("");
    // Step 3: Time Slots
    const [timeSlots, setTimeSlots] = useState<{ start: string; end: string }[]>([]);
    const [slotStart, setSlotStart] = useState("");
    const [slotEnd, setSlotEnd] = useState("");
    // General
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Validation helpers
    const isStep1Valid = title && duration > 0 && timeZone;
    const isStep2Valid = participants.length > 0 && participants.every(e => /.+@.+\..+/.test(e));
    const isStep3Valid = timeSlots.length > 0 && timeSlots.every(s => s.start && s.end);

    // Step navigation
    const nextStep = () => setStep((s) => s + 1);
    const prevStep = () => setStep((s) => s - 1);

    // Add participant
    const addParticipant = () => {
        if (participantInput && /.+@.+\..+/.test(participantInput) && !participants.includes(participantInput)) {
            setParticipants([...participants, participantInput]);
            setParticipantInput("");
        }
    };
    const removeParticipant = (email: string) => setParticipants(participants.filter(e => e !== email));

    // Add time slot
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
                time_slots: timeSlots.map((s) => ({ start_time: s.start, end_time: s.end, timezone: timeZone })),
                participants: participants.map((email) => ({ email })),
            };
            await gatewayClient.createMeetingPoll(pollData);
            router.push("/dashboard/meetings");
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

    return (
        <div className="max-w-xl mx-auto p-4 sm:p-8">
            <h1 className="text-2xl font-bold mb-6">Create New Meeting Poll</h1>
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
                                {getTimeZones().map((tz) => (
                                    <option key={tz} value={tz}>{tz}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}
                {step === 2 && (
                    <div className="space-y-4">
                        <div>
                            <label className="block font-semibold mb-1">Participants (emails)</label>
                            <div className="flex gap-2 mb-2">
                                <input
                                    className="flex-1 border rounded px-3 py-2"
                                    value={participantInput}
                                    onChange={e => setParticipantInput(e.target.value)}
                                    placeholder="Add email"
                                    type="email"
                                />
                                <button type="button" className="bg-teal-600 text-white px-3 py-2 rounded" onClick={addParticipant} disabled={!/.+@.+\..+/.test(participantInput)}>Add</button>
                            </div>
                            <ul className="flex flex-wrap gap-2">
                                {participants.map(email => (
                                    <li key={email} className="bg-gray-100 px-2 py-1 rounded flex items-center">
                                        <span>{email}</span>
                                        <button type="button" className="ml-2 text-red-600" onClick={() => removeParticipant(email)}>&times;</button>
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
                        <div><b>Participants:</b> {participants.join(", ")}</div>
                        <div><b>Time Slots:</b>
                            <ul className="ml-4 list-disc">
                                {timeSlots.map((slot, idx) => (
                                    <li key={idx}>{slot.start.replace("T", " ")} - {slot.end.slice(11, 16)} ({timeZone})</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}
                {error && <div className="text-red-600">{error}</div>}
                <div className="flex gap-2 justify-between">
                    {step > 1 && <button type="button" className="bg-gray-200 px-4 py-2 rounded" onClick={prevStep}>Back</button>}
                    {step < 4 && <button type="button" className="bg-teal-600 text-white px-4 py-2 rounded" onClick={nextStep} disabled={
                        (step === 1 && !isStep1Valid) ||
                        (step === 2 && !isStep2Valid) ||
                        (step === 3 && !isStep3Valid)
                    }>Next</button>}
                    {step === 4 && <button type="submit" className="bg-teal-600 text-white px-4 py-2 rounded" disabled={loading}>{loading ? "Creating..." : "Create Poll"}</button>}
                </div>
            </form>
        </div>
    );
} 