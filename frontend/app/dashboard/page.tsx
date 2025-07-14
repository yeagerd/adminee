'use client';

import ChatInterface from '@/components/chat-interface';
import Navbar from '@/components/navbar';
import ScheduleList from '@/components/schedule-list';
import TaskList from '@/components/task-list';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { gatewayClient, Integration } from '@/lib/gateway-client';
import {
    AlertCircle,
    Calendar,
    CheckCircle,
    Clock,
    Mail,
    MessageSquare,
    Plus,
    Shield,
    User
} from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function DashboardPage() {
    const { data: session, status } = useSession();
    const [integrations, setIntegrations] = useState<Integration[]>([]);

    useEffect(() => {
        if (session) {
            loadIntegrations();
        }
    }, [session]);

    const loadIntegrations = async () => {
        try {
            const data = await gatewayClient.getIntegrations();
            // The backend returns { integrations: [...], total: ..., active_count: ..., error_count: ... }
            // Extract just the integrations array
            setIntegrations(data.integrations || []);
        } catch (error) {
            console.error('Failed to load integrations:', error);
        }
    };

    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle>Authentication Required</CardTitle>
                        <CardDescription>Please sign in to access your dashboard</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button asChild className="w-full">
                            <Link href="/login">Sign In</Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const today = new Date();
    const formattedDate = today.toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
    });

    const activeIntegrations = integrations.filter(i => i.status === 'active');
    const hasGoogleIntegration = activeIntegrations.some(i => i.provider === 'google');
    const hasMicrosoftIntegration = activeIntegrations.some(i => i.provider === 'microsoft');

    // Check for integrations with token issues
    // Only show warnings for missing access tokens or expired tokens
    // Missing refresh tokens are acceptable for some providers (like Microsoft)
    const integrationsWithTokenIssues = integrations.filter(i => {
        if (i.status !== 'active') return false;

        // Missing access token is always an issue
        if (!i.has_access_token) return true;

        // Check if access token is expired
        if (i.token_expires_at) {
            const expiresAt = new Date(i.token_expires_at);
            const now = new Date();
            if (expiresAt <= now) return true;
        }

        // Missing refresh token is only an issue if the access token is expired or will expire soon
        if (!i.has_refresh_token && i.token_expires_at) {
            const expiresAt = new Date(i.token_expires_at);
            const now = new Date();
            const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour
            if (expiresAt <= oneHourFromNow) return true;
        }

        return false;
    });
    const hasTokenIssues = integrationsWithTokenIssues.length > 0;

    return (
        <div className="min-h-screen bg-gray-50">
            <Navbar />
            <div className="container mx-auto px-4 py-6 w-full max-w-7xl">
                {/* Welcome Header */}
                <div className="mb-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">
                                Welcome back, {session.user?.name?.split(' ')[0] || 'User'}!
                            </h1>
                            <p className="text-gray-600 mt-1">{formattedDate}</p>
                        </div>
                    </div>
                </div>



                {/* Integration Setup */}
                {activeIntegrations.length === 0 && (
                    <Card className="mb-6 border-blue-200 bg-blue-50">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5 text-blue-600" />
                                Get Started with Integrations
                            </CardTitle>
                            <CardDescription>
                                Connect your calendar and email to unlock the full power of Briefly
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex gap-3">
                                <Button asChild>
                                    <Link href="/integrations">
                                        <Plus className="h-4 w-4 mr-2" />
                                        Connect Services
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/onboarding">
                                        Start Onboarding
                                    </Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Integration Token Issues Warning */}
                {hasTokenIssues && (
                    <Card className="mb-6 border-orange-200 bg-orange-50">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <AlertCircle className="h-5 w-5 text-orange-600" />
                                Integration Issues Detected
                            </CardTitle>
                            <CardDescription>
                                Some of your integrations have token issues and may not work properly
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {integrationsWithTokenIssues.map((integration) => (
                                    <div key={integration.id} className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium capitalize">{integration.provider}</span>
                                            <span className="text-sm text-orange-600">
                                                {!integration.has_access_token && "Missing access token"}
                                                {integration.has_access_token && !integration.has_refresh_token && integration.token_expires_at && (() => {
                                                    const expiresAt = new Date(integration.token_expires_at);
                                                    const now = new Date();
                                                    const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000);
                                                    if (expiresAt <= now) {
                                                        return "Access token expired";
                                                    } else if (expiresAt <= oneHourFromNow) {
                                                        return "Access token expires soon";
                                                    }
                                                    return "Missing refresh token";
                                                })()}
                                            </span>
                                        </div>
                                        <Button variant="outline" size="sm" asChild>
                                            <Link href="/integrations">Fix Integration</Link>
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

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
                            <ScheduleList
                                dateRange="today"
                                providers={[
                                    ...(hasGoogleIntegration ? ['google'] : []),
                                    ...(hasMicrosoftIntegration ? ['microsoft'] : [])
                                ]}
                                limit={10}
                                fallbackToDemo={true}
                                showDemoIndicator={true}
                            />
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
                                    <Link href="/integrations">
                                        <Shield className="h-4 w-4 mr-2" />
                                        Manage Integrations
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/profile">
                                        <User className="h-4 w-4 mr-2" />
                                        View Profile
                                    </Link>
                                </Button>
                                <Button variant="outline" disabled>
                                    <Calendar className="h-4 w-4 mr-2" />
                                    Meeting Prep
                                </Button>
                                <Button variant="outline" disabled>
                                    <Mail className="h-4 w-4 mr-2" />
                                    Email Drafts
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
} 