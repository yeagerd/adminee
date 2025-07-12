'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { gatewayClient, Integration } from '@/lib/gateway-client';
import { Calendar, ExternalLink, Mail, Shield, User } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function ProfilePage() {
    const { data: session, status } = useSession();
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [loading, setLoading] = useState(true);

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
        } finally {
            setLoading(false);
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
                        <CardDescription>Please sign in to view your profile</CardDescription>
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

    const userInitials = session.user?.name
        ? session.user.name
            .split(' ')
            .map((n: string) => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
        : session.user?.email?.[0]?.toUpperCase() || 'U';

    const getProviderIcon = (provider: string) => {
        switch (provider.toLowerCase()) {
            case 'google':
                return '🔍';
            case 'microsoft':
            case 'azure-ad':
                return '🪟';
            default:
                return '🔗';
        }
    };

    const getIntegrationIcon = (provider: string) => {
        switch (provider.toLowerCase()) {
            case 'google':
                return <Calendar className="h-4 w-4" />;
            case 'microsoft':
                return <Mail className="h-4 w-4" />;
            default:
                return <Shield className="h-4 w-4" />;
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                <div className="space-y-6">
                    {/* Header */}
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
                        <p className="text-gray-600 mt-2">Manage your account settings and integrations</p>
                    </div>

                    {/* User Information */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <User className="h-5 w-5" />
                                Account Information
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center space-x-4">
                                <Avatar className="h-16 w-16">
                                    <AvatarImage src={session.user?.image || ''} />
                                    <AvatarFallback className="text-lg">{userInitials}</AvatarFallback>
                                </Avatar>
                                <div className="space-y-1">
                                    <h3 className="text-xl font-semibold">
                                        {session.user?.name || 'User'}
                                    </h3>
                                    <p className="text-gray-600">{session.user?.email}</p>
                                    {session.provider && (
                                        <div className="flex items-center gap-2">
                                            <Badge variant="secondary" className="text-xs">
                                                {getProviderIcon(session.provider)} Connected via {session.provider}
                                            </Badge>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Integration Status */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <Shield className="h-5 w-5" />
                                        Connected Integrations
                                    </CardTitle>
                                    <CardDescription>
                                        Manage your calendar and email integrations
                                    </CardDescription>
                                </div>
                                <Button asChild variant="outline">
                                    <Link href="/integrations">
                                        <ExternalLink className="h-4 w-4 mr-2" />
                                        Manage Integrations
                                    </Link>
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <div className="text-center py-4">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600 mx-auto"></div>
                                    <p className="text-sm text-gray-600 mt-2">Loading integrations...</p>
                                </div>
                            ) : integrations.length > 0 ? (
                                <div className="space-y-3">
                                    {integrations.map((integration) => (
                                        <div
                                            key={integration.id}
                                            className="flex items-center justify-between p-3 border rounded-lg"
                                        >
                                            <div className="flex items-center gap-3">
                                                {getIntegrationIcon(integration.provider)}
                                                <div>
                                                    <p className="font-medium capitalize">{integration.provider}</p>
                                                    <p className="text-sm text-gray-600">
                                                        {integration.scopes.length} permission{integration.scopes.length !== 1 ? 's' : ''}
                                                    </p>
                                                </div>
                                            </div>
                                            <Badge
                                                variant={integration.status === 'ACTIVE' ? 'default' : 'secondary'}
                                            >
                                                {integration.status}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <Shield className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                                        No integrations connected
                                    </h3>
                                    <p className="text-gray-600 mb-4">
                                        Connect your calendar and email to get started with Briefly
                                    </p>
                                    <Button asChild>
                                        <Link href="/integrations">Connect Integrations</Link>
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Account Actions */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Account Actions</CardTitle>
                            <CardDescription>
                                Manage your account settings and preferences
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Button variant="outline" asChild>
                                    <Link href="/dashboard">
                                        <Calendar className="h-4 w-4 mr-2" />
                                        Go to Dashboard
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link href="/integrations">
                                        <Shield className="h-4 w-4 mr-2" />
                                        Manage Integrations
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