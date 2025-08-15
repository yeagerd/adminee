'use client';

import { MeetingSubView, Tool, ToolContextType, ToolSettings, ToolState } from '@/types/navigation';
import { usePathname, useSearchParams } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useMemo, useReducer, useRef } from 'react';

// Initial tool settings
const defaultToolSettings: Record<Tool, ToolSettings> = {
    calendar: { id: 'calendar', enabled: true, preferences: { view: 'month', showWeekends: true } },
    email: { id: 'email', enabled: true, preferences: { view: 'inbox', sortBy: 'date' } },
    contacts: { id: 'contacts', enabled: true, preferences: {} },
    documents: { id: 'documents', enabled: false, preferences: { view: 'list' } },
    tasks: { id: 'tasks', enabled: false, preferences: { view: 'list' } },
    packages: { id: 'packages', enabled: true, preferences: {} },
    research: { id: 'research', enabled: false, preferences: {} },
    pulse: { id: 'pulse', enabled: false, preferences: {} },
    insights: { id: 'insights', enabled: false, preferences: {} },
    drafts: { id: 'drafts', enabled: true, preferences: {} },
    meetings: { id: 'meetings', enabled: true, preferences: {} },
    bookings: { id: 'bookings', enabled: true, preferences: {} },
};

// Initial state
const initialState: ToolState = {
    activeTool: 'calendar',
    toolSettings: defaultToolSettings,
    lastVisited: {
        calendar: '/dashboard?tool=calendar',
        email: '/dashboard?tool=email',
        contacts: '/dashboard?tool=contacts',
        documents: '/dashboard?tool=documents',
        tasks: '/dashboard?tool=tasks',
        packages: '/dashboard?tool=packages',
        research: '/dashboard?tool=research',
        pulse: '/dashboard?tool=pulse',
        insights: '/dashboard?tool=insights',
        drafts: '/dashboard?tool=drafts',
        meetings: '/dashboard?tool=meetings',
        bookings: '/dashboard?tool=bookings',
    },
    visitTimestamps: {
        calendar: 0,
        email: 0,
        contacts: 0,
        documents: 0,
        tasks: 0,
        packages: 0,
        research: 0,
        pulse: 0,
        insights: 0,
        drafts: 0,
        meetings: 0,
        bookings: 0,
    },
    meetingSubView: 'list',
    meetingPollId: null,
    previousMeetingSubView: null,
    previousMeetingPollId: null,
};

// Action types
type ToolAction =
    | { type: 'SET_ACTIVE_TOOL'; payload: Tool }
    | { type: 'UPDATE_TOOL_SETTINGS'; payload: { tool: Tool; settings: Partial<ToolSettings> } }
    | { type: 'SET_LAST_VISITED'; payload: { tool: Tool; path: string } }
    | { type: 'SET_VISIT_TIMESTAMP'; payload: { tool: Tool; timestamp: number } }
    | { type: 'LOAD_STATE'; payload: ToolState }
    | { type: 'SET_MEETING_SUB_VIEW'; payload: { subView: MeetingSubView; pollId?: string } }
    | { type: 'SET_PREVIOUS_MEETING_VIEW'; payload: { subView: MeetingSubView; pollId?: string } };

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
        case 'SET_MEETING_SUB_VIEW':
            return {
                ...state,
                meetingSubView: action.payload.subView,
                meetingPollId: action.payload.pollId || null,
            };
        case 'SET_PREVIOUS_MEETING_VIEW':
            return {
                ...state,
                previousMeetingSubView: action.payload.subView,
                previousMeetingPollId: action.payload.pollId || null,
            };
        case 'LOAD_STATE':
            return action.payload;
        default:
            return state;
    }
}

// Utility to merge preferences from saved state into default tool settings
function mergeToolSettingsWithPreferences(defaults: Record<Tool, ToolSettings>, saved: Record<string, { preferences?: Record<string, unknown> }> | undefined): Record<Tool, ToolSettings> {
    const merged: Record<Tool, ToolSettings> = { ...defaults };
    if (saved && typeof saved === 'object') {
        for (const tool of Object.keys(defaults) as Tool[]) {
            if (saved[tool] && saved[tool].preferences) {
                merged[tool] = {
                    ...defaults[tool],
                    preferences: {
                        ...defaults[tool].preferences,
                        ...saved[tool].preferences,
                    },
                };
            }
        }
    }
    return merged;
}

// Create context
const ToolContext = createContext<ToolContextType | undefined>(undefined);

