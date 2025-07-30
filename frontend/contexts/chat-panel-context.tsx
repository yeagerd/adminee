'use client';

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';

interface ChatPanelState {
    isOpen: boolean;
    width: number;
}

interface ChatPanelContextType {
    isOpen: boolean;
    width: number;
    setIsOpen: (isOpen: boolean) => void;
    setWidth: (width: number) => void;
    toggle: () => void;
    minWidth: number;
    maxWidth: number;
}

const DEFAULT_CHAT_WIDTH = 400;
const MIN_CHAT_WIDTH = 200;
const MAX_CHAT_WIDTH = 800;

const ChatPanelContext = createContext<ChatPanelContextType | undefined>(undefined);

export function ChatPanelProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<ChatPanelState>(() => {
        // Initialize from localStorage if available
        if (typeof window !== 'undefined') {
            try {
                const saved = localStorage.getItem('briefly-chat-panel-state');
                if (saved) {
                    const parsed = JSON.parse(saved);
                    return {
                        isOpen: parsed.isOpen ?? true,
                        width: Math.max(MIN_CHAT_WIDTH, Math.min(MAX_CHAT_WIDTH, parsed.width ?? DEFAULT_CHAT_WIDTH)),
                    };
                }
            } catch (error) {
                console.warn('Failed to load chat panel state from localStorage:', error);
            }
        }
        return {
            isOpen: true,
            width: DEFAULT_CHAT_WIDTH,
        };
    });

    const setIsOpen = useCallback((isOpen: boolean) => {
        setState(prev => ({ ...prev, isOpen }));
    }, []);

    const setWidth = useCallback((width: number) => {
        // Ensure width is within valid bounds and is a positive number
        const clampedWidth = Math.max(MIN_CHAT_WIDTH, Math.min(MAX_CHAT_WIDTH, Math.max(0, width)));
        setState(prev => ({ ...prev, width: clampedWidth }));
    }, []);

    const toggle = useCallback(() => {
        setState(prev => ({ ...prev, isOpen: !prev.isOpen }));
    }, []);

    // Persist state to localStorage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                localStorage.setItem('briefly-chat-panel-state', JSON.stringify(state));
            } catch (error) {
                console.warn('Failed to save chat panel state to localStorage:', error);
            }
        }
    }, [state]);

    const value: ChatPanelContextType = {
        isOpen: state.isOpen,
        width: state.width,
        setIsOpen,
        setWidth,
        toggle,
        minWidth: MIN_CHAT_WIDTH,
        maxWidth: MAX_CHAT_WIDTH,
    };

    return (
        <ChatPanelContext.Provider value={value}>
            {children}
        </ChatPanelContext.Provider>
    );
}

export function useChatPanelState(): ChatPanelContextType {
    const context = useContext(ChatPanelContext);
    if (context === undefined) {
        throw new Error('useChatPanelState must be used within a ChatPanelProvider');
    }
    return context;
} 