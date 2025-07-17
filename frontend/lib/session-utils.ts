// Client-side session utility functions
// These functions work with NextAuth session objects and don't require server-side environment variables

// Helper function to get user ID from session for API calls
export function getUserId(session: unknown): string | null {
    const sessionObj = session as { user?: { id?: string } };
    return sessionObj?.user?.id || null;
}

// Helper function to get provider from session
export function getProvider(session: unknown): string | null {
    const sessionObj = session as { provider?: string };
    return sessionObj?.provider || null;
}

// Helper function to get user email from session
export function getUserEmail(session: unknown): string | null {
    const sessionObj = session as { user?: { email?: string } };
    return sessionObj?.user?.email || null;
}

// Helper function to get user name from session
export function getUserName(session: unknown): string | null {
    const sessionObj = session as { user?: { name?: string } };
    return sessionObj?.user?.name || null;
}

// Helper function to check if user is authenticated
export function isAuthenticated(session: unknown): boolean {
    return !!session && !!(session as any)?.user;
} 