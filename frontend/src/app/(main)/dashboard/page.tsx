import CalendarView from '@/components/dashboard/CalendarView'; // Adjusted path

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Today's Dashboard</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          {/* Replace placeholder with CalendarView component */}
          <CalendarView />
        </div>
        <div className="bg-white p-4 rounded shadow">
          <h2 className="text-xl mb-2">Tasks</h2>
          <p>Task list will be here (Task 4.5.2)</p>
          {/* Placeholder for TaskManager */}
        </div>
        <div className="lg:col-span-3 bg-white p-4 rounded shadow mt-4">
          <h2 className="text-xl mb-2">Chat</h2>
          <p>Chat interface will be here (Task 4.5.3)</p>
          {/* Placeholder for ChatBar */}
        </div>
      </div>
    </div>
  );
} 