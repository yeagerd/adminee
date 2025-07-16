'use client';

import { OAuthScope, ScopeSelector } from '@/components/integrations/scope-selector';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration, OAuthStartResponse } from '@/lib/gateway-client';
import { AlertCircle, Calendar, CheckCircle, Mail, RefreshCw, Settings, XCircle } from 'lucide-react';
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
        scopes: [], // Will be loaded from backend
        color: 'bg-blue-500'
    },
    {
        provider: 'microsoft',
        name: 'Microsoft',
        description: 'Connect your Outlook and Microsoft Calendar',
        icon: <Mail className="h-5 w-5" />,
        scopes: [], // Will be loaded from backend
        color: 'bg-orange-500'
    }
];

function parseUtcDate(dateString: string): Date {
    if (dateString.match(/(Z|[+-][0-9]{2}:[0-9]{2})$/)) {
        return new Date(dateString);
    }
    return new Date(dateString + 'Z');
}

function isTokenExpiringSoon(expiresAt: string, warningMinutes: number = 30): boolean {
    const expirationDate = parseUtcDate(expiresAt);
    const now = new Date();
    const warningTime = new Date(now.getTime() + warningMinutes * 60 * 1000);
    return expirationDate <= warningTime;
}

function isTokenExpired(expiresAt: string): boolean {
    const expirationDate = parseUtcDate(expiresAt);
    const now = new Date();
    return expirationDate <= now;
}

