export type Tool =
    | 'calendar'
    | 'email'
    | 'documents'
    | 'tasks'
    | 'drafts'
    | 'packages'
    | 'research'
    | 'pulse'
    | 'insights'
    | 'meetings';

export type MeetingSubView = 'list' | 'view' | 'edit' | 'new';

export interface ToolSettings {
    id: Tool;
    enabled: boolean;
    preferences: Record<string, unknown>;
}

export interface ToolState {
    activeTool: Tool;
    toolSettings: Record<Tool, ToolSettings>;
    lastVisited: Record<Tool, string>; // URL paths
    visitTimestamps: Record<Tool, number>; // Timestamps for recency sorting
    // Sub-views for specific tools
    meetingSubView: MeetingSubView;
    meetingPollId: string | null; // For view/edit specific polls
    previousMeetingSubView: MeetingSubView | null; // Track previous subview for navigation
    previousMeetingPollId: string | null; // Track previous poll ID for navigation
}

export interface ToolContextType {
    state: ToolState;
    setActiveTool: (tool: Tool) => void;
    updateToolSettings: (tool: Tool, settings: Partial<ToolSettings>) => void;
    getToolSettings: (tool: Tool) => ToolSettings;
    isToolEnabled: (tool: Tool) => boolean;
    getLastVisited: (tool: Tool) => string | null;
    setLastVisited: (tool: Tool, path: string) => void;
    // Meeting-specific actions
    setMeetingSubView: (subView: MeetingSubView, pollId?: string) => void;
    getMeetingSubView: () => MeetingSubView;
    getMeetingPollId: () => string | null;
    // Navigation back to previous meeting subview
    goBackToPreviousMeetingView: () => void;
}

export interface NavigationItem {
    id: Tool;
    title: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
    path: string;
    enabled: boolean;
}

export type NavigationTool =
    | 'calendar'
    | 'email'
    | 'documents'
    | 'tasks'
    | 'drafts';

export const NAVIGATION_TOOLS: Array<NavigationTool> = [
    'calendar',
    'email',
    'documents',
    'tasks',
    'drafts',
]; 