'use client';

import React, { useState, useEffect } from 'react';
import { mockCalendarEvents, getEventsForDay } from '@/lib/mockData'; // Adjusted path
import { CalendarEvent } from '@/lib/types'; // Adjusted path
import { format, startOfDay, addDays, subDays } from 'date-fns';

// Basic card component for displaying an event
const EventCard: React.FC<{ event: CalendarEvent }> = ({ event }) => (
  <div className={`p-2 mb-2 rounded shadow-sm border-l-4 ${event.color ? `border-${event.color}-500` : 'border-blue-500'} bg-white`}>
    <h3 className="font-semibold">{event.title}</h3>
    <p className="text-sm text-gray-600">
      {format(new Date(event.startTime), 'p')} - {format(new Date(event.endTime), 'p')}
    </p>
    {event.location && <p className="text-xs text-gray-500">{event.location}</p>}
    {event.description && <p className="text-xs mt-1">{event.description}</p>}
  </div>
);

const CalendarView: React.FC = () => {
  const [currentDate, setCurrentDate] = useState<Date>(startOfDay(new Date()));
  const [eventsForDay, setEventsForDay] = useState<CalendarEvent[]>([]);

  useEffect(() => {
    // In a real app, you'd fetch events for currentDate
    // For now, we use the mock data utility
    setEventsForDay(getEventsForDay(currentDate));
  }, [currentDate]);

  const goToPreviousDay = () => {
    setCurrentDate((prev: Date) => subDays(prev, 1));
  };

  const goToNextDay = () => {
    setCurrentDate((prev: Date) => addDays(prev, 1));
  };
  
  const goToToday = () => {
    setCurrentDate(startOfDay(new Date()));
  };

  return (
    <div className="bg-gray-50 p-4 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <button onClick={goToPreviousDay} className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&lt; Prev</button>
        <h2 className="text-lg font-semibold">
          {format(currentDate, 'eeee, MMMM do, yyyy')}
        </h2>
        <button onClick={goToNextDay} className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">Next &gt;</button>
      </div>
      <button onClick={goToToday} className="mb-4 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">Go to Today</button>
      
      {eventsForDay.length > 0 ? (
        eventsForDay.map(event => <EventCard key={event.id} event={event} />)
      ) : (
        <p>No events scheduled for this day.</p>
      )}
    </div>
  );
};

export default CalendarView; 