// Provider component
export function ToolProvider({ children }: { children: ReactNode }) {
    const [state, dispatch] = useReducer(toolReducer, initialState);
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const isInitialized = useRef(false);

    // Load user-driven state from localStorage on mount (do NOT persist enabled/disabled)
    useEffect(() => {
        try {
            const savedState = localStorage.getItem('briefly-tool-state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                // Merge preferences only, always use enabled from code
                const mergedToolSettings = mergeToolSettingsWithPreferences(defaultToolSettings, parsedState.toolSettings);
                const mergedState: ToolState = {
                    activeTool: parsedState.activeTool || initialState.activeTool,
                    toolSettings: mergedToolSettings,
                    lastVisited: parsedState.lastVisited || initialState.lastVisited,
                    visitTimestamps: parsedState.visitTimestamps || initialState.visitTimestamps,
                    meetingSubView: parsedState.meetingSubView || initialState.meetingSubView,
                    meetingPollId: parsedState.meetingPollId || initialState.meetingPollId,
                    previousMeetingSubView: parsedState.previousMeetingSubView || initialState.previousMeetingSubView,
                    previousMeetingPollId: parsedState.previousMeetingPollId || initialState.previousMeetingPollId,
                };
                dispatch({ type: 'LOAD_STATE', payload: mergedState });
            }
        } catch (error) {
            console.warn('Failed to load tool state from localStorage:', error);
        }
        isInitialized.current = true;
    }, []);

    // Save only user-driven state to localStorage (do NOT persist enabled/disabled)
    const localStorageDependencies = useMemo(() => [
        state.activeTool,
        JSON.stringify(state.toolSettings),
        JSON.stringify(state.lastVisited),
        JSON.stringify(state.visitTimestamps),
        state.meetingSubView,
        state.meetingPollId,
        state.previousMeetingSubView,
        state.previousMeetingPollId,
    ], [
        state.activeTool,
        state.toolSettings,
        state.lastVisited,
        state.visitTimestamps,
        state.meetingSubView,
        state.meetingPollId,
        state.previousMeetingSubView,
        state.previousMeetingPollId,
    ]);

    useEffect(() => {
        if (!isInitialized.current) return;
        try {
            // Only persist preferences, not enabled/disabled
            const toolSettingsToSave: Record<Tool, { preferences: Record<string, unknown> }> = {} as Record<Tool, { preferences: Record<string, unknown> }>;
            for (const tool of Object.keys(defaultToolSettings) as Tool[]) {
                toolSettingsToSave[tool] = {
                    preferences: state.toolSettings[tool]?.preferences || {},
                };
            }
            const stateToSave = {
                activeTool: state.activeTool,
                toolSettings: toolSettingsToSave,
                lastVisited: state.lastVisited,
                visitTimestamps: state.visitTimestamps,
                meetingSubView: state.meetingSubView,
                meetingPollId: state.meetingPollId,
                previousMeetingSubView: state.previousMeetingSubView,
                previousMeetingPollId: state.previousMeetingPollId,
            };
            localStorage.setItem('briefly-tool-state', JSON.stringify(stateToSave));
        } catch (error) {
            console.warn('Failed to save tool state to localStorage:', error);
        }
    }, localStorageDependencies);

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
            defaultToolSettings[toolFromUrl] &&
            state.toolSettings[toolFromUrl]?.enabled
        ) {
            dispatch({ type: 'SET_ACTIVE_TOOL', payload: toolFromUrl });
            dispatch({ type: 'SET_VISIT_TIMESTAMP', payload: { tool: toolFromUrl, timestamp: Date.now() } });

            // Handle meeting-specific URL parameters
            if (toolFromUrl === 'meetings') {
                const view = searchParams.get('view');
                const id = searchParams.get('id');

                if (view === 'new') {
                    dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView: 'new' } });
                } else if (view === 'edit' && id) {
                    dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView: 'edit', pollId: id } });
                } else if (view === 'poll' && id) {
                    dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView: 'view', pollId: id } });
                } else {
                    // Default to list view
                    dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView: 'list' } });
                }
            }
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

    const setMeetingSubView = (subView: MeetingSubView, pollId?: string) => {
        // If we're navigating to edit, store the current view as previous
        if (subView === 'edit') {
            dispatch({
                type: 'SET_PREVIOUS_MEETING_VIEW',
                payload: {
                    subView: state.meetingSubView,
                    pollId: state.meetingPollId || undefined
                }
            });
        }
        dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView, pollId } });
    };

    const getMeetingSubView = (): MeetingSubView => {
        return state.meetingSubView;
    };

    const getMeetingPollId = (): string | null => {
        return state.meetingPollId;
    };

    const goBackToPreviousMeetingView = () => {
        if (state.previousMeetingSubView) {
            dispatch({
                type: 'SET_MEETING_SUB_VIEW',
                payload: {
                    subView: state.previousMeetingSubView,
                    pollId: state.previousMeetingPollId || undefined
                }
            });
        } else {
            // Fallback to list view if no previous view is stored
            dispatch({ type: 'SET_MEETING_SUB_VIEW', payload: { subView: 'list' } });
        }
    };

    const contextValue: ToolContextType = {
        state,
        setActiveTool,
        updateToolSettings,
        getToolSettings,
        isToolEnabled,
        getLastVisited,
        setLastVisited,
        setMeetingSubView,
        getMeetingSubView,
        getMeetingPollId,
        goBackToPreviousMeetingView,
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