export interface CalendarError {
    type: 'network' | 'auth' | 'api' | 'provider' | 'validation' | 'unknown';
    message: string;
    userFriendlyMessage: string;
    retryable: boolean;
    provider?: string;
    statusCode?: number;
}

export class CalendarErrorHandler {
    static createError(error: unknown, context?: { provider?: string; statusCode?: number }): CalendarError {
        const errorMessage = error instanceof Error ? error.message : String(error);
        const statusCode = context?.statusCode;
        const provider = context?.provider;

        // Network errors
        if (errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Failed to fetch')) {
            return {
                type: 'network',
                message: errorMessage,
                userFriendlyMessage: 'Unable to connect to calendar service. Please check your internet connection.',
                retryable: true,
                provider,
                statusCode
            };
        }

        // Authentication errors
        if (errorMessage.includes('401') || errorMessage.includes('unauthorized') || errorMessage.includes('token')) {
            return {
                type: 'auth',
                message: errorMessage,
                userFriendlyMessage: 'Your calendar connection has expired. Please reconnect your account.',
                retryable: false,
                provider,
                statusCode
            };
        }

        // Provider-specific errors
        if (errorMessage.includes('google') || errorMessage.includes('microsoft')) {
            return {
                type: 'provider',
                message: errorMessage,
                userFriendlyMessage: `Unable to access ${provider || 'calendar'} data. Please check your connection settings.`,
                retryable: true,
                provider,
                statusCode
            };
        }

        // API errors
        if (errorMessage.includes('500') || errorMessage.includes('502') || errorMessage.includes('503')) {
            return {
                type: 'api',
                message: errorMessage,
                userFriendlyMessage: 'Calendar service is temporarily unavailable. Please try again later.',
                retryable: true,
                provider,
                statusCode
            };
        }

        // Validation errors
        if (errorMessage.includes('validation') || errorMessage.includes('invalid')) {
            return {
                type: 'validation',
                message: errorMessage,
                userFriendlyMessage: 'Invalid request. Please check your settings and try again.',
                retryable: false,
                provider,
                statusCode
            };
        }

        // Unknown errors
        return {
            type: 'unknown',
            message: errorMessage,
            userFriendlyMessage: 'An unexpected error occurred. Please try again.',
            retryable: true,
            provider,
            statusCode
        };
    }

    static shouldRetry(error: CalendarError, retryCount: number): boolean {
        if (!error.retryable) return false;
        if (retryCount >= 3) return false;

        // Don't retry auth errors
        if (error.type === 'auth') return false;

        // Don't retry validation errors
        if (error.type === 'validation') return false;

        return true;
    }

    static getRetryDelay(retryCount: number): number {
        // Exponential backoff: 1s, 2s, 4s
        return Math.min(1000 * Math.pow(2, retryCount), 10000);
    }

    static getErrorIcon(error: CalendarError): string {
        switch (error.type) {
            case 'network':
                return '🌐';
            case 'auth':
                return '🔐';
            case 'provider':
                return '📅';
            case 'api':
                return '⚙️';
            case 'validation':
                return '⚠️';
            default:
                return '❌';
        }
    }

    static getErrorColor(error: CalendarError): 'destructive' | 'default' | 'secondary' {
        switch (error.type) {
            case 'auth':
            case 'validation':
                return 'destructive';
            case 'network':
            case 'api':
                return 'default';
            default:
                return 'secondary';
        }
    }

    static formatProviderError(providerErrors: Record<string, string>): string {
        const errors = Object.entries(providerErrors);
        if (errors.length === 0) return '';

        if (errors.length === 1) {
            const [provider, error] = errors[0];
            return `${provider.charAt(0).toUpperCase() + provider.slice(1)}: ${error}`;
        }

        return `Multiple providers had issues: ${errors.map(([provider]) => provider).join(', ')}`;
    }
} 