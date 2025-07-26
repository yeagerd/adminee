'use client';

import { useToolState } from '@/contexts/tool-context';
import { Tool, ToolSettings } from '@/types/navigation';
import { useCallback } from 'react';

export function useToolStateUtils() {
    const {
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
    } = useToolState();

    // Get all enabled tools
    const getEnabledTools = useCallback((): Tool[] => {
        return Object.entries(state.toolSettings)
            .filter(([, settings]) => settings.enabled)
            .map(([tool]) => tool as Tool);
    }, [state.toolSettings]);

    // Get all disabled tools
    const getDisabledTools = useCallback((): Tool[] => {
        return Object.entries(state.toolSettings)
            .filter(([, settings]) => !settings.enabled)
            .map(([tool]) => tool as Tool);
    }, [state.toolSettings]);

    // Toggle tool enabled/disabled
    const toggleTool = useCallback((tool: Tool) => {
        const currentSettings = getToolSettings(tool);
        updateToolSettings(tool, { enabled: !currentSettings.enabled });
    }, [getToolSettings, updateToolSettings]);

    // Update specific preference for a tool
    const updateToolPreference = useCallback((tool: Tool, key: string, value: unknown) => {
        const currentSettings = getToolSettings(tool);
        updateToolSettings(tool, {
            preferences: {
                ...currentSettings.preferences,
                [key]: value,
            },
        });
    }, [getToolSettings, updateToolSettings]);

    // Get specific preference for a tool
    const getToolPreference = useCallback((tool: Tool, key: string, defaultValue?: unknown) => {
        const settings = getToolSettings(tool);
        return settings.preferences[key] ?? defaultValue;
    }, [getToolSettings]);

    // Reset tool settings to defaults
    const resetToolSettings = useCallback((tool: Tool) => {
        const defaultSettings: ToolSettings = {
            id: tool,
            enabled: true,
            preferences: {},
        };
        updateToolSettings(tool, defaultSettings);
    }, [updateToolSettings]);

    // Get recently visited tools (ordered by last visit)
    const getRecentlyVisitedTools = useCallback((): Tool[] => {
        const visitedTools = Object.entries(state.lastVisited)
            .filter(([tool, path]) => path && isToolEnabled(tool as Tool))
            .sort(([toolA], [toolB]) => {
                // Sort by actual visit timestamps (most recent first)
                const timestampA = state.visitTimestamps[toolA as Tool] || 0;
                const timestampB = state.visitTimestamps[toolB as Tool] || 0;
                return timestampB - timestampA; // Descending order (most recent first)
            })
            .map(([tool]) => tool as Tool);

        return visitedTools;
    }, [state.lastVisited, state.visitTimestamps, isToolEnabled]);

    // Check if a tool is the currently active one
    const isActiveTool = useCallback((tool: Tool): boolean => {
        return state.activeTool === tool;
    }, [state.activeTool]);

    // Get the next available tool (for keyboard navigation)
    const getNextTool = useCallback((): Tool | null => {
        const enabledTools = getEnabledTools();
        const currentIndex = enabledTools.indexOf(state.activeTool);
        if (currentIndex === -1 || currentIndex === enabledTools.length - 1) {
            return enabledTools[0] || null;
        }
        return enabledTools[currentIndex + 1];
    }, [state.activeTool, getEnabledTools]);

    // Get the previous available tool (for keyboard navigation)
    const getPreviousTool = useCallback((): Tool | null => {
        const enabledTools = getEnabledTools();
        const currentIndex = enabledTools.indexOf(state.activeTool);
        if (currentIndex === -1 || currentIndex === 0) {
            return enabledTools[enabledTools.length - 1] || null;
        }
        return enabledTools[currentIndex - 1];
    }, [state.activeTool, getEnabledTools]);

    return {
        // Core state
        activeTool: state.activeTool,
        toolSettings: state.toolSettings,
        lastVisited: state.lastVisited,

        // Core actions
        setActiveTool,
        updateToolSettings,
        getToolSettings,
        isToolEnabled,
        getLastVisited,
        setLastVisited,

        // Meeting-specific actions
        setMeetingSubView,
        getMeetingSubView,
        getMeetingPollId,
        goBackToPreviousMeetingView,

        // Utility functions
        getEnabledTools,
        getDisabledTools,
        toggleTool,
        updateToolPreference,
        getToolPreference,
        resetToolSettings,
        getRecentlyVisitedTools,
        isActiveTool,
        getNextTool,
        getPreviousTool,
    };
} 