'use client';

import { ToolStateDemo } from '@/components/tool-state-demo';
import { ToolProvider } from '@/contexts/tool-context';

export default function ToolDemoPage() {
    return (
        <ToolProvider>
            <div className="min-h-screen bg-background">
                <div className="container mx-auto py-8">
                    <h1 className="text-3xl font-bold mb-8">Tool State Management Demo</h1>
                    <ToolStateDemo />
                </div>
            </div>
        </ToolProvider>
    );
} 