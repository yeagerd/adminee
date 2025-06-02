import { Calendar, Clock, CheckCircle2, MessageSquare, Plus, Sailboat } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import ChatInterface from "@/components/chat-interface"
import ScheduleList from "@/components/schedule-list"
import TaskList from "@/components/task-list"

export default function Home() {
  // Get current date
  const today = new Date()
  const formattedDate = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  })

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sailboat className="h-6 w-6 text-teal-600" />
            <h1 className="text-xl font-semibold">Briefly</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4 mr-1" />
              New Event
            </Button>
            <Avatar>
              <AvatarImage src="/placeholder.svg?height=40&width=40" alt="User" />
              <AvatarFallback>JD</AvatarFallback>
            </Avatar>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {/* Date Display */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800">{formattedDate}</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Schedule Section */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-medium flex items-center gap-2">
                <Clock className="h-5 w-5 text-teal-600" />
                Today's Schedule
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScheduleList />
            </CardContent>
          </Card>

          {/* Tasks Section */}
          <Card>
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
  )
}
