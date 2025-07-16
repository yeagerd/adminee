'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Lock } from 'lucide-react';

export function SecurityContent() {
    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Security</h1>
                <p className="text-gray-600 mt-2">Manage your account security settings</p>
            </div>

            {/* Coming Soon Card */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Lock className="h-5 w-5" />
                        Security Settings
                    </CardTitle>
                    <CardDescription>
                        Security features are coming soon
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="text-center py-8">
                        <Lock className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                            Security features coming soon
                        </h3>
                        <p className="text-gray-600">
                            We're working on bringing you comprehensive security management features.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 