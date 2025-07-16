'use client';

import { SessionProvider } from 'next-auth/react';
import { ReactNode } from 'react';
import { TokenAutoRefresh } from './token-auto-refresh';

interface AuthSessionProviderProps {
    children: ReactNode;
}

export default function AuthSessionProvider({ children }: AuthSessionProviderProps) {
    return (
        <SessionProvider>
            <TokenAutoRefresh />
            {children}
        </SessionProvider>
    );
}