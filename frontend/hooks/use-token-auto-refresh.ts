'use client';

import { gatewayClient, Integration } from '@/lib/gateway-client';
import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';

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
    const { data: session } = useSession();
    const [lastRefresh, setLastRefresh] = useState(0);
    const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

    const autoRefreshExpiredTokens = useCallback(async (integrationsData: Integration[]) => {
        const expiredIntegrations = integrationsData.filter(integration => {
            return integration.status === 'error' &&
                integration.has_refresh_token &&
                integration.token_expires_at &&
                isTokenExpired(integration.token_expires_at);
        });

        if (expiredIntegrations.length > 0) {
            console.log('Found expired integrations, auto-refreshing tokens:', expiredIntegrations.map(i => i.provider));

            for (const integration of expiredIntegrations) {
                try {
                    console.log(`Auto-refreshing tokens for ${integration.provider}...`);
                    await gatewayClient.refreshIntegrationTokens(integration.provider);
                    console.log(`Successfully auto-refreshed tokens for ${integration.provider}`);
                } catch (error) {
                    console.error(`Failed to auto-refresh tokens for ${integration.provider}:`, error);
                }
            }
        }
    }, []);

    const loadAndRefreshIntegrations = useCallback(async () => {
        if (Date.now() - lastRefresh < REFRESH_INTERVAL) {
            return;
        }

        try {
            const data = await gatewayClient.getIntegrations();
            const integrationsData = data.integrations || [];
            await autoRefreshExpiredTokens(integrationsData);
            setLastRefresh(Date.now());
        } catch (error) {
            console.error('Failed to load integrations for token refresh:', error);
        }
    }, [autoRefreshExpiredTokens, lastRefresh]);

    useEffect(() => {
        if (session) {
            loadAndRefreshIntegrations();
            const intervalId = setInterval(loadAndRefreshIntegrations, REFRESH_INTERVAL);
            return () => clearInterval(intervalId);
        }
    }, [session, loadAndRefreshIntegrations]);
}
