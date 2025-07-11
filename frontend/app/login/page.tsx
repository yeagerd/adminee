import OAuthButtons from '@/components/auth/oauth-buttons';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sailboat } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                {/* Logo */}
                <div className="flex justify-center">
                    <Link href="/" className="flex items-center gap-2">
                        <Sailboat className="h-8 w-8 text-teal-600" />
                        <span className="text-2xl font-bold text-gray-900">Briefly</span>
                    </Link>
                </div>

                {/* Login Card */}
                <Card className="mt-8">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Welcome back</CardTitle>
                        <CardDescription className="text-center">
                            Sign in to your Briefly account to continue
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <OAuthButtons />

                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-background px-2 text-muted-foreground">
                                    Secure authentication
                                </span>
                            </div>
                        </div>

                        <div className="text-center text-sm text-gray-600">
                            <p>
                                By signing in, you agree to our{' '}
                                <Link href="/terms" className="underline hover:text-gray-900">
                                    Terms of Service
                                </Link>{' '}
                                and{' '}
                                <Link href="/privacy" className="underline hover:text-gray-900">
                                    Privacy Policy
                                </Link>
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Help text */}
                <div className="mt-6 text-center">
                    <p className="text-sm text-gray-600">
                        New to Briefly?{' '}
                        <span className="font-medium text-teal-600">
                            Just sign in with your Google or Microsoft account to get started
                        </span>
                    </p>
                </div>
            </div>
        </div>
    );
} 