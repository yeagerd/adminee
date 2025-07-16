'use client';

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