import jwt from 'jsonwebtoken';
import { NextAuthOptions } from 'next-auth';
import AzureADProvider from 'next-auth/providers/azure-ad';
import GoogleProvider from 'next-auth/providers/google';

// Environment validation
function validateEnvironment() {
    const required = [
        'NEXTAUTH_SECRET',
        'USER_SERVICE_URL',
        'API_FRONTEND_USER_KEY'
    ];

    for (const var_name of required) {
        if (!process.env[var_name]) {
            throw new Error(`${var_name} environment variable is required`);
        }
    }
}

// Validate environment on module load
validateEnvironment();

export const authOptions: NextAuthOptions = {
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID!,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
            authorization: {
                params: {
                    scope: 'openid email profile',
                    access_type: 'offline',
                    prompt: 'consent',
                },
            },
        }),
        // Don't pass in process.env.AZURE_AD_TENANT_ID; it restricts users to those in the tenant
        AzureADProvider({
            clientId: process.env.AZURE_AD_CLIENT_ID!,
            clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
            tenantId: 'common',
            authorization: {
                params: {
                    scope: 'openid email profile',
                },
            },
        }),
    ],
    callbacks: {
        async signIn({ user, account }) {
            // After OAuth login, fetch or create the user in our user service and get the canonical user id
            const provider = account?.provider === 'azure-ad' ? 'microsoft' : account?.provider;
            const email = user.email!;
            const external_auth_id = account?.providerAccountId || user.id;

            // Required environment variables - fail fast if missing
            const userServiceBase = process.env.USER_SERVICE_URL;
            const apiKey = process.env.API_FRONTEND_USER_KEY;

            if (!userServiceBase) {
                throw new Error('USER_SERVICE_URL environment variable is required');
            }
            if (!apiKey) {
                throw new Error('API_FRONTEND_USER_KEY environment variable is required');
            }
            if (!provider) {
                throw new Error('OAuth provider is required');
            }
            if (!email) {
                throw new Error('User email is required');
            }

            // Debug logging
            console.log('BFF Debug - Environment variables:', {
                userServiceBase,
                hasApiKey: !!apiKey,
                provider,
                email
            });

            try {
                // 1. Try to GET user by email and provider
                let backendUser = null;
                const getUrl = `${userServiceBase}/users/id?email=${encodeURIComponent(email)}&provider=${encodeURIComponent(provider)}`;
                console.log('BFF Debug - GET URL:', getUrl);

                const getRes = await fetch(getUrl, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': apiKey,
                    },
                });

                console.log('BFF Debug - GET response:', getRes.status);

                if (getRes.ok) {
                    backendUser = await getRes.json();
                    console.log('BFF Debug - Found user:', { id: backendUser.id, email: backendUser.email });
                } else if (getRes.status === 404) {
                    // 2. If not found, POST to create user
                    const postUrl = `${userServiceBase}/users/`;
                    const userData = {
                        external_auth_id,
                        auth_provider: provider,
                        email,
                        first_name: user.name?.split(' ')[0] || '',
                        last_name: user.name?.split(' ').slice(1).join(' ') || '',
                        profile_image_url: user.image || null,
                    };
                    console.log('BFF Debug - Creating user:', userData);

                    const postRes = await fetch(postUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey,
                        },
                        body: JSON.stringify(userData),
                    });

                    console.log('BFF Debug - POST response:', postRes.status);

                    if (postRes.ok) {
                        backendUser = await postRes.json();
                        console.log('BFF Debug - Created user:', { id: backendUser.id, email: backendUser.email });
                    } else {
                        const errorText = await postRes.text();
                        throw new Error(`Failed to create user in user service: ${postRes.status} ${errorText}`);
                    }
                } else {
                    const errorText = await getRes.text();
                    throw new Error(`Failed to fetch user from user service: ${getRes.status} ${errorText}`);
                }

                // 3. Attach external auth ID to user object for session/jwt
                if (!backendUser || !backendUser.external_auth_id) {
                    throw new Error('User service did not return a valid user with external_auth_id');
                }

                user.id = backendUser.external_auth_id;
                console.log('BFF Debug - Set user.id to:', user.id);

            } catch (error) {
                console.error('Error in user-service user lookup/creation:', error);
                // No fallbacks - let the sign-in fail if we can't get the canonical user ID
                throw error;
            }

            return true;
        },
        async jwt({ token, account, user }) {
            // Store provider information and internal user ID in JWT
            if (account) {
                token.provider = account.provider === 'azure-ad' ? 'microsoft' : account.provider;
                token.providerUserId = account.providerAccountId;
            }
            if (user) {
                token.internalUserId = user.id;
            }
            return token;
        },
        async session({ session, token }) {
            // Include provider information and internal user ID in session
            if (token) {
                session.provider = token.provider as string;
                session.providerUserId = token.providerUserId as string;
                if (session.user) {
                    session.user.id = token.internalUserId as string;
                }

                // Create a custom JWT token for backend authentication
                if (token.internalUserId) {
                    const customToken = jwt.sign(
                        {
                            sub: String(token.internalUserId), // Ensure it's a string
                            iss: 'nextauth-frontend',
                            aud: 'briefly-backend',
                            email: session.user?.email,
                            iat: Math.floor(Date.now() / 1000),
                            exp: Math.floor(Date.now() / 1000) + (60 * 60), // 1 hour
                        },
                        process.env.NEXTAUTH_SECRET!,
                        { algorithm: 'HS256' }
                    );
                    session.accessToken = customToken;
                }
            }
            return session;
        },
    },
    pages: {
        signIn: '/login',
        error: '/auth/error',
    },
    session: {
        strategy: 'jwt',
    },
    debug: process.env.NODE_ENV === 'development',
};

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