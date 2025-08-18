"use client";

import { userApi } from '@/api';
import type { Integration } from '@/api/types/common';
import { useSession } from 'next-auth/react';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { INTEGRATION_STATUS } from '../lib/constants';
import { IntegrationProvider } from '@/types/api/user';

interface IntegrationsContextType {
    integrations: Integration[];
    loading: boolean;
    error: string | null;
    refreshIntegrations: () => Promise<void>;
    activeProviders: string[];
    hasExpiredButRefreshableTokens: boolean;
    triggerAutoRefreshIfNeeded: () => Promise<void>;
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

    const loadIntegrations = async () => {
        try {
            const resp = await userApi.getIntegrations();
            // Convert IntegrationResponse to Integration type
            const convertedIntegrations: Integration[] = (resp.integrations || []).map(integration => ({
                ...integration,
                scopes: integration.scopes || []
            }));
            setIntegrations(convertedIntegrations);
        } catch (error) {
            console.error('Failed to load integrations:', error);
        }
    };

    useEffect(() => {
        if (status === 'authenticated') {
            loadIntegrations();
        } else if (status === 'unauthenticated') {
            setIntegrations([]);
            setError(null);
            setLoading(false);
        }
    }, [loadIntegrations, status]);

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

    const triggerAutoRefreshIfNeeded = useCallback(async () => {
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
        try {
            let hasSuccessfulRefreshes = false;

            for (const integration of expiredIntegrations) {
                const attempts = refreshAttemptsRef.current[integration.provider] || 0;
                if (
                    (integration.status === INTEGRATION_STATUS.EXPIRED && attempts < 1) ||
                    (integration.status === INTEGRATION_STATUS.ACTIVE && attempts < 3)
                ) {
                    try {
                        await userApi.refreshIntegrationTokens(integration.provider as IntegrationProvider);
                        // Reset counter on successful refresh
                        refreshAttemptsRef.current[integration.provider] = 0;
                        hasSuccessfulRefreshes = true;
                        // Wait a bit before trying the next one to avoid overwhelming the server
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    } catch (e) {
                        console.error(`Failed to refresh ${integration.provider} integration:`, e);
                        // Only increment counter on failure
                        refreshAttemptsRef.current[integration.provider] = (attempts || 0) + 1;
                    }
                }
            }

            // Update local state if any tokens were successfully refreshed
            if (hasSuccessfulRefreshes) {
                await loadIntegrations();
            }
        } finally {
            isRefreshingRef.current = false;
        }
    }, [integrations, loading, hasExpiredButRefreshableTokens, activeProviders.length, isExpiredButRefreshableIntegration, loadIntegrations]);

    // Remove the auto-refresh useEffect (now handled by triggerAutoRefreshIfNeeded)

    return (
        <IntegrationsContext.Provider value={{ integrations, loading, error, refreshIntegrations: loadIntegrations, activeProviders, hasExpiredButRefreshableTokens, triggerAutoRefreshIfNeeded }}>
            {children}
        </IntegrationsContext.Provider>
    );
};

export function useIntegrations() {
    const ctx = useContext(IntegrationsContext);
    if (!ctx) throw new Error('useIntegrations must be used within an IntegrationsProvider');
    return ctx;
} 