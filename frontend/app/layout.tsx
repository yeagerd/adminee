import AuthSessionProvider from '@/components/auth/session-provider'
import type { Metadata } from 'next'
import './globals.css'

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
                    {children}
                </AuthSessionProvider>
            </body>
        </html>
    )
}
