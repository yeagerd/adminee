import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Bot, CheckCircle, Sparkles, XCircle } from 'lucide-react';

interface AIDraftIndicatorProps {
    isAIGenerated: boolean;
    status?: 'pending' | 'approved' | 'rejected' | 'modified';
    className?: string;
    showActions?: boolean;
    onApprove?: () => void;
    onReject?: () => void;
}

export function AIDraftIndicator({
    isAIGenerated,
    status = 'pending',
    className,
    showActions = false,
    onApprove,
    onReject,
}: AIDraftIndicatorProps) {
    if (!isAIGenerated) {
        return null;
    }

    const getStatusConfig = () => {
        switch (status) {
            case 'approved':
                return {
                    icon: CheckCircle,
                    text: 'AI Approved',
                    variant: 'default' as const,
                    color: 'text-green-600',
                };
            case 'rejected':
                return {
                    icon: XCircle,
                    text: 'AI Rejected',
                    variant: 'destructive' as const,
                    color: 'text-red-600',
                };
            case 'modified':
                return {
                    icon: Bot,
                    text: 'AI Modified',
                    variant: 'secondary' as const,
                    color: 'text-blue-600',
                };
            default:
                return {
                    icon: Sparkles,
                    text: 'AI Generated',
                    variant: 'outline' as const,
                    color: 'text-purple-600',
                };
        }
    };

    const config = getStatusConfig();
    const Icon = config.icon;

    return (
        <div className={cn('flex items-center gap-2', className)}>
            <Badge variant={config.variant} className="flex items-center gap-1">
                <Icon className={cn('h-3 w-3', config.color)} />
                <span className="text-xs font-medium">{config.text}</span>
            </Badge>

            {showActions && status === 'pending' && (
                <div className="flex items-center gap-1">
                    <button
                        onClick={onApprove}
                        className="p-1 rounded hover:bg-green-100 transition-colors"
                        title="Approve AI draft"
                    >
                        <CheckCircle className="h-3 w-3 text-green-600" />
                    </button>
                    <button
                        onClick={onReject}
                        className="p-1 rounded hover:bg-red-100 transition-colors"
                        title="Reject AI draft"
                    >
                        <XCircle className="h-3 w-3 text-red-600" />
                    </button>
                </div>
            )}
        </div>
    );
} 