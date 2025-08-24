/* 
 * Navigation types for the frontend application.
 */

export type Tool = 'email' | 'calendar' | 'contacts' | 'meetings' | 'shipments' | 'drafts' | 'documents' | 'tasks' | 'packages' | 'research' | 'pulse' | 'insights' | 'bookings';

export type MeetingSubView = 'list' | 'create' | 'edit' | 'view' | 'new';

export interface NavigationItem {
  id: string;
  label: string;
  title: string;
  href: string;
  icon?: any;
  children?: NavigationItem[];
  enabled: boolean;
}

export interface ToolContextType {
  currentTool: Tool | null;
  setCurrentTool: (tool: Tool | null) => void;
  state: ToolState;
  setActiveTool: (tool: Tool | null) => void;
  updateToolSettings: (tool: Tool, settings: Partial<ToolSettings>) => void;
  getToolSettings: (tool: Tool) => ToolSettings;
  isToolEnabled: (tool: Tool) => boolean;
  getLastVisited: (tool: Tool) => string | null;
  setLastVisited: (tool: Tool, path: string) => void;
  setMeetingSubView: (subView: MeetingSubView) => void;
  getMeetingSubView: () => MeetingSubView | null;
  getMeetingPollId: () => string | null;
  goBackToPreviousMeetingView: () => void;
}

export interface ToolSettings {
  enabled: boolean;
  [key: string]: any;
}

export interface ToolState {
  currentTool: Tool | null;
  activeTool: Tool | null;
  settings: Record<Tool, ToolSettings>;
  toolSettings: Record<Tool, ToolSettings>;
  lastVisited: Record<Tool, string | null>;
  visitTimestamps: Record<Tool, string>;
  meetingSubView: MeetingSubView | null;
  meetingPollId: string | null;
  previousMeetingSubView: MeetingSubView | null;
  previousMeetingPollId: string | null;
}
