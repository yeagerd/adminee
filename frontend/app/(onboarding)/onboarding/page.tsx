'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation'; // For redirecting

const OnboardingPage = () => {
  const router = useRouter();
  const [calendarConnected, setCalendarConnected] = useState(false);

  const handleConnectCalendar = () => {
    // Simulate API call or OAuth flow for connecting calendar
    console.log('Simulating calendar connection...');
    // For MVP, we'll just toggle a state and assume success
    setTimeout(() => {
      setCalendarConnected(true);
      console.log('Calendar connection successful (mock)');
    }, 1000);
  };

  const handleCompleteOnboarding = () => {
    if (!calendarConnected) {
      alert('Please connect your calendar first.');
      return;
    }
    // Here you would typically make an API call to mark onboarding as complete for the user.
    console.log('Completing onboarding...');
    // For MVP, redirect to dashboard
    router.push('/dashboard');
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-center">Welcome to Briefly!</h1>
      <p className="text-gray-600 mb-6 text-center">
        Let's get your account set up so we can help you prepare for your meetings.
      </p>

      <div className="mb-6 p-4 border rounded-lg bg-gray-50">
        <h2 className="text-xl font-semibold mb-3">1. Connect Your Calendar</h2>
        {calendarConnected ? (
          <div className="text-green-600 font-semibold p-3 bg-green-100 border border-green-300 rounded">
            ✓ Calendar Connected Successfully!
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-3">
              Connect your primary calendar (e.g., Google Calendar, Outlook Calendar) to allow Briefly to analyze your schedule.
            </p>
            <button
              onClick={handleConnectCalendar}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Connect Calendar (Mock)
            </button>
          </>
        )}
      </div>

      {/* You could add other onboarding steps here, e.g., notification preferences */}

      <div className="mt-8">
        <button
          onClick={handleCompleteOnboarding}
          disabled={!calendarConnected} // Only enable if calendar is connected
          className={`w-full px-4 py-2 font-semibold text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 ${calendarConnected ? 'bg-green-500 hover:bg-green-600 focus:ring-green-500' : 'bg-gray-400 cursor-not-allowed'}`}
        >
          Complete Onboarding & Go to Dashboard
        </button>
      </div>
    </div>
  );
};

export default OnboardingPage; 