'use client';

import { Tool, ToolContextType, ToolSettings, ToolState } from '@/types/navigation';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useReducer, useRef } from 'react';

// Initial tool settings
const defaultToolSettings: Record<Tool, ToolSettings> = {
    calendar: { id: 'calendar', enabled: true, preferences: { view: 'week', showWeekends: true } },
    email: { id: 'email', enabled: true, preferences: { view: 'inbox', sortBy: 'date' } },
    documents: { id: 'documents', enabled: true, preferences: { view: 'list', sortBy: 'modified' } },
    tasks: { id: 'tasks', enabled: true, preferences: { view: 'list', showCompleted: false } },
    packages: { id: 'packages', enabled: true, preferences: { view: 'table', showDelivered: false } },
    research: { id: 'research', enabled: true, preferences: { view: 'split', autoSave: true } },
    pulse: { id: 'pulse', enabled: true, preferences: { categories: ['ai', 'pharma', 'fintech'], autoRefresh: true } },
    insights: { id: 'insights', enabled: false, preferences: { view: 'dashboard', refreshInterval: 300 } },
};

// Initial state
const initialState: ToolState = {
    activeTool: 'calendar',
    toolSettings: defaultToolSettings,
    lastVisited: {
        calendar: '/dashboard?tool=calendar',
        email: '/dashboard?tool=email',
        documents: '/dashboard?tool=documents',
        tasks: '/dashboard?tool=tasks',
        packages: '/dashboard?tool=packages',
        research: '/dashboard?tool=research',
        pulse: '/dashboard?tool=pulse',
        insights: '/dashboard?tool=insights',
    },
};

// Action types
type ToolAction =
    | { type: 'SET_ACTIVE_TOOL'; payload: Tool }
    | { type: 'UPDATE_TOOL_SETTINGS'; payload: { tool: Tool; settings: Partial<ToolSettings> } }
    | { type: 'SET_LAST_VISITED'; payload: { tool: Tool; path: string } }
    | { type: 'LOAD_STATE'; payload: ToolState };

// Reducer
function toolReducer(state: ToolState, action: ToolAction): ToolState {
    switch (action.type) {
        case 'SET_ACTIVE_TOOL':
            return {
                ...state,
                activeTool: action.payload,
            };
        case 'UPDATE_TOOL_SETTINGS':
            return {
                ...state,
                toolSettings: {
                    ...state.toolSettings,
                    [action.payload.tool]: {
                        ...state.toolSettings[action.payload.tool],
                        ...action.payload.settings,
                    },
                },
            };
        case 'SET_LAST_VISITED':
            return {
                ...state,
                lastVisited: {
                    ...state.lastVisited,
                    [action.payload.tool]: action.payload.path,
                },
            };
        case 'LOAD_STATE':
            return action.payload;
        default:
            return state;
    }
}

// Create context
const ToolContext = createContext<ToolContextType | undefined>(undefined);

// Provider component
export function ToolProvider({ children }: { children: ReactNode }) {
    const [state, dispatch] = useReducer(toolReducer, initialState);
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const isUpdatingUrl = useRef(false);
    const isInitialized = useRef(false);

    // Load state from localStorage on mount
    useEffect(() => {
        try {
            const savedState = localStorage.getItem('briefly-tool-state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                dispatch({ type: 'LOAD_STATE', payload: parsedState });
            }
        } catch (error) {
            console.warn('Failed to load tool state from localStorage:', error);
        }
        isInitialized.current = true;
    }, []);

    // Save state to localStorage whenever it changes
    useEffect(() => {
        if (!isInitialized.current) return;

        try {
            localStorage.setItem('briefly-tool-state', JSON.stringify(state));
        } catch (error) {
            console.warn('Failed to save tool state to localStorage:', error);
        }
    }, [state]);

    // Sync URL with active tool (only when URL changes, not when state changes)
    useEffect(() => {
        if (!isInitialized.current || isUpdatingUrl.current) return;

        const toolFromUrl = searchParams.get('tool') as Tool;
        if (toolFromUrl && toolFromUrl !== state.activeTool && defaultToolSettings[toolFromUrl]) {
            dispatch({ type: 'SET_ACTIVE_TOOL', payload: toolFromUrl });
        }
    }, [searchParams]); // Remove state.activeTool from dependencies

    // Update URL when active tool changes (only when state changes, not when URL changes)
    useEffect(() => {
        if (!isInitialized.current || isUpdatingUrl.current) return;

        const currentTool = searchParams.get('tool') as Tool;
        if (state.activeTool !== currentTool) {
            isUpdatingUrl.current = true;
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('tool', state.activeTool);
            router.replace(newUrl.pathname + newUrl.search, { scroll: false });

            // Reset the flag after a short delay
            setTimeout(() => {
                isUpdatingUrl.current = false;
            }, 100);
        }
    }, [state.activeTool]); // Remove searchParams from dependencies

    // Update last visited when pathname changes
    useEffect(() => {
        if (!isInitialized.current || !pathname || pathname === '/') return;

        const currentPath = pathname + (searchParams.toString() ? `?${searchParams.toString()}` : '');
        dispatch({
            type: 'SET_LAST_VISITED',
            payload: { tool: state.activeTool, path: currentPath },
        });
    }, [pathname, searchParams, state.activeTool]);

    const setActiveTool = (tool: Tool) => {
        if (state.toolSettings[tool]?.enabled) {
            dispatch({ type: 'SET_ACTIVE_TOOL', payload: tool });
        }
    };

    const updateToolSettings = (tool: Tool, settings: Partial<ToolSettings>) => {
        dispatch({ type: 'UPDATE_TOOL_SETTINGS', payload: { tool, settings } });
    };

    const getToolSettings = (tool: Tool): ToolSettings => {
        return state.toolSettings[tool] || defaultToolSettings[tool];
    };

    const isToolEnabled = (tool: Tool): boolean => {
        return state.toolSettings[tool]?.enabled ?? false;
    };

    const getLastVisited = (tool: Tool): string | null => {
        return state.lastVisited[tool] || null;
    };

    const setLastVisited = (tool: Tool, path: string) => {
        dispatch({ type: 'SET_LAST_VISITED', payload: { tool, path } });
    };

    const contextValue: ToolContextType = {
        state,
        setActiveTool,
        updateToolSettings,
        getToolSettings,
        isToolEnabled,
        getLastVisited,
        setLastVisited,
    };

    return <ToolContext.Provider value={contextValue}>{children}</ToolContext.Provider>;
}

// Hook to use the tool context
export function useToolState() {
    const context = useContext(ToolContext);
    if (context === undefined) {
        throw new Error('useToolState must be used within a ToolProvider');
    }
    return context;
} 