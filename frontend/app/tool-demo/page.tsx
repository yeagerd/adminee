'use client';

import { ToolStateDemo } from '@/components/tool-state-demo';
import { ToolProvider } from '@/contexts/tool-context';
import { Suspense } from 'react';

export default function ToolDemoPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            <ToolProvider>
                <div className="min-h-screen bg-background">
                    <div className="container mx-auto py-8">
                        <h1 className="text-3xl font-bold mb-8">Tool State Management Demo</h1>
                        <ToolStateDemo />
                    </div>
                </div>
            </ToolProvider>
        </Suspense>
    );
} 