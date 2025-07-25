import AuthSessionProvider from '@/components/auth/session-provider';
import { IntegrationsProvider } from '@/contexts/integrations-context';
import { UserPreferencesProvider } from '@/contexts/settings-context';
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Briefly',
    description: 'Calendar Intelligence'
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body>
                <AuthSessionProvider>
                    <IntegrationsProvider>
                        <UserPreferencesProvider>
                            {children}
                        </UserPreferencesProvider>
                    </IntegrationsProvider>
                </AuthSessionProvider>
            </body>
        </html>
    )
}
