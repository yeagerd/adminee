import { act, renderHook } from '@testing-library/react';
import React from 'react';
import { UserPreferencesProvider, useUserPreferences } from './settings-context';

// Mocks
jest.mock('next-auth/react', () => ({
    useSession: () => ({
        data: { user: { id: 'test-user' } },
        status: 'authenticated',
    }),
}));
jest.mock('@/api', () => ({
    userApi: {
        getUserPreferences: jest.fn(),
        updateUserPreferences: jest.fn(),
    },
}));
jest.mock('@/lib/utils', () => ({
    getUserTimezone: jest.fn(),
}));

import { userApi } from '@/api';
import { getUserTimezone } from '@/lib/utils';

function wrapper({ children }: { children: React.ReactNode }) {
    return <UserPreferencesProvider>{children}</UserPreferencesProvider>;
}

describe('UserPreferencesProvider', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('defaults to browser timezone if no manual override', async () => {
        (getUserTimezone as jest.Mock).mockReturnValue('Browser/Zone');
        (userApi.getUserPreferences as jest.Mock).mockResolvedValue({ timezone_mode: 'auto', manual_timezone: '' });
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        // Wait for useEffect to run
        await act(async () => { });
        expect(result.current.effectiveTimezone).toBe('Browser/Zone');
    });

    it('uses manual timezone if set', async () => {
        (getUserTimezone as jest.Mock).mockReturnValue('Browser/Zone');
        (userApi.getUserPreferences as jest.Mock).mockResolvedValue({ timezone_mode: 'manual', manual_timezone: 'Europe/Paris' });
        (userApi.updateUserPreferences as jest.Mock).mockResolvedValue({});
        const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        await act(async () => {
            await result.current.setUserPreferences({ timezone_mode: 'manual', manual_timezone: 'Europe/Paris' });
        });
        expect(result.current.effectiveTimezone).toBe('Europe/Paris');
        consoleLogSpy.mockRestore();
    });

    it('falls back to browser timezone if manual is empty', async () => {
        (getUserTimezone as jest.Mock).mockReturnValue('Browser/Zone');
        (userApi.getUserPreferences as jest.Mock).mockResolvedValue({ timezone_mode: 'manual', manual_timezone: '' });
        (userApi.updateUserPreferences as jest.Mock).mockResolvedValue({});
        const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
        const { result } = renderHook(() => useUserPreferences(), { wrapper });
        await act(async () => {
            await result.current.setUserPreferences({ timezone_mode: 'manual', manual_timezone: '' });
        });
        expect(result.current.effectiveTimezone).toBe('Browser/Zone');
        consoleLogSpy.mockRestore();
    });
}); 