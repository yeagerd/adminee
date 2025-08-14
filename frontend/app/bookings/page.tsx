"use client";

import { useState } from "react";
import { bookingAPI } from "../../lib/booking-api";

type Step = "basics" | "availability" | "duration" | "limits" | "template" | "review";

type WeekdayKey = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

type BusinessHours = {
  [K in WeekdayKey]: { start: string; end: string; enabled: boolean };
};

export default function BookingsPage() {
  const [currentStep, setCurrentStep] = useState<Step>("basics");
  const [showOneTimeForm, setShowOneTimeForm] = useState(false);
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
  });

  const [oneTimeData, setOneTimeData] = useState({
    recipientEmail: "",
    recipientName: "",
    expiresInDays: 7,
  });

  // Mock data for existing links
  const [existingLinks] = useState([
    {
      id: "1",
      title: "Coffee Chat",
      slug: "coffee-chat",
      isActive: true,
      createdAt: "2024-01-15",
      totalBookings: 12,
      conversionRate: "8.5%",
    },
    {
      id: "2", 
      title: "Consultation",
      slug: "consultation",
      isActive: false,
      createdAt: "2024-01-10",
      totalBookings: 5,
      conversionRate: "12.3%",
    },
  ]);

  // Mock data for bookings
  const [bookings] = useState([
    {
      id: "1",
      title: "Coffee Chat with John Doe",
      startTime: "2024-01-20T10:00:00Z",
      endTime: "2024-01-20T10:30:00Z",
      attendeeEmail: "john@example.com",
      attendeeName: "John Doe",
      linkTitle: "Coffee Chat",
      status: "confirmed",
    },
    {
      id: "2",
      title: "Consultation with Jane Smith",
      startTime: "2024-01-21T14:00:00Z",
      endTime: "2024-01-21T15:00:00Z",
      attendeeEmail: "jane@example.com",
      attendeeName: "Jane Smith",
      linkTitle: "Consultation",
      status: "confirmed",
    },
    {
      id: "3",
      title: "Coffee Chat with Bob Wilson",
      startTime: "2024-01-22T09:00:00Z",
      endTime: "2024-01-22T09:30:00Z",
      attendeeEmail: "bob@example.com",
      attendeeName: "Bob Wilson",
      linkTitle: "Coffee Chat",
      status: "pending",
    },
  ]);

  // Mock analytics data
  const [analyticsData] = useState([
    {
      linkId: "1",
      linkTitle: "Coffee Chat",
      views: 142,
      bookings: 12,
      conversionRate: "8.5%",
      lastViewed: "2024-01-19T15:30:00Z",
      topReferrers: ["Direct", "Email", "LinkedIn"],
    },
    {
      linkId: "2",
      linkTitle: "Consultation",
      views: 41,
      bookings: 5,
      conversionRate: "12.3%",
      lastViewed: "2024-01-18T11:20:00Z",
      topReferrers: ["Direct", "Twitter"],
    },
  ]);

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
                  const result = await bookingAPI.createBookingLink({
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
                  });
                  
                  // Show success message and reset form
                  alert(`Booking link created successfully!\n\nPublic URL: ${result.data.public_url}`);
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
    if (currentStep === "basics") return formData.title.trim().length > 0;
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

  const createOneTimeLink = async () => {
    try {
      // For now, we'll use the first existing link as the parent
      // In a real app, this would be selected by the user
      if (existingLinks.length === 0) {
        alert("Please create a booking link first before creating one-time links.");
        return;
      }
      
      const parentLinkId = existingLinks[0].id;
      const result = await bookingAPI.createOneTimeLink(parentLinkId, {
        recipient_email: oneTimeData.recipientEmail,
        recipient_name: oneTimeData.recipientName,
        expires_in_days: oneTimeData.expiresInDays,
      });
      
      alert(`One-time link created!\n\nURL: ${result.data.public_url}\n\nThis link will expire in ${oneTimeData.expiresInDays} days or after first use.`);
      
      // Reset form
      setOneTimeData({
        recipientEmail: "",
        recipientName: "",
        expiresInDays: 7,
      });
    } catch (error) {
      alert(`Error creating one-time link: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const toggleLinkStatus = async (linkId: string) => {
    try {
      const result = await bookingAPI.toggleBookingLink(linkId);
      alert(`Link ${linkId} ${result.data.is_active ? 'activated' : 'deactivated'} successfully!`);
      // In a real app, you would refresh the links list here
    } catch (error) {
      alert(`Error toggling link status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const duplicateLink = async (linkId: string) => {
    try {
      const result = await bookingAPI.duplicateBookingLink(linkId);
      alert(`Link duplicated successfully!\n\nNew slug: ${result.data.slug}`);
      // In a real app, you would refresh the links list here
    } catch (error) {
      alert(`Error duplicating link: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const editLink = (linkId: string) => {
    // TODO: Navigate to edit mode - this would require implementing an edit form
    alert(`Editing link ${linkId}... (edit mode pending - would navigate to edit form)`);
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

  if (activeTab === "manage") {
    return (
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
            className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${
              manageView === "links"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setManageView("links")}
          >
            Links
          </button>
          <button
            className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${
              manageView === "bookings"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setManageView("bookings")}
          >
            Bookings
          </button>
          <button
            className={`px-3 sm:px-4 py-2 border-b-2 font-medium whitespace-nowrap ${
              manageView === "analytics"
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
              
              <div className="divide-y">
                {existingLinks.map((link) => (
                  <div key={link.id} className="px-4 sm:px-6 py-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                          <h3 className="font-medium">{link.title}</h3>
                          <span className={`px-2 py-1 text-xs rounded-full w-fit ${
                            link.isActive 
                              ? "bg-green-100 text-green-800" 
                              : "bg-gray-100 text-gray-800"
                          }`}>
                            {link.isActive ? "Active" : "Inactive"}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Slug: {link.slug} • Created: {link.createdAt}
                        </p>
                        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mt-2 text-sm">
                          <span>Total bookings: {link.totalBookings}</span>
                          <span>Conversion: {link.conversionRate}</span>
                        </div>
                      </div>
                      
                      <div className="flex flex-wrap gap-2">
                        <button
                          className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                          onClick={() => toggleLinkStatus(link.id)}
                        >
                          {link.isActive ? "Disable" : "Enable"}
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
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick stats */}
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Total Links</h3>
                <p className="text-2xl font-semibold">{existingLinks.length}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Active Links</h3>
                <p className="text-2xl font-semibold">{existingLinks.filter(l => l.isActive).length}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Total Bookings</h3>
                <p className="text-2xl font-semibold">{existingLinks.reduce((sum, l) => sum + l.totalBookings, 0)}</p>
              </div>
            </div>
          </>
        ) : manageView === "bookings" ? (
          <>
            {/* Bookings list */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="px-4 sm:px-6 py-4 border-b bg-gray-50">
                <h2 className="font-medium">Upcoming & Recent Bookings</h2>
              </div>
              
              <div className="divide-y">
                {bookings.map((booking) => (
                  <div key={booking.id} className="px-4 sm:px-6 py-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                          <h3 className="font-medium">{booking.title}</h3>
                          <span className={`px-2 py-1 text-xs rounded-full w-fit ${
                            booking.status === "confirmed"
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
                          <span>Attendee: {booking.attendeeName} ({booking.attendeeEmail})</span>
                          <span>Link: {booking.linkTitle}</span>
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
              </div>
            </div>

            {/* Bookings stats */}
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Total Bookings</h3>
                <p className="text-2xl font-semibold">{bookings.length}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Confirmed</h3>
                <p className="text-2xl font-semibold">{bookings.filter(b => b.status === "confirmed").length}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Pending</h3>
                <p className="text-2xl font-semibold">{bookings.filter(b => b.status === "pending").length}</p>
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
                            {item.topReferrers.map((referrer, idx) => (
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
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Total Views</h3>
                <p className="text-2xl font-semibold">{analyticsData.reduce((sum, item) => sum + item.views, 0)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Total Bookings</h3>
                <p className="text-2xl font-semibold">{analyticsData.reduce((sum, item) => sum + item.bookings, 0)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-sm font-medium text-muted-foreground">Avg Conversion</h3>
                <p className="text-2xl font-semibold text-green-600">
                  {((analyticsData.reduce((sum, item) => sum + parseFloat(item.conversionRate), 0) / analyticsData.length)).toFixed(1)}%
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
            <div key={step.key} className="flex items-center flex-shrink-0">
              <div
                className={`w-6 sm:w-8 h-6 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-medium ${
                  currentStep === step.key
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

      {/* One-time link creation */}
      <div className="mt-12 border-t pt-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <h2 className="text-lg sm:text-xl font-semibold">One-Time Link</h2>
          <button
            className="w-full sm:w-auto text-blue-600 hover:text-blue-700 text-sm"
            onClick={() => setShowOneTimeForm(!showOneTimeForm)}
          >
            {showOneTimeForm ? "Hide" : "Create One-Time Link"}
          </button>
        </div>
        
        {showOneTimeForm && (
          <div className="bg-white border rounded-lg p-4 sm:p-6">
            <p className="text-sm text-muted-foreground mb-4">
              Create a single-use link for a specific recipient. This link will expire after use or after a set time.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Recipient Email *</label>
                <input
                  type="email"
                  className="border rounded px-3 py-2 w-full"
                  value={oneTimeData.recipientEmail}
                  onChange={(e) => setOneTimeData({ ...oneTimeData, recipientEmail: e.target.value })}
                  placeholder="recipient@example.com"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Recipient Name</label>
                <input
                  className="border rounded px-3 py-2 w-full"
                  value={oneTimeData.recipientName}
                  onChange={(e) => setOneTimeData({ ...oneTimeData, recipientName: e.target.value })}
                  placeholder="Optional name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Expires In (days)</label>
                <select
                  className="border rounded px-3 py-2 w-full"
                  value={oneTimeData.expiresInDays}
                  onChange={(e) => setOneTimeData({ ...oneTimeData, expiresInDays: Number(e.target.value) })}
                >
                  <option value={1}>1 day</option>
                  <option value={3}>3 days</option>
                  <option value={7}>1 week</option>
                  <option value={14}>2 weeks</option>
                  <option value={30}>1 month</option>
                </select>
              </div>
              
              <button
                className="w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 disabled:opacity-50"
                disabled={!oneTimeData.recipientEmail}
                onClick={createOneTimeLink}
              >
                Create One-Time Link
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


