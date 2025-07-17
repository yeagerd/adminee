'use client';

import { useTokenAutoRefresh } from '@/hooks/use-token-auto-refresh';

export function TokenAutoRefresh() {
    useTokenAutoRefresh();
    return null;
}
