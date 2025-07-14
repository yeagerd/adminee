'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration, OAuthStartResponse } from '@/lib/gateway-client';
import { AlertCircle, Calendar, CheckCircle, Mail, RefreshCw, Shield, User, XCircle } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

interface IntegrationConfig {
    provider: string;
    name: string;
    description: string;
    icon: React.ReactNode;
    scopes: string[];
    color: string;
}

const INTEGRATION_CONFIGS: IntegrationConfig[] = [
    {
        provider: 'google',
        name: 'Google',
        description: 'Connect your Gmail and Google Calendar',
        icon: <Calendar className="h-5 w-5" />,
        scopes: [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar'
        ],
        color: 'bg-blue-500'
    },
    {
        provider: 'microsoft',
        name: 'Microsoft',
        description: 'Connect your Outlook and Microsoft Calendar',
        icon: <Mail className="h-5 w-5" />,
        scopes: [
            'https://graph.microsoft.com/User.Read',
            'https://graph.microsoft.com/Calendars.ReadWrite',
            'https://graph.microsoft.com/Mail.Read'
        ],
        color: 'bg-orange-500'
    }
];

function parseUtcDate(dateString: string): Date {
    if (dateString.match(/(Z|[+-][0-9]{2}:[0-9]{2})$/)) {
        return new Date(dateString);
    }
    return new Date(dateString + 'Z');
}

