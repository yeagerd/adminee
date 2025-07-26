'use client';

import { useUserPreferences } from '@/contexts/settings-context';
import { useCallback } from 'react';

export function useSidebarState() {
    const { userPreferences, setUserPreferences } = useUserPreferences();

    const isExpanded = userPreferences?.ui?.sidebar_expanded ?? true;

    const setExpanded = useCallback(async (expanded: boolean) => {
        try {
            await setUserPreferences({
                ui: {
                    ...userPreferences?.ui,
                    sidebar_expanded: expanded,
                }
            });
        } catch (error) {
            console.warn('Failed to save sidebar state to user preferences:', error);
        }
    }, [setUserPreferences, userPreferences?.ui]);

    return {
        isExpanded,
        setExpanded,
        isLoaded: true, // UserPreferencesProvider handles loading state
    };
} 