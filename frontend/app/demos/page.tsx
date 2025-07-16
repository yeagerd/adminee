'use client';

import { DemoChatInterface } from '@/components/demo-chat-interface';
import { DemoScheduleList } from '@/components/demo-schedule-list';
import { DemoTaskList } from '@/components/demo-task-list';
import Navbar from '@/components/navbar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { demoIntegrations, demoUser, type DemoIntegration } from '@/lib/demo-data';
import {
    Calendar,
    CheckCircle,
    Clock,
    Mail,
    MessageSquare,
    Play,
    Plus,
    RefreshCw,
    Settings,
    Shield,
    User
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function DemosPage() {
    const [isRefreshing, setIsRefreshing] = useState(false);

    const handleRefresh = () => {
        setIsRefreshing(true);
        // Simulate refresh delay
        setTimeout(() => setIsRefreshing(false), 1000);
    };

    const today = new Date();
    const formattedDate = today.toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
        timeZoneName: "short",
    });

    const activeIntegrations = demoIntegrations.filter((i: DemoIntegration) => i.status === 'active');
    const hasGoogleIntegration = activeIntegrations.some((i: DemoIntegration) => i.provider === 'google');
    const hasMicrosoftIntegration = activeIntegrations.some((i: DemoIntegration) => i.provider === 'microsoft');

    return (
        <div className="min-h-screen bg-gray-50">
            <Navbar />
            <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
                {/* Demo Mode Banner */}
                <div className="mb-6">
                    <Card className="border-blue-200 bg-blue-50">
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Play className="h-5 w-5 text-blue-600" />
                                    <div>
                                        <h2 className="text-lg font-semibold text-blue-900">Demo Mode</h2>
                                        <p className="text-sm text-blue-700">Showing sample data for demonstration purposes</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                                        Demo Data
                                    </Badge>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleRefresh}
                                        disabled={isRefreshing}
                                    >
                                        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                                        Refresh
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Welcome Header */}
                <div className="mb-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">
                                Welcome back, {demoUser.name?.split(' ')[0] || 'Demo User'}!
                            </h1>
                            <p className="text-gray-600 mt-1">{formattedDate}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" asChild>
                                <Link href="/dashboard">
                                    <Settings className="h-4 w-4 mr-2" />
                                    Real Dashboard
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Demo Integration Status */}
                <Card className="mb-6 border-green-200 bg-green-50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Shield className="h-5 w-5 text-green-600" />
                            Demo Integrations Active
                        </CardTitle>
                        <CardDescription>
                            Sample integrations are connected to demonstrate the full Briefly experience
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-3">
                            {hasGoogleIntegration && (
                                <Badge variant="outline" className="bg-white">
                                    <Calendar className="h-3 w-3 mr-1" />
                                    Google Calendar
                                </Badge>
                            )}
                            {hasMicrosoftIntegration && (
                                <Badge variant="outline" className="bg-white">
                                    <Mail className="h-3 w-3 mr-1" />
                                    Microsoft 365
                                </Badge>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Main Dashboard Content */}
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
                            <DemoScheduleList />
                        </CardContent>
                    </Card>

                    {/* Tasks Section */}
                    <Card className="flex-1 min-w-0 w-full">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg font-medium flex items-center gap-2">
                                <CheckCircle className="h-5 w-5 text-teal-600" />
                                Today's Tasks
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <DemoTaskList />
                        </CardContent>
                    </Card>
                </div>

                {/* Chat Interface */}
                <div className="mt-6">
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg font-medium flex items-center gap-2">
                                <MessageSquare className="h-5 w-5 text-teal-600" />
                                AI Assistant (Demo)
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <DemoChatInterface />
                        </CardContent>
                    </Card>
                </div>

                {/* Quick Actions */}
                <div className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Quick Actions</CardTitle>
                            <CardDescription>Common tasks and settings</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <Button variant="outline" asChild>
                                    <Link href="/settings?page=integrations">
                                        <Shield className="h-4 w-4 mr-2" />
                                        Manage Integrations
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/settings?page=profile">
                                        <User className="h-4 w-4 mr-2" />
                                        View Profile
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/dashboard">
                                        <Calendar className="h-4 w-4 mr-2" />
                                        Real Dashboard
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/onboarding">
                                        <Play className="h-4 w-4 mr-2" />
                                        Start Onboarding
                                    </Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
} 