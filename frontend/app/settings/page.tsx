'use client';

import AppLayout from '@/components/layout/app-layout';
import SettingsSidebar from '@/components/layout/settings-sidebar';
import { SettingsContent } from '@/components/settings-content';
import { SettingsProvider } from '@/contexts/settings-context';
import { useSession } from 'next-auth/react';
import { Suspense } from 'react';

function SettingsPageContent() {
    const { data: session, status } = useSession();

    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
                    <p>Please sign in to access your settings</p>
                </div>
            </div>
        );
    }

    return (
        <AppLayout
            sidebar={<SettingsSidebar />}
            main={
                <div className="h-full flex flex-col">
                    <div className="flex-1 overflow-auto">
                        <SettingsContent />
                    </div>
                </div>
            }
        />
    );
}

export default function SettingsPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            <SettingsProvider>
                <SettingsPageContent />
            </SettingsProvider>
        </Suspense>
    );
} 