function getTimeUntilExpiration(expiresAt: string): string {
    const expirationDate = parseUtcDate(expiresAt);
    const now = new Date();
    const diffMs = expirationDate.getTime() - now.getTime();

    if (diffMs <= 0) {
        return 'Expired';
    }

    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
    } else if (diffHours > 0) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
    } else {
        return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''}`;
    }
}

function getScopeDescription(scope: string): string {
    // Microsoft Graph API scopes - ReadWrite only
    if (scope === 'https://graph.microsoft.com/Mail.ReadWrite') return 'Read and send email messages';
    if (scope === 'https://graph.microsoft.com/Calendars.ReadWrite') return 'Read and create calendar events';
    if (scope === 'https://graph.microsoft.com/Files.ReadWrite') return 'Read and save files to OneDrive';
    if (scope === 'https://graph.microsoft.com/User.Read') return 'Access detailed user profile (job title, department, manager, contact info)';
    if (scope === 'https://graph.microsoft.com/User.ReadWrite') return 'Read and write user profile';
    if (scope === 'https://graph.microsoft.com/Contacts.ReadWrite') return 'Read and manage contacts';
    if (scope === 'https://graph.microsoft.com/Tasks.ReadWrite') return 'Read and write tasks';
    if (scope === 'https://graph.microsoft.com/Notes.ReadWrite') return 'Read and write OneNote notebooks';

    // Google API scopes
    if (scope.includes('gmail')) {
        if (scope.includes('readonly')) return 'Read Gmail messages';
        if (scope.includes('modify')) return 'Read and write Gmail messages';
        if (scope.includes('send')) return 'Send Gmail messages';
        if (scope.includes('compose')) return 'Compose Gmail messages';
    }
    if (scope.includes('calendar')) {
        if (scope.includes('readonly')) return 'Read Google Calendar events';
        if (scope.includes('events')) return 'Read and write Google Calendar events';
    }
    if (scope.includes('drive')) {
        if (scope.includes('readonly')) return 'Read Google Drive files';
        if (scope.includes('file')) return 'Read and write Google Drive files';
    }

    // Standard OAuth scopes
    if (scope === 'openid') return 'OpenID Connect authentication';
    if (scope === 'email') return 'Access email address';
    if (scope === 'profile') return 'Access basic profile information (name, picture)';
    if (scope === 'offline_access') return 'Access when you\'re not present';

    // Fallback
    return scope;
}

export function IntegrationsContent() {
    const { data: session, status } = useSession();
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [loading, setLoading] = useState(true);
    const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [lastFetchTime, setLastFetchTime] = useState<number>(0);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [preferredProvider, setPreferredProvider] = useState<string | null>(null);

    // Scope selection state
    const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
    const [providerScopes, setProviderScopes] = useState<Record<string, OAuthScope[]>>({});
    const [scopeDialogOpen, setScopeDialogOpen] = useState(false);
    const [currentProvider, setCurrentProvider] = useState<string | null>(null);

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

    const loadProviderScopes = useCallback(async (provider: string) => {
        try {
            if (providerScopes[provider]) {
                console.log(`Using cached scopes for ${provider}:`, providerScopes[provider].map(s => s.name));
                return providerScopes[provider];
            }

            console.log(`Loading scopes for ${provider}...`);
            const response = await gatewayClient.getProviderScopes(provider);
            const scopes = response.scopes;
            console.log(`Loaded scopes for ${provider}:`, scopes.map(s => s.name));

            setProviderScopes(prev => ({ ...prev, [provider]: scopes }));

            // For new/disconnected integrations, select ALL available scopes by default
            const allScopeNames = scopes.map(scope => scope.name);
            console.log(`Setting selected scopes to all scopes:`, allScopeNames);
            setSelectedScopes(allScopeNames);

            return scopes;
        } catch (error) {
            console.error(`Failed to load scopes for ${provider}:`, error);
            setError(`Failed to load scopes for ${provider}. Please try again.`);
            return [];
        }
    }, [providerScopes]);

    const handleScopeSelection = (provider: string) => {
        setCurrentProvider(provider);
        setScopeDialogOpen(true);

        // Load provider scopes and set initial selection
        loadProviderScopes(provider).then(() => {
            const existingIntegration = getIntegrationStatus(provider);
            if (existingIntegration && existingIntegration.status === INTEGRATION_STATUS.ACTIVE && existingIntegration.scopes) {
                // For existing active integrations, merge current scopes with any missing default scopes
                // Also convert any Read-only scopes to ReadWrite scopes
                const currentScopes = new Set(existingIntegration.scopes);
                const availableScopes = providerScopes[provider] || [];
                const defaultScopeNames = availableScopes.map(scope => scope.name);

                // Convert Read-only scopes to ReadWrite scopes
                const convertedScopes = new Set<string>();
                for (const scope of currentScopes) {
                    if (scope === 'https://graph.microsoft.com/Mail.Read') {
                        convertedScopes.add('https://graph.microsoft.com/Mail.ReadWrite');
                    } else if (scope === 'https://graph.microsoft.com/Calendars.Read') {
                        convertedScopes.add('https://graph.microsoft.com/Calendars.ReadWrite');
                    } else if (scope === 'https://graph.microsoft.com/Files.Read') {
                        convertedScopes.add('https://graph.microsoft.com/Files.ReadWrite');
                    } else if (scope === 'https://graph.microsoft.com/Contacts.Read') {
                        convertedScopes.add('https://graph.microsoft.com/Contacts.ReadWrite');
                    } else {
                        convertedScopes.add(scope);
                    }
                }

                // Add any missing default scopes to the current selection
                const mergedScopes = [...convertedScopes];
                for (const scopeName of defaultScopeNames) {
                    if (!convertedScopes.has(scopeName)) {
                        mergedScopes.push(scopeName);
                    }
                }
                setSelectedScopes(mergedScopes);
            }
            // For new/disconnected integrations, all scopes will be selected by default
            // (this is handled in the loadProviderScopes function)
        });
    };

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

            // Determine preferred provider
            const preferred = determinePreferredProvider(integrationsData);
            setPreferredProvider(preferred);

        } catch (error) {
            console.error('Failed to load integrations:', error);
            setError('Failed to load integrations. Please try again.');
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    }, [integrations.length, shouldRefetch, isRefreshing, determinePreferredProvider]);

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

            // Load scopes for this provider
            const scopes = await loadProviderScopes(config.provider);
            if (scopes.length === 0) {
                setError(`No scopes available for ${config.name}. Please try again.`);
                return;
            }

            // Start OAuth flow
            const response: OAuthStartResponse = await gatewayClient.startOAuthFlow(config.provider, selectedScopes);
            console.log('OAuth start response:', response);

            if (response.auth_url) {
                // Redirect to OAuth provider
                window.location.href = response.auth_url;
            } else {
                setError('Failed to start OAuth flow. Please try again.');
            }
        } catch (error) {
            console.error('Failed to connect integration:', error);
            setError('Failed to connect integration. Please try again.');
        } finally {
            setConnectingProvider(null);
        }
    };

    const handleDisconnect = async (provider: string) => {
        try {
            setError(null);
            await gatewayClient.disconnectIntegration(provider);
            console.log(`Disconnected ${provider} integration`);

            // Refresh integrations list
            await loadIntegrations(true);
        } catch (error) {
            console.error('Failed to disconnect integration:', error);
            setError('Failed to disconnect integration. Please try again.');
        }
    };

    const handleRefresh = async (provider: string) => {
        try {
            setIsRefreshing(true);
            setError(null);
            await gatewayClient.refreshIntegration(provider);
            console.log(`Refreshed ${provider} integration`);

            // Refresh integrations list
            await loadIntegrations(true);
        } catch (error) {
            console.error('Failed to refresh integration:', error);
            setError('Failed to refresh integration. Please try again.');
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
                return <CheckCircle className="h-4 w-4 text-green-500" />;
            case INTEGRATION_STATUS.INACTIVE:
                return <XCircle className="h-4 w-4 text-gray-400" />;
            case INTEGRATION_STATUS.ERROR:
                return <AlertCircle className="h-4 w-4 text-red-500" />;
            default:
                return <XCircle className="h-4 w-4 text-gray-400" />;
        }
    };

    const getStatusColor = (status?: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
        switch (status) {
            case INTEGRATION_STATUS.ACTIVE:
                return 'default';
            case INTEGRATION_STATUS.INACTIVE:
                return 'secondary';
            case INTEGRATION_STATUS.ERROR:
                return 'destructive';
            default:
                return 'outline';
        }
    };

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
        <div className="p-6 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Integrations</h1>
                <p className="text-gray-600 mt-2">Connect your calendar and email accounts to get started with Briefly</p>
            </div>

            {/* Error Alert */}
            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Integration Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {INTEGRATION_CONFIGS.map((config) => {
                    const integration = getIntegrationStatus(config.provider);
                    const isConnecting = connectingProvider === config.provider;
                    const isRefreshingIntegration = isRefreshing && integration?.provider === config.provider;

                    return (
                        <Card key={config.provider} className="relative">
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-3">
                                        <div className={`p-2 rounded-lg ${config.color}`}>
                                            {config.icon}
                                        </div>
                                        <div>
                                            <CardTitle className="text-lg">{config.name}</CardTitle>
                                            <CardDescription>{config.description}</CardDescription>
                                        </div>
                                    </div>
                                    {integration && getStatusIcon(integration.status)}
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {integration ? (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium">Status</span>
                                            <Badge variant={getStatusColor(integration.status)}>
                                                {integration.status === INTEGRATION_STATUS.INACTIVE ? 'Disconnected' : integration.status}
                                            </Badge>
                                        </div>

                                        {integration.expires_at && (
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-medium">Token expires</span>
                                                <span className={`text-sm ${isTokenExpiringSoon(integration.expires_at) ? 'text-orange-600' : 'text-gray-600'}`}>
                                                    {getTimeUntilExpiration(integration.expires_at)}
                                                </span>
                                            </div>
                                        )}

                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium">Permissions</span>
                                            <span className="text-sm text-gray-600">
                                                {integration.scopes?.length || 0} permission{(integration.scopes?.length || 0) !== 1 ? 's' : ''}
                                            </span>
                                        </div>

                                        <div className="flex space-x-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleScopeSelection(config.provider)}
                                                className="flex-1"
                                            >
                                                <Settings className="h-4 w-4 mr-2" />
                                                Manage Permissions
                                            </Button>

                                            {integration.status === INTEGRATION_STATUS.ACTIVE && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => handleRefresh(config.provider)}
                                                    disabled={isRefreshingIntegration}
                                                    className="flex-1"
                                                >
                                                    <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshingIntegration ? 'animate-spin' : ''}`} />
                                                    Refresh
                                                </Button>
                                            )}

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleDisconnect(config.provider)}
                                                className="flex-1"
                                            >
                                                Disconnect
                                            </Button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <p className="text-sm text-gray-600">
                                            Connect your {config.name} account to access your calendar and email.
                                        </p>
                                        <Button
                                            onClick={() => handleConnect(config)}
                                            disabled={isConnecting}
                                            className="w-full"
                                        >
                                            {isConnecting ? (
                                                <>
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    Connecting...
                                                </>
                                            ) : (
                                                `Connect ${config.name}`
                                            )}
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Scope Selection Dialog */}
            <Dialog open={scopeDialogOpen} onOpenChange={setScopeDialogOpen}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Manage Permissions</DialogTitle>
                        <DialogDescription>
                            Select which permissions you want to grant to {currentProvider?.charAt(0).toUpperCase()}{currentProvider?.slice(1)}.
                        </DialogDescription>
                    </DialogHeader>

                    {currentProvider && providerScopes[currentProvider] && (
                        <ScopeSelector
                            scopes={providerScopes[currentProvider]}
                            selectedScopes={selectedScopes}
                            onSelectionChange={setSelectedScopes}
                            getScopeDescription={getScopeDescription}
                        />
                    )}

                    <div className="flex justify-end space-x-2">
                        <Button variant="outline" onClick={() => setScopeDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                if (currentProvider) {
                                    handleConnect(INTEGRATION_CONFIGS.find(c => c.provider === currentProvider)!);
                                }
                                setScopeDialogOpen(false);
                            }}
                        >
                            Update Permissions
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
} 