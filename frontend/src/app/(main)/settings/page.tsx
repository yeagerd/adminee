'use client';

import React, { useState, useEffect } from 'react';

const SettingsPage = () => {
  const [currentTimezone, setCurrentTimezone] = useState('');
  const [mockDataEnabled, setMockDataEnabled] = useState(true);

  useEffect(() => {
    // Get the default timezone from the browser
    setCurrentTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
  }, []);

  const timezones = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
    // Add more common timezones as needed
  ];

  const handleTimezoneChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setCurrentTimezone(e.target.value);
    // Here you would typically save this to user preferences (e.g., via API call)
    console.log('Timezone changed to:', e.target.value);
  };

  const handleMockDataToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMockDataEnabled(e.target.checked);
    // Here you would typically save this preference
    console.log('Mock data enabled:', e.target.checked);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="mb-8 p-4 border rounded-lg shadow-sm bg-white">
        <h2 className="text-xl font-semibold mb-3">Timezone</h2>
        <p className="text-sm text-gray-600 mb-2">
          Select your preferred timezone. This will affect how dates and times are displayed.
        </p>
        <select
          value={currentTimezone}
          onChange={handleTimezoneChange}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {timezones.map(tz => (
            <option key={tz} value={tz}>{tz.replace(/_/g, ' ' )}</option>
          ))}
          {/* Option to show the user's detected timezone if not in the list */}
          {!timezones.includes(currentTimezone) && currentTimezone && (
            <option value={currentTimezone} disabled>{currentTimezone.replace(/_/g, ' ' )} (Current)</option>
          )}
        </select>
        <p className="text-xs text-gray-500 mt-2">
          Current system timezone: {Intl.DateTimeFormat().resolvedOptions().timeZone.replace(/_/g, ' ' )}
        </p>
      </div>

      <div className="mb-8 p-4 border rounded-lg shadow-sm bg-white">
        <h2 className="text-xl font-semibold mb-3">Data Preferences</h2>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={mockDataEnabled}
            onChange={handleMockDataToggle}
            className="mr-2 h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="text-gray-700">Use Mock Data (for demonstration)</span>
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Toggle this to switch between mock data and real data (once implemented).
        </p>
      </div>

      {/* Add more settings sections as needed */}
    </div>
  );
};

export default SettingsPage; 