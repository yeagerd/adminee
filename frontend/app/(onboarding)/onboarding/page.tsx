'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration } from '@/lib/gateway-client';
import { Calendar, CheckCircle, Loader2, Mail, Shield } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const OnboardingPage = () => {
    const router = useRouter();
    const { data: session, status } = useSession();
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

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

    const handleConnectIntegration = async (provider: string, scopes: string[]) => {
        try {
            setConnectingProvider(provider);
            const response = await gatewayClient.startOAuthFlow(provider, scopes) as { authorization_url: string };
            // Redirect to OAuth provider
            window.location.href = response.authorization_url;
        } catch (error) {
            console.error('Failed to start OAuth flow:', error);
            setConnectingProvider(null);
        }
    };

    const handleCompleteOnboarding = async () => {
        try {
            // Mark onboarding as completed in user service
            await gatewayClient.updateUser({ onboarding_completed: true });
            router.push('/dashboard');
        } catch (error) {
            console.error('Failed to complete onboarding:', error);
            // Still redirect to dashboard
            router.push('/dashboard');
        }
    };

    if (status === 'loading') {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
            </div>
        );
    }

    if (!session) {
        return (
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
                <p className="text-gray-600 mb-6">Please sign in to complete your onboarding</p>
                <Button onClick={() => router.push('/login')}>
                    Sign In
                </Button>
            </div>
        );
    }

    const activeIntegrations = integrations.filter(i => i.status === INTEGRATION_STATUS.ACTIVE);
    const hasGoogleIntegration = activeIntegrations.some(i => i.provider === 'google');
    const hasMicrosoftIntegration = activeIntegrations.some(i => i.provider === 'microsoft');
    const hasAnyIntegration = activeIntegrations.length > 0;

    return (
        <div className="space-y-6">
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-2">Welcome to Briefly!</h1>
                <p className="text-gray-600">
                    Let's connect your calendar and email to get started with intelligent meeting preparation.
                </p>
            </div>

            {/* Step 1: Google Integration */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-blue-600" />
                        1. Connect Google Services
                    </CardTitle>
                    <CardDescription>
                        Connect your Gmail and Google Calendar for comprehensive meeting insights
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {hasGoogleIntegration ? (
                        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span className="text-green-800 font-medium">Google services connected!</span>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <div className="text-sm text-gray-600">
                                <p><strong>Permissions needed:</strong></p>
                                <ul className="list-disc list-inside mt-1 space-y-1">
                                    <li>Gmail - Read emails for meeting context</li>
                                    <li>Google Calendar - Access your schedule</li>
                                </ul>
                            </div>
                            <Button
                                onClick={() => handleConnectIntegration('google', [
                                    'https://www.googleapis.com/auth/gmail.readonly',
                                    'https://www.googleapis.com/auth/calendar'
                                ])}
                                disabled={connectingProvider === 'google'}
                                className="w-full"
                            >
                                {connectingProvider === 'google' ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Connecting...
                                    </>
                                ) : (
                                    <>
                                        <Shield className="h-4 w-4 mr-2" />
                                        Connect Google
                                    </>
                                )}
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Step 2: Microsoft Integration */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-orange-600" />
                        2. Connect Microsoft Services (Optional)
                    </CardTitle>
                    <CardDescription>
                        Connect Outlook and Microsoft Calendar for additional coverage
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {hasMicrosoftIntegration ? (
                        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span className="text-green-800 font-medium">Microsoft services connected!</span>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <div className="text-sm text-gray-600">
                                <p><strong>Permissions needed:</strong></p>
                                <ul className="list-disc list-inside mt-1 space-y-1">
                                    <li>Outlook Mail - Read emails for context</li>
                                    <li>Microsoft Calendar - Access your schedule</li>
                                </ul>
                            </div>
                            <Button
                                onClick={() => handleConnectIntegration('microsoft', [
                                    'https://graph.microsoft.com/User.Read',
                                    'https://graph.microsoft.com/Calendars.ReadWrite',
                                    'https://graph.microsoft.com/Mail.Read'
                                ])}
                                disabled={connectingProvider === 'microsoft'}
                                variant="outline"
                                className="w-full"
                            >
                                {connectingProvider === 'microsoft' ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Connecting...
                                    </>
                                ) : (
                                    <>
                                        <Shield className="h-4 w-4 mr-2" />
                                        Connect Microsoft
                                    </>
                                )}
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Completion */}
            <Card className={hasAnyIntegration ? 'border-green-200 bg-green-50' : ''}>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <CheckCircle className={`h-5 w-5 ${hasAnyIntegration ? 'text-green-600' : 'text-gray-400'}`} />
                        3. Complete Setup
                    </CardTitle>
                    <CardDescription>
                        {hasAnyIntegration
                            ? "You're all set! You can always add more integrations later."
                            : "Connect at least one service to get started with Briefly."
                        }
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {hasAnyIntegration && (
                            <div className="text-sm text-gray-600">
                                <p><strong>Connected services:</strong></p>
                                <div className="flex gap-2 mt-2">
                                    {hasGoogleIntegration && (
                                        <Badge variant="default">Google</Badge>
                                    )}
                                    {hasMicrosoftIntegration && (
                                        <Badge variant="default">Microsoft</Badge>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-3">
                            <Button
                                onClick={handleCompleteOnboarding}
                                disabled={!hasAnyIntegration}
                                className="flex-1"
                            >
                                {hasAnyIntegration ? 'Complete Setup & Go to Dashboard' : 'Connect a Service First'}
                            </Button>

                            {hasAnyIntegration && (
                                <Button
                                    variant="outline"
                                    onClick={() => router.push('/settings?page=integrations')}
                                >
                                    Add More Services
                                </Button>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default OnboardingPage; 