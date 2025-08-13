import { Tool } from '@/types/navigation';

// Tool route mapping
export const TOOL_ROUTES: Record<Tool, string> = {
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
};

// Tool display names
export const TOOL_NAMES: Record<Tool, string> = {
    calendar: 'Calendar',
    email: 'Email',
    contacts: 'Contacts',
    documents: 'Documents',
    tasks: 'Tasks',
    packages: 'Package Tracker',
    research: 'Research',
    pulse: 'Pulse',
    insights: 'Insights',
    drafts: 'Drafts',
    meetings: 'Meetings',
};

// Tool descriptions
export const TOOL_DESCRIPTIONS: Record<Tool, string> = {
    calendar: 'View and manage your calendar events',
    email: 'Read and send emails',
    contacts: 'View and manage your contacts',
    documents: 'Browse and edit documents',
    tasks: 'Track your tasks and todos',
    packages: 'Track your packages',
    research: 'AI-powered research assistant',
    pulse: 'Industry news and trends',
    insights: 'Analytics and insights',
    drafts: 'View and manage your drafts',
    meetings: 'View and manage your meetings',
};

// Get tool from URL
export function getToolFromUrl(url: string): Tool | null {
    try {
        const urlObj = new URL(url, window.location.origin);
        const tool = urlObj.searchParams.get('tool') as Tool;
        return tool && TOOL_ROUTES[tool] ? tool : null;
    } catch {
        return null;
    }
}

// Get URL for tool
export function getUrlForTool(tool: Tool, baseUrl?: string): string {
    const base = baseUrl || window.location.origin;
    return `${base}${TOOL_ROUTES[tool]}`;
}

// Update URL with tool parameter
export function updateUrlWithTool(currentUrl: string, tool: Tool): string {
    try {
        const url = new URL(currentUrl, window.location.origin);
        url.searchParams.set('tool', tool);
        return url.pathname + url.search;
    } catch {
        return TOOL_ROUTES[tool];
    }
}

// Remove tool parameter from URL
export function removeToolFromUrl(url: string): string {
    try {
        const urlObj = new URL(url, window.location.origin);
        urlObj.searchParams.delete('tool');
        return urlObj.pathname + urlObj.search;
    } catch {
        return url;
    }
}

// Get tool from pathname (for direct navigation)
export function getToolFromPathname(pathname: string): Tool | null {
    // Handle direct routes like /calendar, /email, etc.
    const path = pathname.replace(/^\/+/, '').split('?')[0];

    // Map pathname to tool
    const pathToTool: Record<string, Tool> = {
        'calendar': 'calendar',
        'email': 'email',
        'contacts': 'contacts',
        'documents': 'documents',
        'tasks': 'tasks',
        'packages': 'packages',
        'research': 'research',
        'pulse': 'pulse',
        'insights': 'insights',
        'drafts': 'drafts',
        'meetings': 'meetings',
    };

    return pathToTool[path] || null;
}

// Validate tool
export function isValidTool(tool: string): tool is Tool {
    return tool in TOOL_ROUTES;
}

// Get all available tools
export function getAvailableTools(): Tool[] {
    return Object.keys(TOOL_ROUTES) as Tool[];
}

// Get tool icon name (for dynamic imports)
export function getToolIconName(tool: Tool): string {
    const iconMap: Record<Tool, string> = {
        calendar: 'Calendar',
        email: 'Mail',
        contacts: 'Users',
        documents: 'FileText',
        tasks: 'ListChecks',
        packages: 'Package',
        research: 'BookOpen',
        pulse: 'TrendingUp',
        insights: 'BarChart3',
        drafts: 'Copy',
        meetings: 'Calendar',
    };
    return iconMap[tool];
}

// Get tool color (for theming)
export function getToolColor(tool: Tool): string {
    const colorMap: Record<Tool, string> = {
        calendar: 'blue',
        email: 'green',
        contacts: 'emerald',
        documents: 'purple',
        tasks: 'orange',
        packages: 'red',
        research: 'indigo',
        pulse: 'pink',
        insights: 'teal',
        drafts: 'gray',
        meetings: 'blue',
    };
    return colorMap[tool];
}

// Get tool badge (for "Soon" features)
export function getToolBadge(tool: Tool): string | null {
    const badgeMap: Record<Tool, string | null> = {
        calendar: null,
        email: null,
        contacts: null,
        documents: null,
        tasks: null,
        packages: null,
        research: null,
        pulse: null,
        insights: null,
        drafts: null,
        meetings: null,
    };
    return badgeMap[tool];
}

// Check if tool is available (not "Soon")
export function isToolAvailable(tool: Tool): boolean {
    return getToolBadge(tool) === null;
} 