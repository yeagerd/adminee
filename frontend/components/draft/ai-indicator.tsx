'use client';

import { cn } from '@/lib/utils';
import { Sparkles } from 'lucide-react';

interface AIIndicatorProps {
    isAIGenerated: boolean;
    className?: string;
    showLabel?: boolean;
    size?: 'sm' | 'md' | 'lg';
}

export function AIIndicator({
    isAIGenerated,
    className,
    showLabel = true,
    size = 'md'
}: AIIndicatorProps) {
    if (!isAIGenerated) return null;

    const sizeClasses = {
        sm: 'w-3 h-3',
        md: 'w-4 h-4',
        lg: 'w-5 h-5',
    };

    const textSizes = {
        sm: 'text-xs',
        md: 'text-sm',
        lg: 'text-base',
    };

    return (
        <div className={cn(
            'inline-flex items-center gap-1.5 text-amber-600 bg-amber-50 px-2 py-1 rounded-md border border-amber-200',
            className
        )}>
            <Sparkles className={cn('text-amber-500', sizeClasses[size])} />
            {showLabel && (
                <span className={cn('font-medium', textSizes[size])}>
                    AI Generated
                </span>
            )}
        </div>
    );
}

export function AIIndicatorBadge({
    isAIGenerated,
    className
}: {
    isAIGenerated: boolean;
    className?: string;
}) {
    if (!isAIGenerated) return null;

    return (
        <div className={cn(
            'absolute top-2 right-2 z-10',
            className
        )}>
            <AIIndicator isAIGenerated={true} showLabel={false} size="sm" />
        </div>
    );
} 