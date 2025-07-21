// Client-side environment variables - SAFE for client-side use
// This file only contains environment variables that are safe to expose to the client.
// For server-side environment variables, use @/lib/env-server instead.

export const env = {
    // Gateway URL (for client-side use)
    GATEWAY_URL: process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001',
} as const;

// Client-side environment validation
export function validateClientEnv() {
    const required = ['NEXT_PUBLIC_GATEWAY_URL'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            console.warn(`Missing optional client environment variable: ${envVar} (using default)`);
        }
    }
} 