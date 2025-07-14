'use client';

import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { signIn, useSession } from 'next-auth/react';
import { useState } from 'react';

interface OAuthButtonsProps {
    callbackUrl?: string;
    className?: string;
}

export default function OAuthButtons({ callbackUrl = '/dashboard', className }: OAuthButtonsProps) {
    const [isLoading, setIsLoading] = useState<string | null>(null);
    const { data: session } = useSession();

    const handleSignIn = async (provider: 'google' | 'azure-ad') => {
        try {
            setIsLoading(provider);
            await signIn(provider, { callbackUrl });
        } catch (error) {
            console.error('Sign in error:', error);
        } finally {
            setIsLoading(null);
        }
    };

    // If user is already signed in and has a provider, show only that provider
    if (session?.provider) {
        const provider = session.provider === 'microsoft' ? 'azure-ad' : session.provider;

        return (
            <div className={`space-y-3 ${className || ''}`}>
                <Button
                    variant="outline"
                    className="w-full h-12 text-left justify-start"
                    onClick={() => handleSignIn(provider as 'google' | 'azure-ad')}
                    disabled={isLoading !== null}
                >
                    {isLoading === provider ? (
                        <Loader2 className="mr-3 h-4 w-4 animate-spin" />
                    ) : (
                        provider === 'google' ? (
                            <svg className="mr-3 h-4 w-4" viewBox="0 0 24 24">
                                <path
                                    fill="currentColor"
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                />
                                <path
                                    fill="currentColor"
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                />
                                <path
                                    fill="currentColor"
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                />
                                <path
                                    fill="currentColor"
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                />
                            </svg>
                        ) : (
                            <svg className="mr-3 h-4 w-4" viewBox="0 0 24 24">
                                <path
                                    fill="currentColor"
                                    d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4z"
                                />
                                <path fill="#1BA1E2" d="M24 11.4H12.6V0H24v11.4z" />
                            </svg>
                        )
                    )}
                    Continue with {session.provider === 'microsoft' ? 'Microsoft' : 'Google'}
                </Button>
            </div>
        );
    }

    return (
        <div className={`space-y-3 ${className || ''}`}>
            <Button
                variant="outline"
                className="w-full h-12 text-left justify-start"
                onClick={() => handleSignIn('google')}
                disabled={isLoading !== null}
            >
                {isLoading === 'google' ? (
                    <Loader2 className="mr-3 h-4 w-4 animate-spin" />
                ) : (
                    <svg className="mr-3 h-4 w-4" viewBox="0 0 24 24">
                        <path
                            fill="currentColor"
                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        />
                        <path
                            fill="currentColor"
                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        />
                        <path
                            fill="currentColor"
                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        />
                        <path
                            fill="currentColor"
                            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        />
                    </svg>
                )}
                Continue with Google
            </Button>

            <Button
                variant="outline"
                className="w-full h-12 text-left justify-start"
                onClick={() => handleSignIn('azure-ad')}
                disabled={isLoading !== null}
            >
                {isLoading === 'azure-ad' ? (
                    <Loader2 className="mr-3 h-4 w-4 animate-spin" />
                ) : (
                    <svg className="mr-3 h-4 w-4" viewBox="0 0 24 24">
                        <path
                            fill="currentColor"
                            d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4z"
                        />
                        <path fill="#1BA1E2" d="M24 11.4H12.6V0H24v11.4z" />
                    </svg>
                )}
                Continue with Microsoft
            </Button>
        </div>
    );
} 