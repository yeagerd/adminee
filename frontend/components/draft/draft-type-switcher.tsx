'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { DraftType } from '@/types/draft';
import { Calendar, FileText, Mail } from 'lucide-react';

interface DraftTypeSwitcherProps {
    currentType: DraftType;
    onTypeChange: (type: DraftType) => void;
    className?: string;
    disabled?: boolean;
}

const draftTypes: { type: DraftType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { type: 'email', label: 'Email', icon: Mail },
    { type: 'calendar', label: 'Calendar', icon: Calendar },
    { type: 'document', label: 'Document', icon: FileText },
];

export function DraftTypeSwitcher({
    currentType,
    onTypeChange,
    className,
    disabled = false
}: DraftTypeSwitcherProps) {
    return (
        <div className={cn(
            'flex items-center gap-1 p-1 bg-muted rounded-lg',
            className
        )}>
            {draftTypes.map(({ type, label, icon: Icon }) => (
                <Button
                    key={type}
                    variant={currentType === type ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => onTypeChange(type)}
                    disabled={disabled}
                    className={cn(
                        'flex items-center gap-2 px-3 py-1.5 text-xs font-medium',
                        currentType === type
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                    )}
                >
                    <Icon className="w-3 h-3" />
                    {label}
                </Button>
            ))}
        </div>
    );
}

export function DraftTypeIcon({ type, className }: { type: DraftType; className?: string }) {
    const Icon = draftTypes.find(t => t.type === type)?.icon || FileText;
    return <Icon className={className} />;
} 