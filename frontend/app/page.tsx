"use client"

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LogIn, Play } from "lucide-react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
    const { data: session, status } = useSession();
    const router = useRouter();

    // Redirect authenticated users to dashboard
    useEffect(() => {
        if (status === "authenticated" && session) {
            router.replace("/dashboard");
        }
    }, [session, status, router]);

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
                            <div className="flex flex-col gap-3 items-center">
                                <Button asChild className="w-full max-w-xs">
                                    <Link href="/login">
                                        <LogIn className="h-4 w-4 mr-2" />
                                        Sign In
                                    </Link>
                                </Button>
                                <Button asChild variant="outline" className="w-full max-w-xs">
                                    <Link href="/demos">
                                        <Play className="h-4 w-4 mr-2" />
                                        Try Demo
                                    </Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        );
    }

    // This should not be reached due to the redirect, but just in case
    return (
        <main className="min-h-screen bg-gray-50">
            <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
                </div>
            </div>
        </main>
    );
}
