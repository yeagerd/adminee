"use client";

import { useSession } from 'next-auth/react';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { INTEGRATION_STATUS } from '../lib/constants';
import gatewayClient, { Integration } from '../lib/gateway-client';

interface IntegrationsContextType {
    integrations: Integration[];
    loading: boolean;
    error: string | null;
    refreshIntegrations: () => Promise<void>;
    activeProviders: string[];
    hasExpiredButRefreshableTokens: boolean;
    triggerAutoRefreshIfNeeded: () => void;
}

const IntegrationsContext = createContext<IntegrationsContextType | undefined>(undefined);

export const IntegrationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { status } = useSession();

    // NEW: Track refresh state to prevent infinite loops and race conditions
    const isRefreshingRef = useRef(false);
    const refreshAttemptsRef = useRef<Record<string, number>>({});

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

    // Helper to determine if an integration is expired but refreshable
    const isExpiredButRefreshableIntegration = useCallback((i: Integration): boolean => {
        return (
            (i.status === INTEGRATION_STATUS.EXPIRED ||
                (i.status === INTEGRATION_STATUS.ACTIVE && isTokenExpired(i.token_expires_at))
            ) &&
            (i.provider === 'google' || i.provider === 'microsoft') &&
            i.has_refresh_token
        );
    }, [isTokenExpired]);

    // Memoized active providers array
    const activeProviders = useMemo(() => {
        return integrations
            .filter(i =>
                i.status === INTEGRATION_STATUS.ACTIVE &&
                (i.provider === 'google' || i.provider === 'microsoft') &&
                !isTokenExpired(i.token_expires_at)
            )
            .map(i => i.provider);
    }, [integrations, isTokenExpired]);

    const hasExpiredButRefreshableTokens = useMemo(() => {
        return integrations.some(isExpiredButRefreshableIntegration);
    }, [integrations, isExpiredButRefreshableIntegration]);

    const triggerAutoRefreshIfNeeded = useCallback(() => {
        const expiredIntegrations = integrations.filter(isExpiredButRefreshableIntegration);
        // For 'expired' status, only try once; for 'active', allow up to 3 attempts
        const shouldRetry = expiredIntegrations.some(i =>
            (i.status === INTEGRATION_STATUS.EXPIRED && (refreshAttemptsRef.current[i.provider] || 0) < 1) ||
            (i.status === INTEGRATION_STATUS.ACTIVE && (refreshAttemptsRef.current[i.provider] || 0) < 3)
        );
        if (
            loading ||
            !hasExpiredButRefreshableTokens ||
            activeProviders.length !== 0 ||
            !shouldRetry ||
            expiredIntegrations.length === 0 ||
            isRefreshingRef.current
        ) {
            return;
        }
        isRefreshingRef.current = true;
        const refreshExpiredTokens = async () => {
            try {
                for (const integration of expiredIntegrations) {
                    // For 'expired' status, only try once; for 'active', allow up to 3 attempts
                    const maxAttempts = integration.status === INTEGRATION_STATUS.EXPIRED ? 1 : 3;
                    if ((refreshAttemptsRef.current[integration.provider] || 0) >= maxAttempts) {
                        continue;
                    }
                    try {
                        await gatewayClient.refreshIntegrationTokens(integration.provider);
                        // Reset attempt counter on success
                        refreshAttemptsRef.current[integration.provider] = 0;
                    } catch {
                        // Increment attempt counter on failure
                        refreshAttemptsRef.current[integration.provider] =
                            (refreshAttemptsRef.current[integration.provider] || 0) + 1;
                    }
                }
                // Refresh the integrations list to get updated token data
                await fetchIntegrations();
            } catch {
            } finally {
                isRefreshingRef.current = false;
            }
        };
        refreshExpiredTokens();
    }, [integrations, isExpiredButRefreshableIntegration, loading, hasExpiredButRefreshableTokens, activeProviders, fetchIntegrations]);

    // Remove the auto-refresh useEffect (now handled by triggerAutoRefreshIfNeeded)

    return (
        <IntegrationsContext.Provider value={{ integrations, loading, error, refreshIntegrations: fetchIntegrations, activeProviders, hasExpiredButRefreshableTokens, triggerAutoRefreshIfNeeded }}>
            {children}
        </IntegrationsContext.Provider>
    );
};

export function useIntegrations() {
    const ctx = useContext(IntegrationsContext);
    if (!ctx) throw new Error('useIntegrations must be used within an IntegrationsProvider');
    return ctx;
} 