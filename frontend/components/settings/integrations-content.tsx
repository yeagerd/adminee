'use client';

import { OAuthScope, ScopeSelector } from '@/components/integrations/scope-selector';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration, OAuthStartResponse } from '@/lib/gateway-client';
import { AlertCircle, Calendar, CheckCircle, Mail, RefreshCw, Settings, Shield, XCircle } from 'lucide-react';
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
    }, [integrations.length, shouldRefetch, determinePreferredProvider, isRefreshing]);

    useEffect(() => {
        if (session) {
            loadIntegrations();
        }
    }, [session, loadIntegrations]);

    // Check if we're returning from an OAuth flow
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const oauthReturn = urlParams.get('oauth_return');

        if (oauthReturn === 'true') {
            // Clear the URL parameter
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.delete('oauth_return');
            window.history.replaceState({}, '', newUrl.toString());

            // Force refresh the integrations data
            console.log('Detected OAuth return, forcing refresh...');
            loadIntegrations(true);
        }
    }, [loadIntegrations]);

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

            // Use selected scopes if available, otherwise load and use all available scopes
            let scopesToUse = selectedScopes;
            if (scopesToUse.length === 0) {
                // Load provider scopes and use all of them
                const scopes = await loadProviderScopes(config.provider);
                scopesToUse = scopes.map(scope => scope.name);
            }

            console.log(`Starting OAuth flow for ${config.provider} with scopes:`, scopesToUse);

            const response = await gatewayClient.startOAuthFlow(
                config.provider,
                scopesToUse
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

            // Check if this is a re-authentication required error
            const errorMessage = error instanceof Error ? error.message : String(error);
            if (errorMessage.includes('REAUTHENTICATION_REQUIRED')) {
                // Start a new OAuth flow for re-authentication
                const config = INTEGRATION_CONFIGS.find(c => c.provider === provider);
                if (config) {
                    setError(`Your ${config.name} connection has expired and needs to be renewed. Redirecting to re-authenticate...`);
                    // Small delay to show the message
                    setTimeout(() => {
                        handleConnect(config);
                    }, 2000);
                } else {
                    setError(`Failed to refresh ${provider} tokens. Please try reconnecting.`);
                }
            } else if (errorMessage.includes('Missing refresh token')) {
                // Handle the old error message format as well
                const config = INTEGRATION_CONFIGS.find(c => c.provider === provider);
                if (config) {
                    setError(`Your ${config.name} connection has expired and needs to be renewed. Redirecting to re-authenticate...`);
                    setTimeout(() => {
                        handleConnect(config);
                    }, 2000);
                } else {
                    setError(`Failed to refresh ${provider} tokens. Please try reconnecting.`);
                }
            } else {
                setError(`Failed to refresh ${provider} tokens. Please try again.`);
            }
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
            <div className="grid gap-6">
                {INTEGRATION_CONFIGS
                    .filter(config => !preferredProvider || config.provider === preferredProvider)
                    .map((config) => {
                        const integration = getIntegrationStatus(config.provider);
                        const hasIntegration = integration !== undefined && integration.status === INTEGRATION_STATUS.ACTIVE;
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
                                            {hasIntegration ? (
                                                // Show actual granted scopes for active integration
                                                integration.scopes.map((scope, index) => (
                                                    <div key={index} className="text-xs text-gray-600">
                                                        • {getScopeDescription(scope)}
                                                    </div>
                                                ))
                                            ) : (
                                                // Show default scopes for new/disconnected integration
                                                config.scopes.map((scope, index) => (
                                                    <div key={index} className="text-xs text-gray-600">
                                                        • {getScopeDescription(scope)}
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>

                                    {/* Status Details */}
                                    {integration && (
                                        <div className="space-y-2">
                                            {integration.token_expires_at && (
                                                <div className="text-xs text-gray-600">
                                                    <span className="font-medium">Access token expires:</span>{' '}
                                                    <span className={
                                                        isTokenExpired(integration.token_expires_at)
                                                            ? 'text-red-600 font-medium'
                                                            : isTokenExpiringSoon(integration.token_expires_at)
                                                                ? 'text-orange-600 font-medium'
                                                                : 'text-green-600 font-medium'
                                                    }>
                                                        {parseUtcDate(integration.token_expires_at).toLocaleString(undefined, { timeZoneName: 'short' })}
                                                        {' '}({getTimeUntilExpiration(integration.token_expires_at)})
                                                        {isTokenExpired(integration.token_expires_at) && ' (EXPIRED)'}
                                                        {isTokenExpiringSoon(integration.token_expires_at) && !isTokenExpired(integration.token_expires_at) && ' (EXPIRING SOON)'}
                                                    </span>
                                                </div>
                                            )}
                                            {integration.token_created_at && (
                                                <div className="text-xs text-gray-600">
                                                    <span className="font-medium">Token created:</span>{' '}
                                                    {parseUtcDate(integration.token_created_at).toLocaleString(undefined, { timeZoneName: 'short' })}
                                                </div>
                                            )}
                                            <div className="text-xs text-gray-600">
                                                <span className="font-medium">Tokens:</span>{' '}
                                                <span className={integration.has_access_token ? 'text-green-600' : 'text-red-600'}>
                                                    Access {integration.has_access_token ? '✓' : '✗'}
                                                </span>
                                                {' • '}
                                                <span className={integration.has_refresh_token ? 'text-green-600' : 'text-red-600'}>
                                                    Refresh {integration.has_refresh_token ? '✓' : '✗'}
                                                </span>
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
                                        {!hasIntegration ? (
                                            <>
                                                <Button
                                                    onClick={() => handleScopeSelection(config.provider)}
                                                    disabled={loading}
                                                    className="flex-1"
                                                >
                                                    <Shield className="h-4 w-4 mr-2" />
                                                    Connect
                                                </Button>
                                            </>
                                        ) : (
                                            <>
                                                {integration?.status === INTEGRATION_STATUS.ERROR && !integration?.has_refresh_token ? (
                                                    <Button
                                                        variant="outline"
                                                        onClick={() => handleConnect(config)}
                                                        disabled={loading || isConnecting}
                                                        size="sm"
                                                    >
                                                        <Shield className="h-4 w-4 mr-2" />
                                                        Re-authenticate
                                                    </Button>
                                                ) : (
                                                    <Button
                                                        variant="outline"
                                                        onClick={() => handleRefresh(config.provider)}
                                                        disabled={loading || isRefreshing}
                                                        size="sm"
                                                    >
                                                        <RefreshCw className="h-4 w-2 mr-2" />
                                                        Refresh
                                                    </Button>
                                                )}
                                                <Button
                                                    variant="outline"
                                                    onClick={() => handleScopeSelection(config.provider)}
                                                    disabled={loading}
                                                    size="sm"
                                                >
                                                    <Settings className="h-4 w-4" />
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

            {/* Scope Selection Dialog */}
            <Dialog open={scopeDialogOpen} onOpenChange={setScopeDialogOpen}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>
                            {currentProvider && getIntegrationStatus(currentProvider)?.status === INTEGRATION_STATUS.ACTIVE
                                ? `Modify Permissions for ${currentProvider.toUpperCase()}`
                                : `Connect ${currentProvider?.toUpperCase()} Account`
                            }
                        </DialogTitle>
                        <DialogDescription>
                            {currentProvider && getIntegrationStatus(currentProvider)?.status === INTEGRATION_STATUS.ACTIVE
                                ? "Modify the permissions granted to Briefly. Required permissions are automatically included."
                                : "Select which permissions you'd like to grant to Briefly. All permissions are selected by default for the best experience."
                            }
                        </DialogDescription>
                    </DialogHeader>
                    {currentProvider && providerScopes[currentProvider] && (
                        <ScopeSelector
                            scopes={providerScopes[currentProvider]}
                            selectedScopes={selectedScopes}
                            onScopeChange={setSelectedScopes}
                        />
                    )}
                    <div className="flex justify-end gap-2 pt-4">
                        <Button
                            variant="outline"
                            onClick={() => setScopeDialogOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                setScopeDialogOpen(false);
                                if (currentProvider) {
                                    const config = INTEGRATION_CONFIGS.find(c => c.provider === currentProvider);
                                    if (config) {
                                        handleConnect(config);
                                    }
                                }
                            }}
                        >
                            {currentProvider && getIntegrationStatus(currentProvider)?.status === INTEGRATION_STATUS.ACTIVE
                                ? "Update Permissions"
                                : "Connect Account"
                            }
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
} 