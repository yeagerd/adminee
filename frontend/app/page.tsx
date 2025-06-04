import {
  Calendar,
  Clock,
  CheckCircle2,
  MessageSquare,
  Plus,
  Sailboat,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import ChatInterface from "@/components/chat-interface";
import ScheduleList from "@/components/schedule-list";
import TaskList from "@/components/task-list";
import Navbar from "@/components/navbar";

export default function Home() {
  // Get current date
  const today = new Date();
  const formattedDate = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <Navbar />

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
        {/* Date Display */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800">{formattedDate}</h2>
        </div>

        <div className="flex flex-col gap-6 w-full lg:flex-row">
          {/* Schedule Section */}
          <Card className="flex-1 min-w-0 w-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-medium flex items-center gap-2 justify-between">
                <span className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-teal-600" />
                  Today's Schedule
                </span>
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-1" />
                  New Event
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScheduleList />
            </CardContent>
          </Card>

          {/* Tasks Section */}
          <Card className="flex-1 min-w-0 w-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-medium flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-teal-600" />
                Today's Tasks
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TaskList />
            </CardContent>
          </Card>
        </div>

        {/* Chat Interface */}
        <div className="mt-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-medium flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-teal-600" />
                AI Assistant
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChatInterface />
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
