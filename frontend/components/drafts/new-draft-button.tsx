import { Button } from '@/components/ui/button';

export function NewDraftButton({ onClick }: { onClick: () => void }) {
    return (
        <Button onClick={onClick} className="mb-2 w-full" variant="default">
            + New Draft
        </Button>
    );
} 