"use client";

import { useState } from "react";

type Step = "basics" | "availability" | "duration" | "limits" | "template" | "review";

export default function BookingsPage() {
  const [currentStep, setCurrentStep] = useState<Step>("basics");
  const [showOneTimeForm, setShowOneTimeForm] = useState(false);
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
  });

  const [oneTimeData, setOneTimeData] = useState({
    recipientEmail: "",
    recipientName: "",
    expiresInDays: 7,
  });

  const steps: { key: Step; label: string }[] = [
    { key: "basics", label: "Basics" },
    { key: "availability", label: "Availability" },
    { key: "duration", label: "Duration & Buffer" },
    { key: "limits", label: "Limits" },
    { key: "template", label: "Template" },
    { key: "review", label: "Review" },
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
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Availability Settings</h2>
            <p className="text-sm text-muted-foreground">
              Configure when your booking link is active and available.
            </p>
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
          </div>
        );

      case "duration":
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Duration & Buffer</h2>
            <div>
              <label className="block text-sm font-medium mb-1">Meeting Duration (minutes)</label>
              <select
                className="border rounded px-3 py-2 w-full"
                value={formData.duration}
                onChange={(e) => setFormData({ ...formData, duration: Number(e.target.value) })}
              >
                <option value={15}>15 minutes</option>
                <option value={30}>30 minutes</option>
                <option value={60}>1 hour</option>
                <option value={120}>2 hours</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Buffer Before (minutes)</label>
                <input
                  type="number"
                  className="border rounded px-3 py-2 w-full"
                  value={formData.bufferBefore}
                  onChange={(e) => setFormData({ ...formData, bufferBefore: Number(e.target.value) })}
                  min="0"
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
                />
              </div>
            </div>
          </div>
        );

      case "limits":
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Booking Limits</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Max per Day</label>
                <input
                  type="number"
                  className="border rounded px-3 py-2 w-full"
                  value={formData.maxPerDay}
                  onChange={(e) => setFormData({ ...formData, maxPerDay: Number(e.target.value) })}
                  min="1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max per Week</label>
                <input
                  type="number"
                  className="border rounded px-3 py-2 w-full"
                  value={formData.maxPerWeek}
                  onChange={(e) => setFormData({ ...formData, maxPerWeek: Number(e.target.value) })}
                  min="1"
                />
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
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Review & Create</h2>
            <div className="bg-gray-50 p-4 rounded">
              <h3 className="font-medium">{formData.title}</h3>
              {formData.description && <p className="text-sm text-muted-foreground mt-1">{formData.description}</p>}
              <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
                <div>Duration: {formData.duration} minutes</div>
                <div>Buffer: {formData.bufferBefore}m before, {formData.bufferAfter}m after</div>
                <div>Max per day: {formData.maxPerDay}</div>
                <div>Max per week: {formData.maxPerWeek}</div>
                <div>Advance booking: {formData.advanceDays} days</div>
                <div>Max advance: {formData.maxAdvanceDays} days</div>
              </div>
            </div>
            <button
              className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
              onClick={() => {
                // TODO: Implement API call to create booking link
                alert("Creating booking link... (API integration pending)");
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

  const createOneTimeLink = () => {
    // TODO: Implement API call to create one-time link
    const mockToken = "ot_" + Math.random().toString(36).substr(2, 9);
    const mockUrl = `${window.location.origin}/public/bookings/${mockToken}`;
    alert(`One-time link created!\n\nURL: ${mockUrl}\n\nThis link will expire in ${oneTimeData.expiresInDays} days or after first use.`);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold mb-6">Create Booking Link</h1>
      
      {/* Step indicator */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                currentStep === step.key
                  ? "bg-blue-600 text-white"
                  : index < steps.findIndex(s => s.key === currentStep)
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-600"
              }`}
            >
              {index < steps.findIndex(s => s.key === currentStep) ? "✓" : index + 1}
            </div>
            <span className="ml-2 text-sm font-medium">{step.label}</span>
            {index < steps.length - 1 && (
              <div className="w-16 h-0.5 bg-gray-200 mx-4" />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white border rounded-lg p-6">
        {renderStep()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <button
          className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
          disabled={!canGoBack()}
          onClick={goBack}
        >
          Back
        </button>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          disabled={!canGoNext()}
          onClick={goNext}
        >
          {currentStep === "review" ? "Create" : "Next"}
        </button>
      </div>

      {/* One-time link creation */}
      <div className="mt-12 border-t pt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">One-Time Link</h2>
          <button
            className="text-blue-600 hover:text-blue-700 text-sm"
            onClick={() => setShowOneTimeForm(!showOneTimeForm)}
          >
            {showOneTimeForm ? "Hide" : "Create One-Time Link"}
          </button>
        </div>
        
        {showOneTimeForm && (
          <div className="bg-white border rounded-lg p-6">
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


