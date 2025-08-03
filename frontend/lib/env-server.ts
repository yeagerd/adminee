// Server-side environment variables - DO NOT import in client-side code
// This file should only be used in server components, API routes, or other server-side contexts.

export const serverEnv = {
    // NextAuth configuration
    NEXTAUTH_URL: process.env.NEXTAUTH_URL!,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET!,

    // User Service (only for login flow)
    USER_SERVICE_URL: process.env.USER_SERVICE_URL!,
    API_FRONTEND_USER_KEY: process.env.API_FRONTEND_USER_KEY!,

    // OAuth configuration
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID!,
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET!,
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID!,
} as const;

// Validation functions for server-side environment variables
export function validateServerEnv() {
    const requiredEnvVars = [
        'NEXTAUTH_URL',
        'NEXTAUTH_SECRET',
        'USER_SERVICE_URL',
        'API_FRONTEND_USER_KEY',
        'AZURE_AD_CLIENT_ID',
        'AZURE_AD_CLIENT_SECRET',
        'AZURE_AD_TENANT_ID',
    ] as const;

    for (const envVar of requiredEnvVars) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required server environment variable: ${envVar}`);
        }
    }
}

export function validateNextAuthEnv() {
    const required = ['NEXTAUTH_URL', 'NEXTAUTH_SECRET'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
}

export function validateOAuthEnv() {
    const required = ['AZURE_AD_CLIENT_ID', 'AZURE_AD_CLIENT_SECRET', 'AZURE_AD_TENANT_ID'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
}

