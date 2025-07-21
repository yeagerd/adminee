"use client";

import { useSession } from 'next-auth/react';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import gatewayClient, { Integration } from '../lib/gateway-client';

interface IntegrationsContextType {
    integrations: Integration[];
    loading: boolean;
    error: string | null;
    refreshIntegrations: () => Promise<void>;
    activeProviders: string[];
}

const IntegrationsContext = createContext<IntegrationsContextType | undefined>(undefined);

export const IntegrationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { status } = useSession();

    const fetchIntegrations = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const resp = await gatewayClient.getIntegrations();
            setIntegrations(resp.integrations || []);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load integrations');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (status === 'authenticated') {
            fetchIntegrations();
        } else if (status === 'unauthenticated') {
            setIntegrations([]);
            setError(null);
            setLoading(false);
        }
    }, [fetchIntegrations, status]);

    // Helper to check if a token is expired
    const isTokenExpired = useCallback((token_expires_at?: string): boolean => {
        if (!token_expires_at) return true;
        const expirationDate = new Date(token_expires_at);
        const now = new Date();
        // Check if the date is valid before comparison
        return isNaN(expirationDate.getTime()) || expirationDate <= now;
    }, []);

    // Memoized active providers array
    const activeProviders = useMemo(() => {
        return integrations
            .filter(i =>
                i.status === 'active' &&
                (i.provider === 'google' || i.provider === 'microsoft') &&
                !isTokenExpired(i.token_expires_at)
            )
            .map(i => i.provider);
    }, [integrations, isTokenExpired]);

    // NEW: Check for expired but refreshable tokens
    const hasExpiredButRefreshableTokens = useMemo(() => {
        return integrations.some(i =>
            i.status === 'active' &&
            (i.provider === 'google' || i.provider === 'microsoft') &&
            isTokenExpired(i.token_expires_at) &&
            i.has_refresh_token
        );
    }, [integrations, isTokenExpired]);

    // NEW: Auto-refresh when we have expired but refreshable tokens
    useEffect(() => {
        if (!loading && hasExpiredButRefreshableTokens && activeProviders.length === 0) {
            console.log('Detected expired but refreshable tokens, triggering auto-refresh...');
            // Trigger the auto-refresh mechanism
            const refreshExpiredTokens = async () => {
                try {
                    const expiredIntegrations = integrations.filter(i =>
                        i.status === 'active' &&
                        (i.provider === 'google' || i.provider === 'microsoft') &&
                        isTokenExpired(i.token_expires_at) &&
                        i.has_refresh_token
                    );

                    if (expiredIntegrations.length > 0) {
                        console.log('Auto-refreshing expired tokens:', expiredIntegrations.map(i => i.provider));
                        for (const integration of expiredIntegrations) {
                            try {
                                console.log(`Auto-refreshing tokens for ${integration.provider}...`);
                                await gatewayClient.refreshIntegrationTokens(integration.provider);
                                console.log(`Successfully auto-refreshed tokens for ${integration.provider}`);
                            } catch (error) {
                                console.error(`Failed to auto-refresh tokens for ${integration.provider}:`, error);
                            }
                        }
                        // Refresh the integrations list to get updated token data
                        await fetchIntegrations();
                    }
                } catch (error) {
                    console.error('Failed to auto-refresh expired tokens:', error);
                }
            };
            refreshExpiredTokens();
        }
    }, [loading, hasExpiredButRefreshableTokens, activeProviders.length, integrations, isTokenExpired, fetchIntegrations]);

    return (
        <IntegrationsContext.Provider value={{ integrations, loading, error, refreshIntegrations: fetchIntegrations, activeProviders }}>
            {children}
        </IntegrationsContext.Provider>
    );
};

export function useIntegrations() {
    const ctx = useContext(IntegrationsContext);
    if (!ctx) throw new Error('useIntegrations must be used within an IntegrationsProvider');
    return ctx;
} 