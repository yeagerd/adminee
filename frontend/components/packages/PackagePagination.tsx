import { ChevronLeft, ChevronRight, ChevronsLeft } from 'lucide-react';
import { Button } from '../ui/button';

interface PackagePaginationProps {
    hasNext: boolean;
    hasPrev: boolean;
    loading: boolean;
    onNextPage: () => void;
    onPrevPage: () => void;
    onFirstPage: () => void;
    currentPageInfo?: string;
}

export default function PackagePagination({
    hasNext,
    hasPrev,
    loading,
    onNextPage,
    onPrevPage,
    onFirstPage,
    currentPageInfo = 'Showing packages'
}: PackagePaginationProps) {
    return (
        <div className="flex items-center justify-between mt-4 px-2">
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onFirstPage}
                    disabled={!hasPrev || loading}
                    className="flex items-center gap-1"
                >
                    <ChevronsLeft className="h-4 w-4" />
                    First
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onPrevPage}
                    disabled={!hasPrev || loading}
                    className="flex items-center gap-1"
                >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                </Button>
            </div>
            
            <div className="text-sm text-gray-600">
                {loading ? 'Loading...' : currentPageInfo}
            </div>
            
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onNextPage}
                    disabled={!hasNext || loading}
                    className="flex items-center gap-1"
                >
                    Next
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
} 