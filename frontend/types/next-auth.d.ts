import 'next-auth';

declare module 'next-auth' {
    interface Session {
        provider?: string;
        providerUserId?: string;
    }

    interface JWT {
        provider?: string;
        providerUserId?: string;
    }
} 