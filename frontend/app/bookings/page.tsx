"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { gatewayClient } from "@/lib/gateway-client";
import type { BookingLink } from "@/types/bookings";
import { CheckCircle } from "lucide-react";
import { useEffect, useState } from "react";

type Step = "basics" | "availability" | "duration" | "limits" | "template" | "review";

type WeekdayKey = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

type BusinessHours = {
    [K in WeekdayKey]: { start: string; end: string; enabled: boolean };
};

export default function BookingsPage() {
    const [currentStep, setCurrentStep] = useState<Step>("basics");
    const [activeTab, setActiveTab] = useState<"create" | "manage">("create");
    const [manageView, setManageView] = useState<"links" | "bookings" | "analytics">("links");
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        duration: 30,
        bufferBefore: 0,
        bufferAfter: 0,
        maxPerDay: 3,
        maxPerWeek: 10,
        advanceDays: 1,
        maxAdvanceDays: 30,
        templateName: "",
        questions: [],
        emailFollowup: false,
        isSingleUse: false,
        recipientEmail: "",
        recipientName: "",
        businessHours: {
            monday: { start: "09:00", end: "17:00", enabled: true },
            tuesday: { start: "09:00", end: "17:00", enabled: true },
            wednesday: { start: "09:00", end: "17:00", enabled: true },
            thursday: { start: "09:00", end: "17:00", enabled: true },
            friday: { start: "09:00", end: "17:00", enabled: true },
            saturday: { start: "10:00", end: "14:00", enabled: false },
            sunday: { start: "10:00", end: "14:00", enabled: false },
        },
        holidayExclusions: [] as string[],
        durationPresets: [15, 30, 60, 120],
        customDuration: null as number | null,
        lastMinuteCutoff: 2, // hours
        expiresInDays: 7, // for both evergreen and single-use
    });

    // Real data state
    const [existingLinks, setExistingLinks] = useState<BookingLink[]>([]);
    const [bookings, setBookings] = useState<any[]>([]);
    const [analyticsData, setAnalyticsData] = useState<any[]>([]);

    // Filter state for bookings
    const [bookingsFilter, setBookingsFilter] = useState<string | null>(null); // link_id to filter by

    // Loading and error states
    const [isLoadingLinks, setIsLoadingLinks] = useState(false);
    const [isLoadingBookings, setIsLoadingBookings] = useState(false);
    const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
    const [linksError, setLinksError] = useState<string | null>(null);
    const [bookingsError, setBookingsError] = useState<string | null>(null);
    const [analyticsError, setAnalyticsError] = useState<string | null>(null);

    // Success dialog state
    const [showSuccessDialog, setShowSuccessDialog] = useState(false);
    const [successData, setSuccessData] = useState<{
        title: string;
        message: string;
        publicUrl: string;
        slug: string;
        bookingTitle: string;
        createdAt: string;
    } | null>(null);

    // Data fetching functions
    const fetchLinks = async () => {
        try {
            setIsLoadingLinks(true);
            setLinksError(null);
            const result = await gatewayClient.listBookingLinks();
            setExistingLinks(result.data);
        } catch (error) {
            setLinksError(error instanceof Error ? error.message : 'Failed to fetch links');
            console.error('Error fetching links:', error);
        } finally {
            setIsLoadingLinks(false);
        }
    };

    const fetchBookings = async () => {
        try {
            setIsLoadingBookings(true);
            setBookingsError(null);
            // TODO: Implement when backend endpoint is ready
            // const result = await gatewayClient.listBookings();
            // setBookings(result.data);
            setBookings([]); // Empty for now
        } catch (error) {
            setBookingsError(error instanceof Error ? error.message : 'Failed to fetch bookings');
            console.error('Error fetching bookings:', error);
        } finally {
            setIsLoadingBookings(false);
        }
    };

    const fetchAnalytics = async () => {
        try {
            setIsLoadingAnalytics(true);
            setAnalyticsError(null);
            // TODO: Implement when backend endpoint is ready
            // const result = await gatewayClient.getAnalytics();
            // setAnalyticsData(result.data);
            setAnalyticsData([]); // Empty for now
        } catch (error) {
            setAnalyticsError(error instanceof Error ? error.message : 'Failed to fetch analytics');
            console.error('Error fetching analytics:', error);
        } finally {
            setIsLoadingAnalytics(false);
        }
    };

    // Load data when component mounts or tab changes
    useEffect(() => {
        if (activeTab === "manage") {
            fetchLinks();
            fetchBookings();
            fetchAnalytics();
        }
    }, [activeTab]);

    const steps: { key: Step; label: string }[] = [
        { key: "basics", label: "Basics" },
        { key: "availability", label: "Availability" },
        { key: "duration", label: "Duration & Buffer" },
        { key: "limits", label: "Limits" },
        { key: "template", label: "Template" },
        { key: "review", label: "Review" },
    ];

    const weekdays = [
        { key: "monday", label: "Monday" },
        { key: "tuesday", label: "Tuesday" },
        { key: "wednesday", label: "Wednesday" },
        { key: "thursday", label: "Thursday" },
        { key: "friday", label: "Friday" },
        { key: "saturday", label: "Saturday" },
        { key: "sunday", label: "Sunday" },
    ];

    const renderStep = () => {
        switch (currentStep) {
            case "basics":
                return (
                    <div className="space-y-4">
                        <h2 className="text-xl font-semibold">Basic Information</h2>
                        <div>
                            <label className="block text-sm font-medium mb-1">Title *</label>
                            <input
                                className="border rounded px-3 py-2 w-full"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                placeholder="e.g., Coffee Chat, Consultation"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Description</label>
                            <textarea
                                className="border rounded px-3 py-2 w-full"
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Optional description for recipients"
                            />
                        </div>

                        {/* Link Type Toggle */}
                        <div className="border rounded-lg p-4 bg-gray-50">
                            <h3 className="text-lg font-medium mb-3">Link Type</h3>
                            <div className="space-y-3">
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="linkType"
                                        checked={!formData.isSingleUse}
                                        onChange={() => setFormData({ ...formData, isSingleUse: false })}
                                        className="w-4 h-4 text-blue-600"
                                    />
                                    <div>
                                        <span className="font-medium">Persistent Link</span>
                                        <p className="text-sm text-muted-foreground">Create a reusable link that anyone can use to book time</p>
                                    </div>
                                </label>
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="linkType"
                                        checked={formData.isSingleUse}
                                        onChange={() => setFormData({ ...formData, isSingleUse: true })}
                                        className="w-4 h-4 text-blue-600"
                                    />
                                    <div>
                                        <span className="font-medium">Single-Use Link</span>
                                        <p className="text-sm text-muted-foreground">Create a one-time link for a specific recipient</p>
                                    </div>
                                </label>
                            </div>
                        </div>

                        {/* Recipient Information (only for single-use) */}
                        {formData.isSingleUse && (
                            <div className="border rounded-lg p-4 bg-blue-50">
                                <h3 className="text-lg font-medium mb-3">Recipient Information</h3>
                                <div className="space-y-3">
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Recipient Email *</label>
                                        <input
                                            type="email"
                                            className="border rounded px-3 py-2 w-full"
                                            value={formData.recipientEmail}
                                            onChange={(e) => setFormData({ ...formData, recipientEmail: e.target.value })}
                                            placeholder="recipient@example.com"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Recipient Name</label>
                                        <input
                                            type="text"
                                            className="border rounded px-3 py-2 w-full"
                                            value={formData.recipientName}
                                            onChange={(e) => setFormData({ ...formData, recipientName: e.target.value })}
                                            placeholder="Optional name"
                                        />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                );

            case "availability":
                return (
                    <div className="space-y-6">
                        <h2 className="text-xl font-semibold">Availability Settings</h2>

                        {/* Business Hours */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Business Hours</h3>
                            <div className="space-y-3">
                                {weekdays.map((day) => (
                                    <div key={day.key} className="flex items-center gap-4">
                                        <div className="w-24">
                                            <label className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.businessHours[day.key as keyof BusinessHours].enabled}
                                                    onChange={(e) => {
                                                        const newHours = { ...formData.businessHours };
                                                        newHours[day.key as keyof BusinessHours].enabled = e.target.checked;
                                                        setFormData({ ...formData, businessHours: newHours });
                                                    }}
                                                />
                                                <span className="text-sm font-medium">{day.label}</span>
                                            </label>
                                        </div>
                                        {formData.businessHours[day.key as keyof BusinessHours].enabled && (
                                            <>
                                                <input
                                                    type="time"
                                                    className="border rounded px-2 py-1"
                                                    value={formData.businessHours[day.key as keyof BusinessHours].start}
                                                    onChange={(e) => {
                                                        const newHours = { ...formData.businessHours };
                                                        newHours[day.key as keyof BusinessHours].start = e.target.value;
                                                        setFormData({ ...formData, businessHours: newHours });
                                                    }}
                                                />
                                                <span className="text-sm text-muted-foreground">to</span>
                                                <input
                                                    type="time"
                                                    className="border rounded px-2 py-1"
                                                    value={formData.businessHours[day.key as keyof BusinessHours].end}
                                                    onChange={(e) => {
                                                        const newHours = { ...formData.businessHours };
                                                        newHours[day.key as keyof BusinessHours].end = e.target.value;
                                                        setFormData({ ...formData, businessHours: newHours });
                                                    }}
                                                />
                                            </>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Holiday Exclusions */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Holiday & Vacation Exclusions</h3>
                            <p className="text-sm text-muted-foreground mb-2">
                                Add dates when you're not available for bookings
                            </p>
                            <div className="space-y-2">
                                {formData.holidayExclusions.map((date, index) => (
                                    <div key={index} className="flex items-center gap-2">
                                        <input
                                            type="date"
                                            className="border rounded px-2 py-1"
                                            value={date}
                                            onChange={(e) => {
                                                const newExclusions = [...formData.holidayExclusions];
                                                newExclusions[index] = e.target.value;
                                                setFormData({ ...formData, holidayExclusions: newExclusions });
                                            }}
                                        />
                                        <button
                                            className="px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                                            onClick={() => {
                                                const newExclusions = formData.holidayExclusions.filter((_, i) => i !== index);
                                                setFormData({ ...formData, holidayExclusions: newExclusions });
                                            }}
                                        >
                                            Remove
                                        </button>
                                    </div>
                                ))}
                                <button
                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                    onClick={() => {
                                        const today = new Date().toISOString().split('T')[0];
                                        setFormData({
                                            ...formData,
                                            holidayExclusions: [...formData.holidayExclusions, today]
                                        });
                                    }}
                                >
                                    + Add Date
                                </button>
                            </div>
                        </div>

                        {/* Advance Booking */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Advance Booking (days)</label>
                                <input
                                    type="number"
                                    className="border rounded px-3 py-2 w-full"
                                    value={formData.advanceDays}
                                    onChange={(e) => setFormData({ ...formData, advanceDays: Number(e.target.value) })}
                                    min="0"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Max Advance (days)</label>
                                <input
                                    type="number"
                                    className="border rounded px-3 py-2 w-full"
                                    value={formData.maxAdvanceDays}
                                    onChange={(e) => setFormData({ ...formData, maxAdvanceDays: Number(e.target.value) })}
                                    min="1"
                                />
                            </div>
                        </div>

                        {/* Last Minute Cutoff */}
                        <div>
                            <label className="block text-sm font-medium mb-1">Last Minute Cutoff (hours)</label>
                            <input
                                type="number"
                                className="border rounded px-3 py-2 w-full"
                                value={formData.lastMinuteCutoff}
                                onChange={(e) => setFormData({ ...formData, lastMinuteCutoff: Number(e.target.value) })}
                                min="0"
                                max="24"
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                                Minimum time required before a meeting (e.g., 2 hours = no same-day bookings)
                            </p>
                        </div>

                        {/* Link Expiry */}
                        <div>
                            <label className="block text-sm font-medium mb-1">Link Expiry (days)</label>
                            <select
                                className="border rounded px-3 py-2 w-full"
                                value={formData.expiresInDays}
                                onChange={(e) => setFormData({ ...formData, expiresInDays: Number(e.target.value) })}
                            >
                                <option value={1}>1 day</option>
                                <option value={3}>3 days</option>
                                <option value={7}>1 week</option>
                                <option value={14}>2 weeks</option>
                                <option value={30}>1 month</option>
                                <option value={90}>3 months</option>
                                <option value={365}>1 year</option>
                                <option value={0}>Never expire</option>
                            </select>
                            <p className="text-xs text-muted-foreground mt-1">
                                {formData.expiresInDays === 0
                                    ? "This link will never expire"
                                    : `This link will expire ${formData.expiresInDays} day${formData.expiresInDays === 1 ? '' : 's'} after creation`
                                }
                            </p>
                        </div>
                    </div>
                );

            case "duration":
                return (
                    <div className="space-y-6">
                        <h2 className="text-xl font-semibold">Duration & Buffer</h2>

                        {/* Duration Presets */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Meeting Duration</h3>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                {formData.durationPresets.map((preset) => (
                                    <label key={preset} className="flex items-center gap-2 p-3 border rounded cursor-pointer hover:bg-gray-50">
                                        <input
                                            type="radio"
                                            name="duration"
                                            value={preset}
                                            checked={formData.duration === preset}
                                            onChange={(e) => setFormData({ ...formData, duration: Number(e.target.value) })}
                                        />
                                        <span className="font-medium">{preset} minutes</span>
                                    </label>
                                ))}
                            </div>

                            {/* Custom Duration */}
                            <div>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="radio"
                                        name="duration"
                                        checked={formData.customDuration !== null}
                                        onChange={() => setFormData({ ...formData, customDuration: formData.customDuration || 45 })}
                                    />
                                    <span className="font-medium">Custom duration</span>
                                </label>
                                {formData.customDuration !== null && (
                                    <div className="mt-2 ml-6">
                                        <input
                                            type="number"
                                            className="border rounded px-3 py-2 w-32"
                                            value={formData.customDuration}
                                            onChange={(e) => setFormData({ ...formData, customDuration: Number(e.target.value) })}
                                            min="5"
                                            max="480"
                                            step="5"
                                        />
                                        <span className="ml-2 text-sm text-muted-foreground">minutes</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Buffers */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Buffer Time</h3>
                            <p className="text-sm text-muted-foreground mb-3">
                                Add time before and after meetings to prevent back-to-back scheduling
                            </p>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Buffer Before (minutes)</label>
                                    <input
                                        type="number"
                                        className="border rounded px-3 py-2 w-full"
                                        value={formData.bufferBefore}
                                        onChange={(e) => setFormData({ ...formData, bufferBefore: Number(e.target.value) })}
                                        min="0"
                                        max="60"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Buffer After (minutes)</label>
                                    <input
                                        type="number"
                                        className="border rounded px-3 py-2 w-full"
                                        value={formData.bufferAfter}
                                        onChange={(e) => setFormData({ ...formData, bufferAfter: Number(e.target.value) })}
                                        min="0"
                                        max="60"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                );

            case "limits":
                return (
                    <div className="space-y-6">
                        <h2 className="text-xl font-semibold">Booking Limits</h2>

                        {/* Daily/Weekly Limits */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Meeting Frequency Limits</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Max per Day</label>
                                    <input
                                        type="number"
                                        className="border rounded px-3 py-2 w-full"
                                        value={formData.maxPerDay}
                                        onChange={(e) => setFormData({ ...formData, maxPerDay: Number(e.target.value) })}
                                        min="1"
                                        max="20"
                                    />
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Maximum meetings per day
                                    </p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Max per Week</label>
                                    <input
                                        type="number"
                                        className="border rounded px-3 py-2 w-full"
                                        value={formData.maxPerWeek}
                                        onChange={(e) => setFormData({ ...formData, maxPerWeek: Number(e.target.value) })}
                                        min="1"
                                        max="100"
                                    />
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Maximum meetings per week
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Time-based Restrictions */}
                        <div>
                            <h3 className="text-lg font-medium mb-3">Time Restrictions</h3>
                            <div className="space-y-3">
                                <div>
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={formData.lastMinuteCutoff > 0}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setFormData({ ...formData, lastMinuteCutoff: 2 });
                                                } else {
                                                    setFormData({ ...formData, lastMinuteCutoff: 0 });
                                                }
                                            }}
                                        />
                                        <span className="text-sm font-medium">Enforce last-minute cutoff</span>
                                    </label>
                                    {formData.lastMinuteCutoff > 0 && (
                                        <p className="text-xs text-muted-foreground ml-6 mt-1">
                                            Currently set to {formData.lastMinuteCutoff} hours before meeting time
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                );

            case "template":
                return (
                    <div className="space-y-4">
                        <h2 className="text-xl font-semibold">Template & Questions</h2>
                        <div>
                            <label className="block text-sm font-medium mb-1">Template Name</label>
                            <input
                                className="border rounded px-3 py-2 w-full"
                                value={formData.templateName}
                                onChange={(e) => setFormData({ ...formData, templateName: e.target.value })}
                                placeholder="e.g., Interview, Consultation"
                            />
                        </div>
                        <div>
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={formData.emailFollowup}
                                    onChange={(e) => setFormData({ ...formData, emailFollowup: e.target.checked })}
                                />
                                <span className="text-sm font-medium">Send follow-up email after booking</span>
                            </label>
                        </div>
                    </div>
                );

            case "review":
                const effectiveDuration = formData.customDuration || formData.duration;
                const activeDays = Object.values(formData.businessHours).filter(h => h.enabled).length;

                return (
                    <div className="space-y-4">
                        <h2 className="text-xl font-semibold">Review & Create</h2>
                        <div className="bg-gray-50 p-4 rounded space-y-3">
                            <h3 className="font-medium">{formData.title}</h3>
                            {formData.description && <p className="text-sm text-muted-foreground">{formData.description}</p>}

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>Duration: {effectiveDuration} minutes</div>
                                <div>Buffer: {formData.bufferBefore}m before, {formData.bufferAfter}m after</div>
                                <div>Max per day: {formData.maxPerDay}</div>
                                <div>Max per week: {formData.maxPerWeek}</div>
                                <div>Advance booking: {formData.advanceDays} days</div>
                                <div>Max advance: {formData.maxAdvanceDays} days</div>
                                <div>Business days: {activeDays}/7</div>
                                <div>Last-minute cutoff: {formData.lastMinuteCutoff}h</div>
                            </div>

                            {formData.holidayExclusions.length > 0 && (
                                <div>
                                    <p className="text-sm font-medium">Holiday exclusions: {formData.holidayExclusions.length} dates</p>
                                </div>
                            )}
                        </div>
                        <button
                            className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
                            onClick={async () => {
                                try {
                                    setIsLoading(true);
                                    const result = await gatewayClient.createBookingLink({
                                        title: formData.title,
                                        description: formData.description,
                                        duration: formData.duration,
                                        buffer_before: formData.bufferBefore,
                                        buffer_after: formData.bufferAfter,
                                        max_per_day: formData.maxPerDay,
                                        max_per_week: formData.maxPerWeek,
                                        advance_days: formData.advanceDays,
                                        max_advance_days: formData.maxAdvanceDays,
                                        business_hours: formData.businessHours,
                                        holiday_exclusions: formData.holidayExclusions,
                                        last_minute_cutoff: formData.lastMinuteCutoff,
                                        template_name: formData.questions.length > 0 ? "Custom Template" : undefined,
                                        questions: formData.questions.length > 0 ? formData.questions : undefined,
                                        emailFollowup: formData.emailFollowup,
                                        is_single_use: formData.isSingleUse,
                                        recipient_email: formData.isSingleUse ? formData.recipientEmail : undefined,
                                        recipient_name: formData.isSingleUse ? formData.recipientName : undefined,
                                        expires_in_days: formData.isSingleUse ? formData.expiresInDays : undefined,
                                    });

                                    // Show success dialog
                                    setSuccessData({
                                        title: "Booking Link Created Successfully!",
                                        message: "Your new booking link is ready to share with recipients.",
                                        publicUrl: result.data.public_url,
                                        slug: result.data.slug,
                                        bookingTitle: formData.title,
                                        createdAt: new Date().toISOString()
                                    });
                                    setShowSuccessDialog(true);
                                    setFormData({
                                        title: "",
                                        description: "",
                                        duration: 30,
                                        bufferBefore: 0,
                                        bufferAfter: 0,
                                        maxPerDay: 5,
                                        maxPerWeek: 20,
                                        advanceDays: 7,
                                        maxAdvanceDays: 90,
                                        templateName: "",
                                        questions: [],
                                        emailFollowup: false,
                                        isSingleUse: false,
                                        recipientEmail: "",
                                        recipientName: "",
                                        businessHours: {
                                            monday: { start: "09:00", end: "17:00", enabled: true },
                                            tuesday: { start: "09:00", end: "17:00", enabled: true },
                                            wednesday: { start: "09:00", end: "17:00", enabled: true },
                                            thursday: { start: "09:00", end: "17:00", enabled: true },
                                            friday: { start: "09:00", end: "17:00", enabled: true },
                                            saturday: { start: "10:00", end: "14:00", enabled: false },
                                            sunday: { start: "10:00", end: "14:00", enabled: false },
                                        },
                                        holidayExclusions: [],
                                        durationPresets: [15, 30, 60, 120],
                                        customDuration: null,
                                        lastMinuteCutoff: 2,
                                        expiresInDays: 7,
                                    });
                                    setCurrentStep("basics");
                                } catch (error) {
                                    alert(`Error creating booking link: ${error instanceof Error ? error.message : 'Unknown error'}`);
                                } finally {
                                    setIsLoading(false);
                                }
                            }}
                        >
                            Create Booking Link
                        </button>
                    </div>
                );

            default:
                return null;
        }
    };

    const canGoNext = () => {
        if (currentStep === "basics") {
            const hasTitle = formData.title.trim().length > 0;
            if (formData.isSingleUse) {
                return hasTitle && formData.recipientEmail.trim().length > 0;
            }
            return hasTitle;
        }
        if (currentStep === "review") return false;
        return true;
    };

    const canGoBack = () => currentStep !== "basics";

    const goNext = () => {
        const currentIndex = steps.findIndex(s => s.key === currentStep);
        if (currentIndex < steps.length - 1) {
            setCurrentStep(steps[currentIndex + 1].key);
        }
    };

    const goBack = () => {
        const currentIndex = steps.findIndex(s => s.key === currentStep);
        if (currentIndex > 0) {
            setCurrentStep(steps[currentIndex - 1].key);
        }
    };

    const toggleLinkStatus = async (linkId: string) => {
        try {
            console.log('Toggling link status for:', linkId);

            // Optimistically update the UI for better user experience
            setExistingLinks(prev => prev.map(link =>
                link.id === linkId
                    ? { ...link, is_active: !link.is_active }
                    : link
            ));

            const result = await gatewayClient.toggleBookingLink(linkId);
            console.log('Toggle API response:', result);

            // Refresh the links list to ensure consistency with backend
            await fetchLinks();
        } catch (error) {
            console.error('Error toggling link status:', error);

            // Revert the optimistic update on error
            setExistingLinks(prev => prev.map(link =>
                link.id === linkId
                    ? { ...link, is_active: !link.is_active }
                    : link
            ));
            alert(`Error toggling link status: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const duplicateLink = async (linkId: string) => {
        try {
            const result = await gatewayClient.duplicateBookingLink(linkId);
            // Find the original link to get its title for the success message
            const originalLink = existingLinks.find(l => l.id === linkId);
            setSuccessData({
                title: "Link Duplicated Successfully!",
                message: `A copy of "${originalLink?.settings?.title || `Untitled Link (${originalLink?.slug.slice(0, 8)}...)`}" has been created.`,
                publicUrl: `${window.location.origin}/public/bookings/${result.data.slug}`,
                slug: result.data.slug,
                bookingTitle: originalLink?.settings?.title || `Untitled Link (${originalLink?.slug.slice(0, 8)}...)`,
                createdAt: new Date().toISOString()
            });
            setShowSuccessDialog(true);
            // Refresh the links list
            await fetchLinks();
        } catch (error) {
            alert(`Error duplicating link: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const editLink = (linkId: string) => {
        // TODO: Navigate to edit mode - this would require implementing an edit form
        alert(`Editing link ${linkId}... (edit mode pending - would navigate to edit form)`);
    };

    const viewLinkBookings = (linkId: string) => {
        setBookingsFilter(linkId);
        setManageView("bookings");
    };

    const formatDateTime = (dateTimeString: string) => {
        const date = new Date(dateTimeString);
        return date.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            timeZoneName: 'short'
        });
    };

    // Render manage view
    const renderManageView = () => (
        <div className="p-4 sm:p-6 max-w-6xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <h1 className="text-xl sm:text-2xl font-semibold">Manage Booking Links</h1>
                <button
                    className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    onClick={() => setActiveTab("create")}
                >
                    Create New Link
                </button>
            </div>

            {/* Tab navigation */}
            <div className="flex border-b mb-6 overflow-x-auto">
                <button
                    className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${manageView === "links"
                        ? "border-blue-500 text-blue-600"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                        }`}
                    onClick={() => setManageView("links")}
                >
                    Links
                </button>
                <button
                    className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${manageView === "bookings"
                        ? "border-blue-500 text-blue-600"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                        }`}
                    onClick={() => setManageView("bookings")}
                >
                    Bookings
                </button>
                <button
                    className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${manageView === "analytics"
                        ? "border-blue-500 text-blue-600"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                        }`}
                    onClick={() => setManageView("analytics")}
                >
                    Analytics
                </button>
            </div>

            {manageView === "links" ? (
                <>
                    {/* Links list */}
                    <div className="bg-white border rounded-lg overflow-hidden">
                        <div className="px-4 sm:px-6 py-4 border-b bg-gray-50">
                            <h2 className="font-medium">Your Booking Links</h2>
                        </div>

                        {isLoadingLinks ? (
                            <div className="px-4 sm:px-6 py-8 text-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                                <p className="text-gray-500">Loading booking links...</p>
                            </div>
                        ) : linksError ? (
                            <div className="px-4 sm:px-6 py-8 text-center">
                                <p className="text-red-500 mb-4">{linksError}</p>
                                <button
                                    onClick={fetchLinks}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Retry
                                </button>
                            </div>
                        ) : existingLinks.length === 0 ? (
                            <div className="px-4 sm:px-6 py-8 text-center">
                                <p className="text-gray-500 mb-4">No booking links found</p>
                                <button
                                    onClick={() => setActiveTab("create")}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Create Your First Link
                                </button>
                            </div>
                        ) : (
                            <div className="divide-y">
                                {existingLinks.map((link) => (
                                    <div key={link.id} className="px-4 sm:px-6 py-4">
                                        {/* Responsive 2x2 grid layout */}
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                            {/* Upper Left: Title and Status */}
                                            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                                                <h3 className="font-medium text-lg">
                                                    {link.settings?.title || `Untitled Link (${link.slug.slice(0, 8)}...)`}
                                                </h3>
                                                <span className={`px-2 py-1 text-xs rounded-full w-fit ${link.is_active
                                                    ? "bg-green-100 text-green-800"
                                                    : "bg-gray-100 text-gray-800"
                                                    }`}>
                                                    {link.is_active ? "Active" : "Inactive"}
                                                </span>
                                            </div>

                                            {/* Upper Right: URL and Copy Button */}
                                            <div className="flex items-center gap-2 justify-end lg:justify-start">
                                                <span className="text-xs font-medium text-gray-700">URL:</span>
                                                <a
                                                    href={`/public/bookings/${link.slug}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-sm text-blue-600 hover:text-blue-800 truncate flex-1"
                                                >
                                                    {`${window.location.origin}/public/bookings/${link.slug}`}
                                                </a>
                                                <button
                                                    onClick={(e) => {
                                                        const publicUrl = `${window.location.origin}/public/bookings/${link.slug}`;
                                                        navigator.clipboard.writeText(publicUrl).then(() => {
                                                            // Show temporary success feedback
                                                            const button = e.currentTarget;
                                                            const originalText = button.textContent;
                                                            button.textContent = 'Copied!';
                                                            button.className = 'px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700';
                                                            setTimeout(() => {
                                                                button.textContent = originalText;
                                                                button.className = 'px-2 py-1 text-xs border rounded hover:bg-gray-50';
                                                            }, 2000);
                                                        }).catch(err => {
                                                            console.error('Failed to copy: ', err);
                                                            alert('Failed to copy link to clipboard');
                                                        });
                                                    }}
                                                    className="px-2 py-1 text-xs border rounded hover:bg-gray-50 flex-shrink-0"
                                                    title="Copy link"
                                                >
                                                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                                                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                                                    </svg>
                                                </button>
                                            </div>

                                            {/* Lower Left: Stats */}
                                            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm">
                                                <span>Created: {formatDateTime(link.created_at)}</span>
                                                <span>Total bookings: {link.total_bookings}</span>
                                                <span>Conversion: {link.conversion_rate}</span>
                                            </div>

                                            {/* Lower Right: Action Buttons */}
                                            <div className="flex flex-wrap gap-2 justify-end lg:justify-start">
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => toggleLinkStatus(link.id)}
                                                >
                                                    {link.is_active ? "Disable" : "Enable"}
                                                </button>
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => duplicateLink(link.id)}
                                                >
                                                    Duplicate
                                                </button>
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => editLink(link.id)}
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => viewLinkBookings(link.id)}
                                                >
                                                    View
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Quick stats */}
                    <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Total Links</h3>
                            <p className="text-2xl font-semibold">{existingLinks.length}</p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Active Links</h3>
                            <p className="text-2xl font-semibold">{existingLinks.filter(l => l.is_active).length}</p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Total Bookings</h3>
                            <p className="text-2xl font-semibold">{existingLinks.reduce((sum, l) => sum + l.total_bookings, 0)}</p>
                        </div>
                    </div>
                </>
            ) : manageView === "bookings" ? (
                <>
                    {/* Bookings list */}
                    <div className="bg-white border rounded-lg overflow-hidden">
                        <div className="px-4 sm:px-6 py-4 border-b bg-gray-50">
                            <div className="flex items-center justify-between">
                                <h2 className="font-medium">
                                    {bookingsFilter
                                        ? `Bookings for "${existingLinks.find(l => l.id === bookingsFilter)?.settings?.title || `Untitled Link (${existingLinks.find(l => l.id === bookingsFilter)?.slug.slice(0, 8)}...)`}"`
                                        : "Upcoming & Recent Bookings"
                                    }
                                </h2>
                                {bookingsFilter && (
                                    <button
                                        onClick={() => setBookingsFilter(null)}
                                        className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                    >
                                        Clear Filter
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="divide-y">
                            {bookings
                                .filter(booking => !bookingsFilter || booking.link_id === bookingsFilter)
                                .map((booking) => (
                                    <div key={booking.id} className="px-4 sm:px-6 py-4">
                                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                                            <div className="flex-1">
                                                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                                                    <h3 className="font-medium">{booking.title}</h3>
                                                    <span className={`px-2 py-1 text-xs rounded-full w-fit ${booking.status === "confirmed"
                                                        ? "bg-green-100 text-green-800"
                                                        : "bg-yellow-100 text-yellow-800"
                                                        }`}>
                                                        {booking.status === "confirmed" ? "Confirmed" : "Pending"}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-muted-foreground mt-1">
                                                    {formatDateTime(booking.startTime)} - {formatDateTime(booking.endTime)}
                                                </p>
                                                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mt-2 text-sm">
                                                    <span>Attendee: {booking.attendeeEmail}</span>
                                                    <span>Link ID: {booking.link_id}</span>
                                                </div>

                                                {/* Public Link Display */}
                                                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-xs font-medium text-gray-700">URL:</span>
                                                                <a
                                                                    href={`/public/bookings/${booking.link_id}`}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    className="text-sm text-blue-600 hover:text-blue-800 truncate"
                                                                >
                                                                    {`${window.location.origin}/public/bookings/${booking.link_id}`}
                                                                </a>
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={(e) => {
                                                                const publicUrl = `${window.location.origin}/public/bookings/${booking.link_id}`;
                                                                navigator.clipboard.writeText(publicUrl).then(() => {
                                                                    // Show temporary success feedback
                                                                    const button = e.currentTarget;
                                                                    const originalText = button.textContent;
                                                                    button.textContent = 'Copied!';
                                                                    button.className = 'px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700';
                                                                    setTimeout(() => {
                                                                        button.textContent = originalText;
                                                                        button.className = 'px-3 py-1 text-sm border rounded hover:bg-gray-50';
                                                                    }, 2000);
                                                                }).catch(err => {
                                                                    console.error('Failed to copy: ', err);
                                                                    alert('Failed to copy link to clipboard');
                                                                });
                                                            }}
                                                            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 flex-shrink-0"
                                                        >
                                                            Copy Link
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex flex-wrap gap-2">
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => {
                                                        // TODO: Open calendar event - would navigate to calendar or open in new tab
                                                        alert(`Opening calendar event for ${booking.title}... (would open in calendar app)`);
                                                    }}
                                                >
                                                    Open Event
                                                </button>
                                                <button
                                                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                                    onClick={() => {
                                                        // TODO: Reschedule booking - would open reschedule form
                                                        alert(`Rescheduling ${booking.title}... (would open reschedule form)`);
                                                    }}
                                                >
                                                    Reschedule
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            {bookingsFilter && bookings.filter(b => b.link_id === bookingsFilter).length === 0 && (
                                <div className="px-4 sm:px-6 py-8 text-center">
                                    <p className="text-gray-500 mb-4">No bookings found for this link</p>
                                    <button
                                        onClick={() => setBookingsFilter(null)}
                                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                    >
                                        View All Bookings
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bookings stats */}
                    <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">
                                {bookingsFilter ? "Filtered Bookings" : "Total Bookings"}
                            </h3>
                            <p className="text-2xl font-semibold">
                                {bookingsFilter
                                    ? bookings.filter(b => b.link_id === bookingsFilter).length
                                    : bookings.length
                                }
                            </p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Confirmed</h3>
                            <p className="text-2xl font-semibold">
                                {bookingsFilter
                                    ? bookings.filter(b => b.link_id === bookingsFilter && b.status === "confirmed").length
                                    : bookings.filter(b => b.status === "confirmed").length
                                }
                            </p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Pending</h3>
                            <p className="text-2xl font-semibold">
                                {bookingsFilter
                                    ? bookings.filter(b => b.link_id === bookingsFilter && b.status === "pending").length
                                    : bookings.filter(b => b.status === "pending").length
                                }
                            </p>
                        </div>
                    </div>
                </>
            ) : (
                <>
                    {/* Analytics view */}
                    <div className="bg-white border rounded-lg overflow-hidden">
                        <div className="px-4 sm:px-6 py-4 border-b bg-gray-50">
                            <h2 className="font-medium">Link Performance Analytics</h2>
                            <p className="text-sm text-muted-foreground mt-1">
                                Track views, bookings, and conversion rates for each link
                            </p>
                        </div>

                        <div className="divide-y">
                            {analyticsData.map((item) => (
                                <div key={item.linkId} className="px-4 sm:px-6 py-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <h3 className="font-medium">{item.linkTitle}</h3>
                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
                                                <div>
                                                    <p className="text-sm text-muted-foreground">Views</p>
                                                    <p className="text-lg font-semibold">{item.views}</p>
                                                </div>
                                                <div>
                                                    <p className="text-sm text-muted-foreground">Bookings</p>
                                                    <p className="text-lg font-semibold">{item.bookings}</p>
                                                </div>
                                                <div>
                                                    <p className="text-sm text-muted-foreground">Conversion</p>
                                                    <p className="text-lg font-semibold text-green-600">{item.conversionRate}</p>
                                                </div>
                                                <div>
                                                    <p className="text-sm text-muted-foreground">Last Viewed</p>
                                                    <p className="text-sm">{formatDateTime(item.lastViewed)}</p>
                                                </div>
                                            </div>
                                            <div className="mt-3">
                                                <p className="text-sm text-muted-foreground">Top Referrers</p>
                                                <div className="flex flex-wrap gap-2 mt-1">
                                                    {item.topReferrers.map((referrer: string, idx: number) => (
                                                        <span key={idx} className="px-2 py-1 bg-gray-100 text-xs rounded">
                                                            {referrer}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Analytics summary */}
                    <div className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-4">
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Total Views</h3>
                            <p className="text-2xl font-semibold">{analyticsData.reduce((sum, item) => sum + item.views, 0)}</p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Total Links</h3>
                            <p className="text-2xl font-semibold">{existingLinks.length}</p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Total Bookings</h3>
                            <p className="text-2xl font-semibold">{analyticsData.reduce((sum, item) => sum + item.bookings, 0)}</p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Avg Conversion</h3>
                            <p className="text-2xl font-semibold text-green-600">
                                {analyticsData.length > 0
                                    ? ((analyticsData.reduce((sum, item) => sum + parseFloat(item.conversionRate), 0) / analyticsData.length)).toFixed(1) + '%'
                                    : '--- %'
                                }
                            </p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                            <h3 className="text-sm font-medium text-muted-foreground">Active Links</h3>
                            <p className="text-2xl font-semibold">{analyticsData.length}</p>
                        </div>
                    </div>
                </>
            )}
        </div>
    );

    // Main component render
    if (activeTab === "manage") {
        return renderManageView();
    }

    return (
        <div className="p-4 sm:p-6 max-w-4xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <h1 className="text-xl sm:text-2xl font-semibold">Create Booking Link</h1>
                <button
                    className="w-full sm:w-auto px-4 py-2 border rounded hover:bg-gray-50"
                    onClick={() => setActiveTab("manage")}
                >
                    Manage Links
                </button>
            </div>

            {/* Step indicator */}
            <div className="mb-8">
                <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto pb-2">
                    {steps.map((step, index) => (
                        <div
                            key={step.key}
                            className="flex items-center flex-shrink-0 cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => setCurrentStep(step.key)}
                        >
                            <div
                                className={`w-6 sm:w-8 h-6 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-medium ${currentStep === step.key
                                    ? "bg-blue-600 text-white"
                                    : index < steps.findIndex(s => s.key === currentStep)
                                        ? "bg-green-500 text-white"
                                        : "bg-gray-200 text-gray-600"
                                    }`}
                            >
                                {index < steps.findIndex(s => s.key === currentStep) ? "✓" : index + 1}
                            </div>
                            <span className="ml-2 text-xs sm:text-sm font-medium whitespace-nowrap">{step.label}</span>
                            {index < steps.length - 1 && (
                                <div className="w-4 sm:w-8 h-0.5 bg-gray-200 mx-2 sm:mx-4" />
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Step content */}
            <div className="bg-white border rounded-lg p-4 sm:p-6">
                {renderStep()}
            </div>

            {/* Navigation */}
            <div className="flex flex-col sm:flex-row justify-between gap-4 mt-6">
                <button
                    className="w-full sm:w-auto px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
                    disabled={!canGoBack()}
                    onClick={goBack}
                >
                    Back
                </button>
                <button
                    className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                    onClick={goNext}
                    disabled={!canGoNext() || isLoading}
                >
                    {isLoading ? (
                        <span className="flex items-center gap-2">
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Processing...
                        </span>
                    ) : (
                        currentStep === "review" ? "Create" : "Next"
                    )}
                </button>
            </div>
        </div>
    );

    // Success Dialog
    return (
        <>
            {/* Success Dialog */}
            <Dialog open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-green-500" />
                            {successData?.title}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            {successData?.message}
                        </p>

                        {successData && (
                            <div className="space-y-3">
                                <div>
                                    <Label className="text-xs font-medium text-gray-700">Booking Title</Label>
                                    <div className="flex items-center gap-2 mt-1">
                                        <code className="flex-1 text-sm bg-gray-100 px-2 py-1 rounded font-mono">
                                            {successData.bookingTitle}
                                        </code>
                                    </div>
                                </div>

                                <div>
                                    <Label className="text-xs font-medium text-gray-700">Public Booking Link</Label>
                                    <div className="flex items-center gap-2 mt-1">
                                        <a
                                            href={successData.publicUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex-1 text-sm text-blue-600 hover:text-blue-800 underline truncate"
                                        >
                                            {successData.publicUrl}
                                        </a>
                                        <button
                                            onClick={() => {
                                                if (!successData) return;
                                                navigator.clipboard.writeText(successData.publicUrl).then(() => {
                                                    // Show temporary success feedback
                                                    const button = event?.target as HTMLButtonElement;
                                                    if (button) {
                                                        const originalText = button.textContent;
                                                        button.textContent = 'Copied!';
                                                        button.className = 'px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700';
                                                        setTimeout(() => {
                                                            button.textContent = originalText;
                                                            button.className = 'px-2 py-1 text-xs border rounded hover:bg-gray-50';
                                                        }, 2000);
                                                    }
                                                }).catch(err => {
                                                    console.error('Failed to copy: ', err);
                                                    alert('Failed to copy link to clipboard');
                                                });
                                            }}
                                            className="px-2 py-1 text-xs border rounded hover:bg-gray-50 flex-shrink-0 flex items-center"
                                            title="Copy link"
                                        >
                                            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                                                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="flex justify-end pt-2">
                            <Button
                                onClick={() => setShowSuccessDialog(false)}
                                className="px-4 py-2"
                            >
                                OK
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Main component content */}
            {activeTab === "manage" ? (
                renderManageView()
            ) : (
                <div className="p-4 sm:p-6 max-w-4xl mx-auto">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                        <h1 className="text-xl sm:text-2xl font-semibold">Create Booking Link</h1>
                        <button
                            className="w-full sm:w-auto px-4 py-2 border rounded hover:bg-gray-50"
                            onClick={() => setActiveTab("manage")}
                        >
                            Manage Links
                        </button>
                    </div>

                    {/* Step indicator */}
                    <div className="mb-8">
                        <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto pb-2">
                            {steps.map((step, index) => (
                                <div
                                    key={step.key}
                                    className="flex items-center flex-shrink-0 cursor-pointer hover:opacity-80 transition-opacity"
                                    onClick={() => setCurrentStep(step.key)}
                                >
                                    <div
                                        className={`w-6 sm:w-8 h-6 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-medium ${currentStep === step.key
                                            ? "bg-blue-600 text-white"
                                            : index < steps.findIndex(s => s.key === currentStep)
                                                ? "bg-blue-600 text-white"
                                                : "bg-gray-200 text-gray-600"
                                            }`}
                                    >
                                        {index < steps.findIndex(s => s.key === currentStep) ? "✓" : index + 1}
                                    </div>
                                    <span className="ml-2 text-xs sm:text-sm font-medium whitespace-nowrap">{step.label}</span>
                                    {index < steps.length - 1 && (
                                        <div className="w-4 sm:w-8 h-0.5 bg-gray-200 mx-2 sm:mx-4" />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Step content */}
                    <div className="bg-white border rounded-lg p-4 sm:p-6">
                        {renderStep()}
                    </div>

                    {/* Navigation */}
                    <div className="flex flex-col sm:flex-row justify-between gap-4 mt-6">
                        <button
                            className="w-full sm:w-auto px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
                            disabled={!canGoBack()}
                            onClick={goBack}
                        >
                            Back
                        </button>
                        <button
                            className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                            onClick={goNext}
                            disabled={!canGoNext() || isLoading}
                        >
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Processing...
                                </span>
                            ) : (
                                currentStep === "review" ? "Create" : "Next"
                            )}
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}


