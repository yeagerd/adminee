import type { NextAuthOptions } from 'next-auth';
import NextAuth from 'next-auth';
import AzureADProvider from 'next-auth/providers/azure-ad';
import GoogleProvider from 'next-auth/providers/google';

const authOptions: NextAuthOptions = {
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
        AzureADProvider({
            clientId: process.env.AZURE_AD_CLIENT_ID!,
            clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
            tenantId: process.env.AZURE_AD_TENANT_ID || 'common',
            authorization: {
                params: {
                    scope: 'openid email profile',
                },
            },
        }),
    ],
    callbacks: {
        async signIn({ user, account, profile }) {
            // Send webhook to create/update user in our user service
            try {
                const webhookUrl = `${process.env.USER_SERVICE_URL}/users/`;

                const userData = {
                    external_auth_id: account?.providerAccountId || user.id,
                    auth_provider: account?.provider === 'azure-ad' ? 'microsoft' : account?.provider,
                    email: user.email!,
                    first_name: user.name?.split(' ')[0] || '',
                    last_name: user.name?.split(' ').slice(1).join(' ') || '',
                    profile_image_url: user.image || null,
                };

                const response = await fetch(webhookUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': process.env.USER_SERVICE_API_KEY || '',
                    },
                    body: JSON.stringify(userData),
                });

                if (!response.ok) {
                    console.error('Failed to create/update user in user service:', response.statusText);
                    // Still allow sign in even if webhook fails
                }
            } catch (error) {
                console.error('Error sending user creation webhook:', error);
                // Still allow sign in even if webhook fails
            }

            return true;
        },
        async jwt({ token, account, user }) {
            // Store provider information in JWT
            if (account) {
                token.provider = account.provider === 'azure-ad' ? 'microsoft' : account.provider;
                token.providerUserId = account.providerAccountId;
            }
            return token;
        },
        async session({ session, token }) {
            // Include provider information in session
            if (token) {
                session.provider = token.provider as string;
                session.providerUserId = token.providerUserId as string;
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

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
