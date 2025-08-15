'use client';

import { userApi } from '@/api';
import { getUserTimezone } from '@/lib/utils';
import { useSession } from 'next-auth/react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

export type SettingsPage = 'profile' | 'integrations' | 'billing' | 'security' | 'notifications';

interface SettingsContextType {
    currentPage: SettingsPage;
    setCurrentPage: (page: SettingsPage) => void;
    isPageEnabled: (page: SettingsPage) => boolean;
    isActivePage: (page: SettingsPage) => boolean;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const DEFAULT_PAGE: SettingsPage = 'profile';

const ENABLED_PAGES: SettingsPage[] = ['profile', 'integrations'];

export function SettingsProvider({ children }: { children: ReactNode }) {
    const [currentPage, setCurrentPageState] = useState<SettingsPage>(DEFAULT_PAGE);
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    // Initialize from URL params
    useEffect(() => {
        const pageParam = searchParams.get('page') as SettingsPage;
        if (pageParam && ENABLED_PAGES.includes(pageParam)) {
            setCurrentPageState(pageParam);
        } else if (!pageParam) {
            // Set default page if no page param
            const params = new URLSearchParams(searchParams.toString());
            params.set('page', DEFAULT_PAGE);
            router.replace(`${pathname}?${params.toString()}`, { scroll: false });
        }
    }, [searchParams, router, pathname]);

    const setCurrentPage = (page: SettingsPage) => {
        if (!isPageEnabled(page)) return;

        setCurrentPageState(page);
        const params = new URLSearchParams(searchParams.toString());
        params.set('page', page);
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    };

    const isPageEnabled = (page: SettingsPage): boolean => {
        return ENABLED_PAGES.includes(page);
    };

    const isActivePage = (page: SettingsPage): boolean => {
        return currentPage === page;
    };

    return (
        <SettingsContext.Provider value={{
            currentPage,
            setCurrentPage,
            isPageEnabled,
            isActivePage,
        }}>
            {children}
        </SettingsContext.Provider>
    );
}

export function useSettings() {
    const context = useContext(SettingsContext);
    if (context === undefined) {
        throw new Error('useSettings must be used within a SettingsProvider');
    }
    return context;
}

export interface UserPreferences {
    timezone_mode: 'auto' | 'manual';
    manual_timezone: string;
    ui?: {
        sidebar_expanded?: boolean;
    };
    privacy?: {
        shipment_data_collection?: boolean;
        data_collection?: boolean;
        analytics?: boolean;
        personalization?: boolean;
    };
    // ...other fields as needed
}

interface UserPreferencesContextType {
    userPreferences: UserPreferences | null;
    effectiveTimezone: string;
    setUserPreferences: (prefs: Partial<UserPreferences>) => Promise<void>;
}

const UserPreferencesContext = createContext<UserPreferencesContextType | undefined>(undefined);

export function UserPreferencesProvider({ children }: { children: ReactNode }) {
    const { data: session, status } = useSession();
    const [userPreferences, setUserPreferencesState] = useState<UserPreferences | null>(null);
    const [effectiveTimezone, setEffectiveTimezone] = useState<string>(getUserTimezone());

    // Fetch preferences on sign-in
    useEffect(() => {
        if (status === 'authenticated' && session?.user?.id) {
            userApi.getUserPreferences().then((prefsRaw: unknown) => {
                // Type guard and defaults
                const obj = (prefsRaw && typeof prefsRaw === 'object') ? prefsRaw as Record<string, unknown> : {};
                const prefs: UserPreferences = {
                    timezone_mode: (typeof obj.timezone_mode === 'string' && (obj.timezone_mode === 'auto' || obj.timezone_mode === 'manual')) ? obj.timezone_mode : 'auto',
                    manual_timezone: (typeof obj.manual_timezone === 'string') ? obj.manual_timezone : '',
                    ui: { sidebar_expanded: (obj.ui as { sidebar_expanded?: boolean } | undefined)?.sidebar_expanded ?? false },
                    privacy: {
                        shipment_data_collection: (obj.privacy as { shipment_data_collection?: boolean; data_collection?: boolean; analytics?: boolean; personalization?: boolean } | undefined)?.shipment_data_collection ?? true,
                        data_collection: (obj.privacy as { shipment_data_collection?: boolean; data_collection?: boolean; analytics?: boolean; personalization?: boolean } | undefined)?.data_collection ?? true,
                        analytics: (obj.privacy as { shipment_data_collection?: boolean; data_collection?: boolean; analytics?: boolean; personalization?: boolean } | undefined)?.analytics ?? true,
                        personalization: (obj.privacy as { shipment_data_collection?: boolean; data_collection?: boolean; analytics?: boolean; personalization?: boolean } | undefined)?.personalization ?? true,
                    },
                    // ...other fields as needed
                };
                setUserPreferencesState(prefs);
                const tz = (prefs.timezone_mode === 'manual' && prefs.manual_timezone)
                    ? prefs.manual_timezone
                    : getUserTimezone();
                setEffectiveTimezone(tz);
            }).catch(() => {
                setUserPreferencesState(null);
                setEffectiveTimezone(getUserTimezone());
            });
        }
    }, [status, session?.user?.id]);

    // Update preferences and recompute effectiveTimezone
    const setUserPreferences = async (prefs: Partial<UserPreferences>) => {
        const updated: UserPreferences = {
            timezone_mode: prefs.timezone_mode ?? userPreferences?.timezone_mode ?? 'auto',
            manual_timezone: prefs.manual_timezone ?? userPreferences?.manual_timezone ?? '',
            ui: {
                ...userPreferences?.ui,
                ...prefs.ui,
            },
            privacy: {
                ...userPreferences?.privacy,
                ...prefs.privacy,
            },
            // ...other fields as needed
        };
        await userApi.updateUserPreferences(updated as unknown as Record<string, unknown>);
        setUserPreferencesState(updated);
        const tz = (updated.timezone_mode === 'manual' && updated.manual_timezone)
            ? updated.manual_timezone
            : getUserTimezone();
        console.log(`[UserPreferences] Updating timezone to: ${tz}`);
        setEffectiveTimezone(tz);
    };

    return (
        <UserPreferencesContext.Provider value={{ userPreferences, effectiveTimezone, setUserPreferences }}>
            {children}
        </UserPreferencesContext.Provider>
    );
}

export function useUserPreferences() {
    const context = useContext(UserPreferencesContext);
    if (context === undefined) {
        throw new Error('useUserPreferences must be used within a UserPreferencesProvider');
    }
    return context;
}

// Helper function to check if user has consented to shipment data collection
export function useShipmentDataCollectionConsent(): boolean {
    const { userPreferences } = useUserPreferences();
    return userPreferences?.privacy?.shipment_data_collection ?? true; // Default to true
} 