'use client';

import React, { useState, useEffect } from 'react';

const TimezoneSelector = () => {
  const [currentTimezone, setCurrentTimezone] = useState('');

  useEffect(() => {
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
  ];

  const handleTimezoneChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newTimezone = e.target.value;
    setCurrentTimezone(newTimezone);
    // In a real app, you might want to persist this to user settings
    // or notify other components of the change.
    console.log('Timezone selected in Nav:', newTimezone);
    // Potentially update a global state or context here.
  };

  return (
    <select
      value={currentTimezone}
      onChange={handleTimezoneChange}
      className="bg-gray-700 text-white p-1.5 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 hover:bg-gray-600"
      title="Select Timezone"
    >
      {timezones.map(tz => (
        <option key={tz} value={tz} className="bg-gray-800 text-white">
          {tz.replace(/_/g, ' ' )}
        </option>
      ))}
      {!timezones.includes(currentTimezone) && currentTimezone && (
         <option key={currentTimezone} value={currentTimezone} className="bg-gray-800 text-white">
          {currentTimezone.replace(/_/g, ' ' )} (Current)
        </option>
      )}
    </select>
  );
};

export default TimezoneSelector; 