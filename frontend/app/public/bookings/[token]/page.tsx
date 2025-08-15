"use client";

import { env } from '@/lib/env';
import { useEffect, useMemo, useState, use } from "react";

interface BookingMeta {
    title: string;
    description: string;
    template_questions: QuestionField[];
    duration_options: number[];
    is_active: boolean;
}

interface QuestionField {
    id: string;
    label: string;
    required: boolean;
    type: string;
    options?: string[];
    placeholder?: string;
    validation?: string;
}

interface TimeSlot {
    start: string;
    end: string;
    available: boolean;
}



export default function PublicBookingPage({ params }: { params: Promise<{ token: string }> }) {
    const { token } = use(params);
    const timezone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone, []);
    const durationOptions = useMemo(() => [15, 30, 60, 120], []);
    const [duration, setDuration] = useState<number>(30);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [meta, setMeta] = useState<BookingMeta | null>(null);
    const [slotLoading, setSlotLoading] = useState<boolean>(false);
    const [slots, setSlots] = useState<TimeSlot[]>([]);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);
        setError(null);
        fetch(`${env.GATEWAY_URL}/api/v1/bookings/public/${token}`)
            .then(async (res) => {
                if (!res.ok) {
                    throw new Error("Link not found or expired");
                }
                return res.json();
            })
            .then((data) => {
                if (!isMounted) return;
                setMeta(data?.data ?? null);
            })
            .catch((e) => {
                if (!isMounted) return;
                setError(e?.message || "Unable to load booking link");
            })
            .finally(() => {
                if (!isMounted) return;
                setLoading(false);
            });
        return () => {
            isMounted = false;
        };
    }, [token]);

    useEffect(() => {
        if (!meta) return;
        setSlotLoading(true);
        setSlots([]);
        fetch(`${env.GATEWAY_URL}/api/v1/bookings/public/${token}/availability?duration=${duration}`)
            .then(async (res) => {
                if (!res.ok) throw new Error("Failed to fetch availability");
                return res.json();
            })
            .then((data) => setSlots(data?.data?.slots || []))
            .catch(() => setSlots([]))
            .finally(() => setSlotLoading(false));
    }, [meta, token, duration]);

    return (
        <div className="p-6">
            <h1 className="text-2xl font-semibold">Public Booking</h1>
            <p className="text-sm text-muted-foreground mb-4">Token: {token}</p>

            {loading && <p className="text-sm">Loading…</p>}
            {!loading && error && (
                <div className="border border-red-200 bg-red-50 text-red-700 p-3 rounded mb-4">
                    {error}
                </div>
            )}
            {!loading && !error && !meta && (
                <div className="border bg-yellow-50 text-yellow-800 p-3 rounded mb-4">
                    Link not found.
                </div>
            )}

            {!loading && !error && meta && (
                <div className="border border-blue-200 bg-blue-50 text-blue-800 p-3 rounded mb-4">
                    <p className="text-sm">
                        <strong>Important:</strong> Please provide a valid email address to receive your booking confirmation.
                    </p>
                </div>
            )}

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-1">Meeting duration</label>
                    <select
                        className="border rounded px-2 py-1"
                        value={duration}
                        onChange={(e) => setDuration(Number(e.target.value))}
                    >
                        {durationOptions.map((d) => (
                            <option key={d} value={d}>
                                {d} minutes
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-1">Your timezone</label>
                    <input
                        className="border rounded px-2 py-1 w-full"
                        value={timezone}
                        readOnly
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                        Detected automatically.
                    </p>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-1">Available slots</label>
                    {slotLoading && <p className="text-sm">Loading slots…</p>}
                    {!slotLoading && slots.length === 0 && (
                        <p className="text-sm text-muted-foreground">No slots available.</p>
                    )}
                    {!slotLoading && slots.length > 0 && (
                        <ul className="space-y-2">
                            {slots.slice(0, 10).map((s, i) => (
                                <li
                                    key={i}
                                    className={`border rounded p-2 text-sm cursor-pointer ${selectedSlot === s ? "ring-2 ring-blue-500" : ""
                                        }`}
                                    onClick={() => setSelectedSlot(s)}
                                >
                                    {s.start} → {s.end}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {Array.isArray(meta?.template_questions) && meta.template_questions.length > 0 && (
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Questions
                            <span className="text-xs text-muted-foreground ml-2">
                                Fields marked with * are required
                            </span>
                        </label>
                        <div className="space-y-3">
                            {meta.template_questions.map((q: QuestionField, idx: number) => {
                                const key = q?.id || `q_${idx}`;
                                const label = q?.label || `Question ${idx + 1}`;
                                const required = Boolean(q?.required);
                                const hasError = required && (!answers[key] || answers[key].trim() === '');
                                const isEmail = q.type === 'email';
                                
                                return (
                                    <div key={key} className="flex flex-col gap-1">
                                        <span className="text-sm font-medium">
                                            {label}
                                            {required && <span className="text-red-500 ml-1">*</span>}
                                        </span>
                                        <input
                                            type={isEmail ? "email" : "text"}
                                            placeholder={isEmail ? "Enter your email address" : `Enter your ${label.toLowerCase()}`}
                                            className={`border rounded px-3 py-2 ${
                                                hasError ? 'border-red-300 bg-red-50' : 'border-gray-300'
                                            }`}
                                            value={answers[key] || ""}
                                            onChange={(e) =>
                                                setAnswers((prev) => ({ ...prev, [key]: e.target.value }))
                                            }
                                            onBlur={() => {
                                                // Trigger validation on blur
                                                if (required && (!answers[key] || answers[key].trim() === '')) {
                                                    // Field is already marked as having error
                                                }
                                            }}
                                        />
                                        {hasError && (
                                            <span className="text-xs text-red-500">
                                                This field is required
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
                <div>
                    <button
                        disabled={!selectedSlot || submitting}
                        className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
                        onClick={async () => {
                            if (!selectedSlot) return;
                            
                            // Validate required fields before submission
                            const requiredFields = meta?.template_questions?.filter(q => q.required) || [];
                            const missingFields = requiredFields.filter(q => !answers[q.id] || answers[q.id].trim() === '');
                            
                            if (missingFields.length > 0) {
                                const fieldNames = missingFields.map(q => q.label).join(', ');
                                alert(`Please fill in all required fields: ${fieldNames}`);
                                return;
                            }
                            
                            // Ensure email is provided for confirmation emails
                            if (!answers.email || answers.email.trim() === '') {
                                alert('Email address is required to receive booking confirmation.');
                                return;
                            }
                            
                            setSubmitting(true);
                            try {
                                const res = await fetch(`${env.GATEWAY_URL}/api/v1/bookings/public/${token}/book`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({
                                        start: selectedSlot.start,
                                        end: selectedSlot.end,
                                        attendeeEmail: answers.email,
                                        answers,
                                    }),
                                });
                                if (!res.ok) throw new Error("Failed to book");
                                alert("Booked! Check your email for confirmation.");
                            } catch (e) {
                                const errorMessage = e instanceof Error ? e.message : "Booking failed";
                                alert(errorMessage);
                            } finally {
                                setSubmitting(false);
                            }
                        }}
                    >
                        {submitting ? "Booking…" : "Book selected slot"}
                    </button>
                </div>
            </div>
        </div>
    );
}


