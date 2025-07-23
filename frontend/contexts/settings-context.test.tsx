import { act, renderHook } from '@testing-library/react';
import React from 'react';
import { UserPreferencesProvider, useUserPreferences } from './settings-context';

function wrapper({ children }: { children: React.ReactNode }) {
    return <UserPreferencesProvider>{children}</UserPreferencesProvider>;
}

describe('UserPreferencesProvider', () => {
    it('defaults to browser timezone if no manual override', () => {
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        expect(result.current.effectiveTimezone).toBeDefined();
    });

    it('uses manual timezone if set', async () => {
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        await act(async () => {
            await result.current.setUserPreferences({ timezone_mode: 'manual', manual_timezone: 'Europe/Paris' });
        });
        expect(result.current.effectiveTimezone).toBe('Europe/Paris');
    });

    it('falls back to browser timezone if manual is empty', async () => {
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        await act(async () => {
            await result.current.setUserPreferences({ timezone_mode: 'manual', manual_timezone: '' });
        });
        expect(result.current.effectiveTimezone).toBeDefined();
    });
}); 