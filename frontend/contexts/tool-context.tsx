'use client';

import { Tool, ToolContextType, ToolSettings, ToolState } from '@/types/navigation';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useReducer, useRef } from 'react';

// Initial tool settings
const defaultToolSettings: Record<Tool, ToolSettings> = {
    calendar: { id: 'calendar', enabled: true, preferences: { view: 'month', showWeekends: true } },
    email: { id: 'email', enabled: true, preferences: { view: 'inbox', sortBy: 'date' } },
    documents: { id: 'documents', enabled: true, preferences: { view: 'list' } },
    tasks: { id: 'tasks', enabled: true, preferences: { view: 'list' } },
    packages: { id: 'packages', enabled: true, preferences: {} },
    research: { id: 'research', enabled: true, preferences: {} },
    pulse: { id: 'pulse', enabled: true, preferences: {} },
    insights: { id: 'insights', enabled: false, preferences: {} },
    drafts: { id: 'drafts', enabled: true, preferences: {} },
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
        drafts: '/dashboard?tool=drafts',
    },
    visitTimestamps: {
        calendar: 0,
        email: 0,
        documents: 0,
        tasks: 0,
        packages: 0,
        research: 0,
        pulse: 0,
        insights: 0,
        drafts: 0,
    },
};

// Action types
type ToolAction =
    | { type: 'SET_ACTIVE_TOOL'; payload: Tool }
    | { type: 'UPDATE_TOOL_SETTINGS'; payload: { tool: Tool; settings: Partial<ToolSettings> } }
    | { type: 'SET_LAST_VISITED'; payload: { tool: Tool; path: string } }
    | { type: 'SET_VISIT_TIMESTAMP'; payload: { tool: Tool; timestamp: number } }
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
        case 'SET_VISIT_TIMESTAMP':
            return {
                ...state,
                visitTimestamps: {
                    ...state.visitTimestamps,
                    [action.payload.tool]: action.payload.timestamp,
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

    // ---
    // IMPORTANT: Avoiding the double-navigate bug and ensuring visit tracking
    // This effect syncs the tool state from the URL. The URL is the single source of truth for tool navigation.
    // DO NOT add state.activeTool or state.toolSettings to the dependency array, as that will cause this effect
    // to run on state changes, creating a feedback loop and double navigation (especially on deep links).
    // Only depend on searchParams so this runs only when the URL changes.
    // We also update the visit timestamp here, since navigation is now URL-driven.
    // ---
    useEffect(() => {
        if (!isInitialized.current) return;
        const toolFromUrl = searchParams.get('tool') as Tool;
        if (
            toolFromUrl &&
            toolFromUrl !== state.activeTool &&
            defaultToolSettings[toolFromUrl] &&
            state.toolSettings[toolFromUrl]?.enabled
        ) {
            dispatch({ type: 'SET_ACTIVE_TOOL', payload: toolFromUrl });
            dispatch({ type: 'SET_VISIT_TIMESTAMP', payload: { tool: toolFromUrl, timestamp: Date.now() } });
        }
    }, [searchParams]);

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
            // Update visit timestamp
            dispatch({ type: 'SET_VISIT_TIMESTAMP', payload: { tool, timestamp: Date.now() } });
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