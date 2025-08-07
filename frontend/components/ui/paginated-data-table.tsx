import { ChevronLeft, ChevronRight, ChevronsLeft } from 'lucide-react';
import React, { memo } from 'react';
import { Button } from './button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './table';

export interface PaginationState {
    hasNext: boolean;
    hasPrev: boolean;
    nextCursor?: string;
    prevCursor?: string;
    loading: boolean;
}

export interface PaginationHandlers {
    onNextPage?: () => void;
    onPrevPage?: () => void;
    onFirstPage?: () => void;
}

export interface ColumnDefinition<T> {
    key: string;
    header: string;
    sortable?: boolean;
    width?: string;
    align?: 'left' | 'center' | 'right';
}

export interface PaginatedDataTableProps<T> {
    data: T[];
    columns: ColumnDefinition<T>[];
    pagination?: PaginationState;
    paginationHandlers?: PaginationHandlers;
    onSort?: (field: string) => void;
    onRowClick?: (item: T) => void;
    rowRenderer: (item: T, index: number) => React.ReactNode;
    emptyMessage?: string;
    loadingMessage?: string;
    className?: string;
    tableClassName?: string;
}

function PaginatedDataTable<T>({
    data,
    columns,
    pagination,
    paginationHandlers,
    onSort,
    onRowClick,
    rowRenderer,
    emptyMessage = "No items found.",
    loadingMessage = "Loading...",
    className = "",
    tableClassName = "",
}: PaginatedDataTableProps<T>) {
    const handleHeaderClick = (column: ColumnDefinition<T>) => {
        if (column.sortable && onSort) {
            onSort(column.key);
        }
    };

    return (
        <div className={`overflow-x-auto ${className}`}>
            <Table className={tableClassName}>
                <TableHeader>
                    <TableRow>
                        {columns.map((column) => (
                            <TableHead
                                key={column.key}
                                className={`${column.sortable ? 'cursor-pointer hover:bg-gray-50' : ''} ${column.width ? `w-${column.width}` : ''}`}
                                style={{ textAlign: column.align || 'left' }}
                                onClick={() => handleHeaderClick(column)}
                            >
                                {column.header}
                            </TableHead>
                        ))}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.length === 0 ? (
                        <TableRow>
                            <TableCell
                                colSpan={columns.length}
                                className="text-center text-gray-500 py-8"
                            >
                                {pagination?.loading ? loadingMessage : emptyMessage}
                            </TableCell>
                        </TableRow>
                    ) : (
                        data.map((item, index) => (
                            <TableRow
                                key={index}
                                className={onRowClick ? "hover:bg-gray-50 cursor-pointer" : ""}
                                onClick={() => onRowClick?.(item)}
                            >
                                {rowRenderer(item, index)}
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>

            {/* Pagination Controls */}
            {pagination && paginationHandlers && (
                <div className="flex items-center justify-between mt-4 px-2">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={paginationHandlers.onFirstPage}
                            disabled={!pagination.hasPrev || pagination.loading}
                            className="flex items-center gap-1"
                        >
                            <ChevronsLeft className="h-4 w-4" />
                            First
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={paginationHandlers.onPrevPage}
                            disabled={!pagination.hasPrev || pagination.loading}
                            className="flex items-center gap-1"
                        >
                            <ChevronLeft className="h-4 w-4" />
                            Previous
                        </Button>
                    </div>

                    <div className="text-sm text-gray-600">
                        {pagination.loading ? 'Loading...' : `Showing ${data.length} items`}
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={paginationHandlers.onNextPage}
                            disabled={!pagination.hasNext || pagination.loading}
                            className="flex items-center gap-1"
                        >
                            Next
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default memo(PaginatedDataTable) as <T>(props: PaginatedDataTableProps<T>) => React.ReactElement;
