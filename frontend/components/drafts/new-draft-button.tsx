import { Button } from '@/components/ui/button';

export function NewDraftButton({ onClick }: { onClick: () => void }) {
    return (
        <Button onClick={onClick} variant="default">
            New
        </Button>
    );
} 