"use client"

import ChatInterface from "@/components/chat-interface";
import Navbar from "@/components/navbar";
import ScheduleList from "@/components/schedule-list";
import TaskList from "@/components/task-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    CheckCircle2,
    Clock,
    LogIn,
    MessageSquare,
    Plus,
} from "lucide-react";
import { useSession } from "next-auth/react";
import Link from "next/link";

export default function Home() {
    const { data: session, status } = useSession();

    // Get current date
    const today = new Date();
    const formattedDate = today.toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
        timeZoneName: "short",
    });

    // Show loading state while checking authentication
    if (status === "loading") {
        return (
            <main className="min-h-screen bg-gray-50">
                <Navbar />
                <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
                    </div>
                </div>
            </main>
        );
    }

    // Show welcome screen for unauthenticated users
    if (!session) {
        return (
            <main className="min-h-screen bg-gray-50">
                <Navbar />
                <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
                    {/* Date Display */}
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-gray-800">{formattedDate}</h2>
                    </div>

                    {/* Welcome Card */}
                    <Card className="max-w-2xl mx-auto">
                        <CardHeader className="text-center">
                            <CardTitle className="text-2xl font-bold text-gray-800">
                                Welcome to Briefly
                            </CardTitle>
                            <p className="text-gray-600 mt-2">
                                Your AI-powered calendar and productivity assistant
                            </p>
                        </CardHeader>
                        <CardContent className="text-center space-y-4">
                            <p className="text-gray-600">
                                Sign in to access your calendar, manage tasks, and chat with your AI assistant.
                            </p>
                            <Button asChild className="w-full max-w-xs">
                                <Link href="/login">
                                    <LogIn className="h-4 w-4 mr-2" />
                                    Sign In
                                </Link>
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </main>
        );
    }

    // Show full dashboard for authenticated users
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
