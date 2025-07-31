// Server-side environment variables - DO NOT import in client-side code
// This file should only be used in server components, API routes, or other server-side contexts.

export const serverEnv = {
    // NextAuth configuration
    NEXTAUTH_URL: process.env.NEXTAUTH_URL!,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET!,

    // Service URLs (for server-side use)
    CHAT_SERVICE_URL: process.env.CHAT_SERVICE_URL!,
    USER_SERVICE_URL: process.env.USER_SERVICE_URL!,
    OFFICE_SERVICE_URL: process.env.OFFICE_SERVICE_URL!,

    // API Keys for service-to-service communication (SERVER-SIDE ONLY)
    API_FRONTEND_CHAT_KEY: process.env.API_FRONTEND_CHAT_KEY!,
    API_FRONTEND_USER_KEY: process.env.API_FRONTEND_USER_KEY!,
    API_FRONTEND_OFFICE_KEY: process.env.API_FRONTEND_OFFICE_KEY!,

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
        'CHAT_SERVICE_URL',
        'USER_SERVICE_URL',
        'OFFICE_SERVICE_URL',
        'API_FRONTEND_CHAT_KEY',
        'API_FRONTEND_USER_KEY',
        'API_FRONTEND_OFFICE_KEY',
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

export function validateChatServiceEnv() {
    const required = ['API_FRONTEND_CHAT_KEY'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
}

export function validateUserServiceEnv() {
    const required = ['API_FRONTEND_USER_KEY'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
}

export function validateOfficeServiceEnv() {
    const required = ['API_FRONTEND_OFFICE_KEY'];
    for (const envVar of required) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
} 