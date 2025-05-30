import CalendarView from '@/components/dashboard/CalendarView';
import TaskManager from '@/components/Tasks/TaskManager';
import ChatBar from '@/components/dashboard/ChatBar';

export default function DashboardPage() {
  return (
    <div>
      <h1>Today's Dashboard</h1>
      
      {/* Interactive Calendar View */}
      <div style={{ border: '1px dashed gray', padding: '20px', margin: '20px 0' }}>
        <CalendarView />
      </div>
      
      {/* Task List Component */}
      <div style={{ border: '1px dashed gray', padding: '20px', margin: '20px 0' }}>
        <TaskManager />
      </div>
      
      {/* Chat Bar */}
      <div style={{ border: '1px dashed gray', padding: '20px', margin: '20px 0' }}>
        <ChatBar />
      </div>
    </div>
  );
} 