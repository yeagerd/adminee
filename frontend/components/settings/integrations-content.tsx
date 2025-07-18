'use client';

import { OAuthScope, ScopeSelector } from '@/components/integrations/scope-selector';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useIntegrations } from '@/contexts/integrations-context';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration, OAuthStartResponse } from '@/lib/gateway-client';
import { AlertCircle, Calendar, Mail, Settings } from 'lucide-react';
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

export function IntegrationsContent() {
    const { data: session, status } = useSession();
    const { integrations, loading, error, refreshIntegrations } = useIntegrations();
    const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
    const [providerScopes, setProviderScopes] = useState<Record<string, OAuthScope[]>>({});
    const [scopeDialogOpen, setScopeDialogOpen] = useState(false);
    const [currentProvider, setCurrentProvider] = useState<string | null>(null);

    // Scope selection state
    const [selectedScopes, setSelectedScopes] = useState<string[]>([]);

    // Cache duration: 5 minutes
    // Removed unused functions and variables: parseUtcDate, status, preferredProvider, CACHE_DURATION, determinePreferredProvider

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
            // error is now handled by the global context
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

    // Only refresh integrations on OAuth return (not on every render)
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const oauthReturn = urlParams.get('oauth_return');
        if (oauthReturn === 'true') {
            // Clear the URL parameter
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.delete('oauth_return');
            window.history.replaceState({}, '', newUrl.toString());
            // Refresh the global context ONCE
            refreshIntegrations();
        }
    }, [refreshIntegrations]);

    // Removed window focus handler to prevent infinite loop
    // The auto refresh hook will handle periodic refreshes

    const handleConnect = async (config: IntegrationConfig) => {
        try {
            setConnectingProvider(config.provider);
            // error is now handled by the global context

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
            // Removed unused functions and variables: parseUtcDate, status, preferredProvider, CACHE_DURATION, determinePreferredProvider

            // Redirect to OAuth provider
            window.location.href = response.authorization_url;
        } catch (error: unknown) {
            console.error('Failed to start OAuth flow:', error);
            // error is now handled by the global context
            setConnectingProvider(null);
        }
    };

    const handleDisconnect = async (provider: string) => {
        try {
            // error is now handled by the global context
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
            await refreshIntegrations(); // No arguments
            console.log('Integrations reloaded');
        } catch (error: unknown) {
            console.error('Failed to disconnect integration:', error);
            // error is now handled by the global context
        }
    };

    const getIntegrationStatus = (provider: string): Integration | undefined => {
        return integrations.find(integration => integration.provider === provider);
    };

    // Get the user's login provider from the session
    const sessionProvider = session?.provider || null;

    // Only show the integration config matching the session provider
    const visibleIntegrationConfigs = INTEGRATION_CONFIGS.filter(
        config => config.provider === sessionProvider
    );

    if (loading) {
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
                {visibleIntegrationConfigs.map((config) => {
                    const integration = getIntegrationStatus(config.provider);
                    const isConnected = integration && (integration.status === INTEGRATION_STATUS.ACTIVE || integration.status === INTEGRATION_STATUS.INACTIVE);
                    const canConnect = config.provider === sessionProvider && !isConnected;
                    return (
                        <Card key={config.provider} className="mb-4">
                            <CardHeader className="flex flex-row items-center gap-4">
                                <div className={`rounded-full p-2 ${config.color}`}>{config.icon}</div>
                                <div>
                                    <CardTitle>{config.name}</CardTitle>
                                    <CardDescription>{config.description}</CardDescription>
                                </div>
                            </CardHeader>
                            <CardContent className="flex items-center gap-2">
                                {/* Connect button opens permissions dialog */}
                                <Button
                                    onClick={() => handleScopeSelection(config.provider)}
                                    disabled={!canConnect || connectingProvider === config.provider}
                                    className="mr-2"
                                >
                                    {isConnected ? 'Connected' : connectingProvider === config.provider ? 'Connecting...' : 'Connect'}
                                </Button>
                                {/* Show gear/settings button for editing permissions when connected */}
                                {isConnected && (
                                    <Button
                                        variant="outline"
                                        onClick={() => handleScopeSelection(config.provider)}
                                        className="ml-2"
                                        title="Edit permissions"
                                    >
                                        <Settings className="h-4 w-4" />
                                    </Button>
                                )}
                                {isConnected && (
                                    <Button
                                        variant="outline"
                                        onClick={() => handleDisconnect(config.provider)}
                                        className="ml-2"
                                    >
                                        Disconnect
                                    </Button>
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