'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { gatewayClient } from '@/lib/gateway-client';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

function IntegrationCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [error, setError] = useState<string | null>(null);
    const [provider, setProvider] = useState<string | null>(null);

    useEffect(() => {
        const handleCallback = async () => {
            try {
                // Get OAuth parameters from URL
                const code = searchParams.get('code');
                const state = searchParams.get('state');
                const error = searchParams.get('error');
                const errorDescription = searchParams.get('error_description');

                // Determine provider from the callback URL
                const pathname = window.location.pathname;
                let detectedProvider = 'microsoft'; // default
                if (pathname.includes('google')) {
                    detectedProvider = 'google';
                } else if (pathname.includes('azure-ad') || pathname.includes('microsoft')) {
                    detectedProvider = 'microsoft';
                }
                setProvider(detectedProvider);

                if (error) {
                    setError(`OAuth Error: ${error} - ${errorDescription || 'Unknown error'}`);
                    setStatus('error');
                    return;
                }

                if (!code || !state) {
                    setError('Missing authorization code or state parameter');
                    setStatus('error');
                    return;
                }

                // Complete the OAuth flow
                const result = await gatewayClient.completeOAuthFlow(detectedProvider, code, state);

                if (result?.success) {
                    setStatus('success');
                    // Redirect back to settings integrations page after a short delay
                    setTimeout(() => {
                        router.push('/settings?page=integrations&oauth_return=true');
                    }, 2000);
                } else {
                    setError(result?.error || 'Failed to complete OAuth flow');
                    setStatus('error');
                }
            } catch (err) {
                console.error('OAuth callback error:', err);
                setError('Failed to complete OAuth flow. Please try again.');
                setStatus('error');
            }
        };

        handleCallback();
    }, [searchParams, router]);

    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Loader2 className="h-5 w-5 animate-spin" />
                            Completing OAuth Flow
                        </CardTitle>
                        <CardDescription>
                            Please wait while we complete your {provider} integration...
                        </CardDescription>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-green-600">
                            <CheckCircle className="h-5 w-5" />
                            Integration Successful
                        </CardTitle>
                        <CardDescription>
                            Your {provider} integration has been successfully connected!
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button
                            onClick={() => router.push('/settings?page=integrations&oauth_return=true')}
                            className="w-full"
                        >
                            Back to Integrations
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-600">
                        <XCircle className="h-5 w-5" />
                        Integration Failed
                    </CardTitle>
                    <CardDescription>
                        We couldn't complete your {provider} integration.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                    <div className="flex gap-2">
                        <Button
                            onClick={() => router.push('/settings?page=integrations&oauth_return=true')}
                            variant="outline"
                            className="flex-1"
                        >
                            Back to Integrations
                        </Button>
                        <Button
                            onClick={() => router.push('/settings?page=integrations&oauth_return=true')}
                            className="flex-1"
                        >
                            Try Again
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

function LoadingFallback() {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Loading...
                    </CardTitle>
                    <CardDescription>
                        Please wait while we process your request...
                    </CardDescription>
                </CardHeader>
            </Card>
        </div>
    );
}

export default function IntegrationCallbackPage() {
    return (
        <Suspense fallback={<LoadingFallback />}>
            <IntegrationCallbackContent />
        </Suspense>
    );
}