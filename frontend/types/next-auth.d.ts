import 'next-auth';
import { DefaultSession } from 'next-auth';

declare module 'next-auth' {
    interface Session {
        provider?: string;
        providerUserId?: string;
        user: {
            id: string;
        } & DefaultSession['user'];
    }

    interface User {
        // This is our internal user id
        id: string;
    }

    interface JWT {
        provider?: string;
        providerUserId?: string;
        internalUserId?: string;
    }
} 