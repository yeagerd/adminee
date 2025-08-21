'use client';

import { SessionProvider } from 'next-auth/react';
import { ReactNode } from 'react';

interface AuthSessionProviderProps {
    children: ReactNode;
}

export default function AuthSessionProvider({ children }: AuthSessionProviderProps) {
    return (
        <SessionProvider
            // Increase the session polling interval from default (24 hours) to reduce requests
            refetchInterval={0} // Disable automatic session refetching
            refetchOnWindowFocus={false} // Disable refetch on window focus/blur
            refetchWhenOffline={false} // Disable refetch when going online
        >
            {children}
        </SessionProvider>
    );
}