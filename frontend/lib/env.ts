// Environment variable validation for frontend
export const env = {
    // NextAuth configuration
    NEXTAUTH_URL: process.env.NEXTAUTH_URL!,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET!,

    // Gateway URL (for client-side use)
    GATEWAY_URL: process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001',

    // Service URLs (for server-side use)
    CHAT_SERVICE_URL: process.env.CHAT_SERVICE_URL || 'http://localhost:8001',
    USER_SERVICE_URL: process.env.USER_SERVICE_URL || 'http://localhost:8000',
    OFFICE_SERVICE_URL: process.env.OFFICE_SERVICE_URL || 'http://localhost:8002',

    // API Keys for service-to-service communication
    API_FRONTEND_CHAT_KEY: process.env.API_FRONTEND_CHAT_KEY!,
    API_FRONTEND_USER_KEY: process.env.API_FRONTEND_USER_KEY!,
    API_FRONTEND_OFFICE_KEY: process.env.API_FRONTEND_OFFICE_KEY!,

    // OAuth configuration
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID!,
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET!,
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID!,
} as const;

// Validation functions for specific use cases
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

// Validate all environment variables (for startup validation)
export function validateAllEnv() {
    const requiredEnvVars = [
        'NEXTAUTH_URL',
        'NEXTAUTH_SECRET',
        'API_FRONTEND_CHAT_KEY',
        'API_FRONTEND_USER_KEY',
        'API_FRONTEND_OFFICE_KEY',
        'AZURE_AD_CLIENT_ID',
        'AZURE_AD_CLIENT_SECRET',
        'AZURE_AD_TENANT_ID',
    ] as const;

    for (const envVar of requiredEnvVars) {
        if (!process.env[envVar]) {
            throw new Error(`Missing required environment variable: ${envVar}`);
        }
    }
} 