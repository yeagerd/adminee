'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { useStreamingSetting } from '@/hooks/use-streaming-setting';
import { Settings, User } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';

export function ProfileContent() {
    const { data: session, status } = useSession();
    const { enableStreaming, updateStreamingSetting, isLoaded } = useStreamingSetting();

    if (status === 'loading') {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="flex items-center justify-center h-full">
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



    return (
        <div className="p-6 space-y-6">
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
                                        Connected via {session.provider}
                                    </Badge>
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Settings className="h-5 w-5" />
                        Settings
                    </CardTitle>
                    <CardDescription>
                        Configure your application preferences and development options
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-4">
                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="streaming"
                                checked={enableStreaming}
                                onCheckedChange={(checked) => updateStreamingSetting(checked as boolean)}
                                disabled={!isLoaded}
                            />
                            <label htmlFor="streaming" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                Enable streaming (dev only)
                            </label>
                        </div>
                        <p className="text-xs text-gray-500">
                            Enable real-time streaming responses in the chat interface. This is a development feature for testing streaming functionality.
                        </p>
                    </div>
                </CardContent>
            </Card>


        </div>
    );
} 