export default function IntegrationsPage() {
    const { data: session, status } = useSession();
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [loading, setLoading] = useState(true);
    const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [lastFetchTime, setLastFetchTime] = useState<number>(0);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [preferredProvider, setPreferredProvider] = useState<string | null>(null);

    // Cache duration: 5 minutes
    const CACHE_DURATION = 5 * 60 * 1000;

    const shouldRefetch = useCallback(() => {
        return Date.now() - lastFetchTime > CACHE_DURATION;
    }, [lastFetchTime, CACHE_DURATION]);

    const determinePreferredProvider = useCallback((integrations: Integration[]) => {
        // If user has active integrations, use the first one as preferred
        const activeIntegration = integrations.find(integration => integration.status === INTEGRATION_STATUS.ACTIVE);
        if (activeIntegration) {
            return activeIntegration.provider;
        }

        // If no active integrations, check if user has any integrations at all
        if (integrations.length > 0) {
            return integrations[0].provider;
        }

        return null;
    }, []);

    const loadIntegrations = useCallback(async (forceRefresh = false) => {
        // Don't refetch if we have recent data and not forcing refresh
        if (!forceRefresh && integrations.length > 0 && !shouldRefetch()) {
            return;
        }

        try {
            setError(null);
            if (!isRefreshing) {
                setLoading(true);
            }
            console.log('Loading integrations...');
            const data = await gatewayClient.getIntegrations();
            console.log('Integrations data:', data);
            // The backend returns { integrations: [...], total: ..., active_count: ..., error_count: ... }
            // Extract just the integrations array
            const integrationsData = data.integrations || [];
            setIntegrations(integrationsData);
            setLastFetchTime(Date.now());
            console.log('Integrations state updated:', integrationsData);

            // Determine preferred provider from integrations
            const preferred = determinePreferredProvider(integrationsData);
            setPreferredProvider(preferred);
        } catch (error: unknown) {
            console.error('Failed to load integrations:', error);
            setError('Failed to load integrations. Please try again.');
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    }, [integrations.length, shouldRefetch, determinePreferredProvider]);

    useEffect(() => {
        if (session) {
            loadIntegrations();
        }
    }, [session, loadIntegrations]);

    // Handle window focus to refresh data if needed
    useEffect(() => {
        const handleWindowFocus = () => {
            if (session && shouldRefetch()) {
                console.log('Window focused, refreshing integrations...');
                loadIntegrations(true);
            }
        };

        window.addEventListener('focus', handleWindowFocus);
        return () => window.removeEventListener('focus', handleWindowFocus);
    }, [session, shouldRefetch, loadIntegrations]);

    const handleConnect = async (config: IntegrationConfig) => {
        try {
            setConnectingProvider(config.provider);
            setError(null);

            const response = await gatewayClient.startOAuthFlow(
                config.provider,
                config.scopes
            ) as OAuthStartResponse;

            // Update preferred provider when connecting
            setPreferredProvider(config.provider);

            // Redirect to OAuth provider
            window.location.href = response.authorization_url;
        } catch (error: unknown) {
            console.error('Failed to start OAuth flow:', error);
            setError(`Failed to connect ${config.name}. Please try again.`);
            setConnectingProvider(null);
        }
    };

    const handleDisconnect = async (provider: string) => {
        try {
            setError(null);
            console.log(`Disconnecting ${provider} integration...`);
            await gatewayClient.disconnectIntegration(provider);
            console.log('Integration disconnected, clearing frontend cache...');

            // Clear frontend calendar cache for this user
            if (session?.user?.id) {
                const { calendarCache } = await import('../../lib/calendar-cache');
                calendarCache.invalidate(session.user.id);
                console.log('Frontend calendar cache cleared');
            }

            console.log('Reloading integrations...');
            await loadIntegrations(true); // Force refresh
            console.log('Integrations reloaded');
        } catch (error: unknown) {
            console.error('Failed to disconnect integration:', error);
            setError(`Failed to disconnect ${provider} integration. Please try again.`);
        }
    };

    const handleRefresh = async (provider: string) => {
        try {
            setError(null);
            setIsRefreshing(true);
            console.log(`Refreshing tokens for ${provider}...`);
            const refreshResult = await gatewayClient.refreshIntegrationTokens(provider);
            console.log('Refresh result:', refreshResult);
            console.log('Reloading integrations...');
            // Add a small delay to ensure the database transaction is committed
            await new Promise(resolve => setTimeout(resolve, 500));
            await loadIntegrations(true); // Force refresh
            console.log('Integrations reloaded');
        } catch (error: unknown) {
            console.error('Failed to refresh tokens:', error);
            setError(`Failed to refresh ${provider} tokens. Please try again.`);
        } finally {
            setIsRefreshing(false);
        }
    };

    const getIntegrationStatus = (provider: string): Integration | undefined => {
        return integrations.find(integration => integration.provider === provider);
    };

    const getStatusIcon = (status?: string) => {
        switch (status) {
            case INTEGRATION_STATUS.ACTIVE:
                return <CheckCircle className="h-4 w-4 text-green-600" />;
            case INTEGRATION_STATUS.ERROR:
                return <XCircle className="h-4 w-4 text-red-600" />;
            case INTEGRATION_STATUS.PENDING:
                return <RefreshCw className="h-4 w-4 text-yellow-600" />;
            case INTEGRATION_STATUS.INACTIVE:
                return <AlertCircle className="h-4 w-4 text-gray-400" />;
            default:
                return <AlertCircle className="h-4 w-4 text-gray-400" />;
        }
    };

    const getStatusColor = (status?: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
        switch (status) {
            case INTEGRATION_STATUS.ACTIVE:
                return 'default';
            case INTEGRATION_STATUS.ERROR:
                return 'destructive';
            case INTEGRATION_STATUS.PENDING:
                return 'secondary';
            case INTEGRATION_STATUS.INACTIVE:
                return 'outline';
            default:
                return 'outline';
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
                        <CardDescription>Please sign in to manage your integrations</CardDescription>
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

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                <div className="space-y-6">
                    {/* Header */}
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Integrations</h1>
                        <p className="text-gray-600 mt-2">
                            Connect your calendar and email accounts to enhance your Briefly experience
                        </p>
                    </div>

                    {/* Error Alert */}
                    {error && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {/* Integration Cards */}
                    <div className="grid gap-6 md:grid-cols-2">
                        {INTEGRATION_CONFIGS
                            .filter(config => !preferredProvider || config.provider === preferredProvider)
                            .map((config) => {
                                const integration = getIntegrationStatus(config.provider);
                                const isConnected = integration?.status === INTEGRATION_STATUS.ACTIVE;
                                const isConnecting = connectingProvider === config.provider;

                                // Debug logging
                                if (config.provider === 'microsoft') {
                                    console.log(`Microsoft integration state:`, integration);
                                }

                                return (
                                    <Card key={config.provider} className="relative">
                                        <CardHeader>
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div className={`p-2 rounded-lg ${config.color} text-white`}>
                                                        {config.icon}
                                                    </div>
                                                    <div>
                                                        <CardTitle className="text-lg">{config.name}</CardTitle>
                                                        <CardDescription>{config.description}</CardDescription>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {getStatusIcon(integration?.status)}
                                                    <Badge variant={getStatusColor(integration?.status)}>
                                                        {integration?.status === INTEGRATION_STATUS.INACTIVE ? 'Disconnected' :
                                                            integration?.status || 'Not Connected'}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            {/* Scopes */}
                                            <div>
                                                <h4 className="text-sm font-medium text-gray-700 mb-2">Permissions:</h4>
                                                <div className="space-y-1">
                                                    {config.scopes.map((scope, index) => (
                                                        <div key={index} className="text-xs text-gray-600">
                                                            • {scope.includes('calendar') ? 'Calendar access' :
                                                                scope.includes('mail') || scope.includes('gmail') ? 'Email access' :
                                                                    scope.includes('User.Read') ? 'Profile access' : scope}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Status Details */}
                                            {integration && (
                                                <div className="space-y-2">
                                                    <div className="text-xs text-gray-600">
                                                        <span className="font-medium">Scopes:</span> {integration.scopes.join(', ')}
                                                    </div>
                                                    {integration.last_sync_at && (
                                                        <div className="text-xs text-gray-600">
                                                            <span className="font-medium">Last sync:</span>{' '}
                                                            {parseUtcDate(integration.last_sync_at).toLocaleString(undefined, { timeZoneName: 'short' })}
                                                        </div>
                                                    )}
                                                    {integration.last_error && (
                                                        <div className="text-xs text-red-600">
                                                            <span className="font-medium">Error:</span> {integration.last_error}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Actions */}
                                            <div className="flex gap-2">
                                                {!isConnected ? (
                                                    <Button
                                                        onClick={() => handleConnect(config)}
                                                        disabled={isConnecting || loading}
                                                        className="flex-1"
                                                    >
                                                        {isConnecting ? (
                                                            <>
                                                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                                                Connecting...
                                                            </>
                                                        ) : (
                                                            <>
                                                                <Shield className="h-4 w-4 mr-2" />
                                                                Connect
                                                            </>
                                                        )}
                                                    </Button>
                                                ) : (
                                                    <>
                                                        <Button
                                                            variant="outline"
                                                            onClick={() => handleRefresh(config.provider)}
                                                            disabled={loading}
                                                            size="sm"
                                                        >
                                                            <RefreshCw className="h-4 w-4 mr-2" />
                                                            Refresh
                                                        </Button>
                                                        <Button
                                                            variant="destructive"
                                                            onClick={() => handleDisconnect(config.provider)}
                                                            disabled={loading}
                                                            size="sm"
                                                        >
                                                            <XCircle className="h-4 w-4 mr-2" />
                                                            Disconnect
                                                        </Button>
                                                    </>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                );
                            })}
                    </div>

                    {/* Help Section */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <User className="h-5 w-5" />
                                Need Help?
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="text-sm text-gray-600">
                                <p>
                                    <strong>Google:</strong> Allows Briefly to access your Gmail for email analysis and Google Calendar for meeting preparation.
                                </p>
                                <p className="mt-2">
                                    <strong>Microsoft:</strong> Connects to your Outlook email and Microsoft Calendar to provide comprehensive meeting insights.
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <Button variant="outline" asChild size="sm">
                                    <Link href="/profile">View Profile</Link>
                                </Button>
                                <Button variant="outline" asChild size="sm">
                                    <Link href="/dashboard">Go to Dashboard</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
} 