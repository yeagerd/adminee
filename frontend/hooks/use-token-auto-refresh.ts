'use client';

import { gatewayClient, Integration } from '@/lib/gateway-client';
import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useRef } from 'react';

function parseUtcDate(dateString: string): Date {
    if (dateString.match(/(Z|[+-][0-9]{2}:[0-9]{2})$/)) {
        return new Date(dateString);
    }
    return new Date(dateString + 'Z');
}

function isTokenExpired(expiresAt: string): boolean {
    const expirationDate = parseUtcDate(expiresAt);
    const now = new Date();
    return expirationDate <= now;
}

export function useTokenAutoRefresh() {
    const ENABLE_TOKEN_AUTO_REFRESH = false; // Set to true to enable auto-refresh
    const { data: session } = useSession();
    const lastRefreshRef = useRef(0);
    const isRefreshingRef = useRef(false);
    const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

    if (!ENABLE_TOKEN_AUTO_REFRESH) {
        console.log('Auto refresh hook is currently disabled.');
        return;
    }

    const autoRefreshExpiredTokens = useCallback(async (integrationsData: Integration[]) => {
        const expiredIntegrations = integrationsData.filter(integration => {
            return integration.status === 'error' &&
                integration.has_refresh_token &&
                integration.token_expires_at &&
                isTokenExpired(integration.token_expires_at);
        });

        if (expiredIntegrations.length > 0) {
            console.log('Found expired integrations, auto-refreshing tokens:', expiredIntegrations.map(i => i.provider));
            let refreshed = false;
            for (const integration of expiredIntegrations) {
                try {
                    console.log(`Auto-refreshing tokens for ${integration.provider}...`);
                    await gatewayClient.refreshIntegrationTokens(integration.provider);
                    console.log(`Successfully auto-refreshed tokens for ${integration.provider}`);
                    refreshed = true;
                } catch (error) {
                    console.error(`Failed to auto-refresh tokens for ${integration.provider}:`, error);
                }
            }
            if (refreshed) {
                // No event dispatch to avoid circular dependency
                console.log('Tokens refreshed.');
            }
        }
    }, []);

    const loadAndRefreshIntegrations = useCallback(async () => {
        // Prevent multiple simultaneous refreshes
        if (isRefreshingRef.current) {
            console.log('Auto refresh already in progress, skipping...');
            return;
        }

        // Check if enough time has passed since last refresh
        if (Date.now() - lastRefreshRef.current < REFRESH_INTERVAL) {
            return;
        }

        isRefreshingRef.current = true;
        try {
            console.log('Auto refresh: Loading integrations...');
            const data = await gatewayClient.getIntegrations();
            const integrationsData = data.integrations || [];
            await autoRefreshExpiredTokens(integrationsData);
            lastRefreshRef.current = Date.now();
            console.log('Auto refresh: Completed successfully');
        } catch (error) {
            console.error('Failed to load integrations for token refresh:', error);
        } finally {
            isRefreshingRef.current = false;
        }
    }, [autoRefreshExpiredTokens]);

    useEffect(() => {
        if (session) {
            // Initial load
            loadAndRefreshIntegrations();
            // Set up interval for periodic refresh
            const intervalId = setInterval(loadAndRefreshIntegrations, REFRESH_INTERVAL);
            return () => clearInterval(intervalId);
        }
    }, [session, loadAndRefreshIntegrations]);
}
