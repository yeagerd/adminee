'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CreditCard } from 'lucide-react';

export function BillingContent() {
    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Billing</h1>
                <p className="text-gray-600 mt-2">Manage your subscription and billing information</p>
            </div>

            {/* Coming Soon Card */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <CreditCard className="h-5 w-5" />
                        Billing Management
                    </CardTitle>
                    <CardDescription>
                        Billing features are coming soon
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="text-center py-8">
                        <CreditCard className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                            Billing features coming soon
                        </h3>
                        <p className="text-gray-600">
                            We're working on bringing you comprehensive billing management features.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 