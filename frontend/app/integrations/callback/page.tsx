'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import { ArrowLeft, CheckCircle, Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

function OAuthCallbackContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('');
    const [provider, setProvider] = useState('');

    useEffect(() => {
        const handleOAuthCallback = async () => {
            const code = searchParams.get('code');
            const state = searchParams.get('state');
            const error = searchParams.get('error');
            const providerParam = searchParams.get('provider');

            if (error) {
                setStatus('error');
                setMessage(`OAuth error: ${error}`);
                return;
            }

            if (!code || !state) {
                setStatus('error');
                setMessage('Missing OAuth parameters');
                return;
            }

            if (!providerParam) {
                setStatus('error');
                setMessage('Missing provider information');
                return;
            }

            setProvider(providerParam);

            try {
                await apiClient.completeOAuthFlow(providerParam, code, state);
                setStatus('success');
                setMessage(`Successfully connected ${providerParam}!`);

                // Redirect to integrations page after a short delay
                setTimeout(() => {
                    router.push('/integrations');
                }, 2000);
            } catch (error: unknown) {
                console.error('OAuth completion failed:', error);
                setStatus('error');
                setMessage(`Failed to complete OAuth flow: ${error instanceof Error ? error.message : 'Unknown error'}`);
            }
        };

        handleOAuthCallback();
    }, [searchParams, router]);

    const getStatusIcon = () => {
        switch (status) {
            case 'loading':
                return <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />;
            case 'success':
                return <CheckCircle className="h-12 w-12 text-green-600" />;
            case 'error':
                return <XCircle className="h-12 w-12 text-red-600" />;
        }
    };

    const getStatusColor = () => {
        switch (status) {
            case 'loading':
                return 'border-blue-200 bg-blue-50';
            case 'success':
                return 'border-green-200 bg-green-50';
            case 'error':
                return 'border-red-200 bg-red-50';
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <Card className={`w-full max-w-md ${getStatusColor()}`}>
                <CardHeader className="text-center">
                    <div className="flex justify-center mb-4">
                        {getStatusIcon()}
                    </div>
                    <CardTitle className="text-xl">
                        {status === 'loading' && 'Completing OAuth...'}
                        {status === 'success' && 'Integration Successful!'}
                        {status === 'error' && 'Integration Failed'}
                    </CardTitle>
                    <CardDescription>
                        {status === 'loading' && 'Please wait while we complete your integration'}
                        {status === 'success' && `${provider} has been successfully connected to your account`}
                        {status === 'error' && 'There was a problem connecting your account'}
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="text-center">
                        <p className="text-sm text-gray-600">{message}</p>
                    </div>

                    {status !== 'loading' && (
                        <div className="space-y-2">
                            {status === 'success' ? (
                                <>
                                    <Button asChild className="w-full">
                                        <Link href="/integrations">
                                            View Integrations
                                        </Link>
                                    </Button>
                                    <Button variant="outline" asChild className="w-full">
                                        <Link href="/dashboard">
                                            Go to Dashboard
                                        </Link>
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button asChild className="w-full">
                                        <Link href="/integrations">
                                            <ArrowLeft className="h-4 w-4 mr-2" />
                                            Back to Integrations
                                        </Link>
                                    </Button>
                                    <Button variant="outline" asChild className="w-full">
                                        <Link href="/profile">
                                            View Profile
                                        </Link>
                                    </Button>
                                </>
                            )}
                        </div>
                    )}

                    {status === 'success' && (
                        <div className="text-center text-xs text-gray-500">
                            Redirecting to integrations page in a moment...
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md">
                    <CardHeader className="text-center">
                        <div className="flex justify-center mb-4">
                            <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />
                        </div>
                        <CardTitle className="text-xl">Loading...</CardTitle>
                        <CardDescription>Processing your OAuth callback</CardDescription>
                    </CardHeader>
                </Card>
            </div>
        }>
            <OAuthCallbackContent />
        </Suspense>
    );
}