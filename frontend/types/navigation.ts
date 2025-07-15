export type Tool = "calendar" | "email" | "documents" | "tasks" | "packages" | "research" | "pulse" | "insights";

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
}

export interface ToolContextType {
    state: ToolState;
    setActiveTool: (tool: Tool) => void;
    updateToolSettings: (tool: Tool, settings: Partial<ToolSettings>) => void;
    getToolSettings: (tool: Tool) => ToolSettings;
    isToolEnabled: (tool: Tool) => boolean;
    getLastVisited: (tool: Tool) => string | null;
    setLastVisited: (tool: Tool, path: string) => void;
}

export interface NavigationItem {
    id: Tool;
    title: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
    path: string;
    enabled: boolean;
} 