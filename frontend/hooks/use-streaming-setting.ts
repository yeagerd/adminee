'use client';

import { useEffect, useState } from 'react';

const STREAMING_SETTING_KEY = 'briefly-streaming-enabled';

export function useStreamingSetting() {
    const [enableStreaming, setEnableStreaming] = useState(false);
    const [isLoaded, setIsLoaded] = useState(false);

    // Load setting from localStorage on mount
    useEffect(() => {
        try {
            const saved = localStorage.getItem(STREAMING_SETTING_KEY);
            if (saved !== null) {
                setEnableStreaming(JSON.parse(saved));
            }
        } catch (error) {
            console.warn('Failed to load streaming setting from localStorage:', error);
        } finally {
            setIsLoaded(true);
        }
    }, []);

    // Save setting to localStorage when it changes
    const updateStreamingSetting = (enabled: boolean) => {
        setEnableStreaming(enabled);
        try {
            localStorage.setItem(STREAMING_SETTING_KEY, JSON.stringify(enabled));
        } catch (error) {
            console.warn('Failed to save streaming setting to localStorage:', error);
        }
    };

    return {
        enableStreaming,
        updateStreamingSetting,
        isLoaded,
    };
} 