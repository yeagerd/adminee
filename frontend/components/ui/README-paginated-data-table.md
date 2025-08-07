# Paginated Data Table Components

This directory contains abstracted pagination components that can be reused across different data types in the Briefly application.

## Components

### `PaginatedDataTable`

A generic, reusable data table component with built-in pagination support.

**Features:**
- Generic typing for any data type
- Configurable columns with sorting
- Built-in pagination controls
- Customizable row rendering
- Loading and empty states
- Click handlers for rows and actions

**Props:**
```typescript
interface PaginatedDataTableProps<T> {
    data: T[];                                    // Array of data items
    columns: ColumnDefinition<T>[];               // Column definitions
    pagination?: PaginationState;                 // Pagination state
    paginationHandlers?: PaginationHandlers;      // Pagination event handlers
    onSort?: (field: string) => void;            // Sort handler
    onRowClick?: (item: T) => void;              // Row click handler
    rowRenderer: (item: T, index: number) => React.ReactNode; // Custom row renderer
    emptyMessage?: string;                        // Message when no data
    loadingMessage?: string;                      // Message when loading
    className?: string;                           // Additional CSS classes
    tableClassName?: string;                      // Table-specific CSS classes
}
```

### `usePagination` Hook

A custom hook for managing pagination state and handlers.

**Features:**
- Cursor-based pagination state management
- Loading state management
- Page change handlers
- Reset functionality

**Usage:**
```typescript
const {
    paginationState,
    paginationHandlers,
    setPaginationData,
    setLoading,
    resetPagination,
} = usePagination({
    initialLimit: 20,
    onPageChange: (cursor, direction) => {
        // Handle page changes
    },
});
```

## Usage Examples

### Basic Usage

```typescript
import PaginatedDataTable, { ColumnDefinition } from '@/components/ui/paginated-data-table';
import { usePagination } from '@/hooks/use-pagination';

interface MyDataType {
    id: string;
    name: string;
    status: string;
}

function MyComponent() {
    const [data, setData] = useState<MyDataType[]>([]);
    
    const {
        paginationState,
        paginationHandlers,
        setPaginationData,
    } = usePagination({
        onPageChange: handlePageChange,
    });

    const columns: ColumnDefinition<MyDataType>[] = [
        { key: 'name', header: 'Name', sortable: true },
        { key: 'status', header: 'Status', sortable: true },
    ];

    const renderRow = (item: MyDataType) => (
        <>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.status}</TableCell>
        </>
    );

    return (
        <PaginatedDataTable
            data={data}
            columns={columns}
            pagination={paginationState}
            paginationHandlers={paginationHandlers}
            rowRenderer={renderRow}
            onRowClick={(item) => console.log('Clicked:', item)}
        />
    );
}
```

### Advanced Usage with Custom Components

See `ShipmentsList.tsx` for an example of a more complex implementation with:
- Custom row rendering with inline editing
- Filter components in headers
- Action buttons
- Status badges
- Icons and formatting

### Migration from Existing Components

To migrate from the existing `PackageList` component:

1. **Replace the table structure** with `PaginatedDataTable`
2. **Extract row rendering logic** into a `rowRenderer` function
3. **Use the `usePagination` hook** instead of manual state management
4. **Define columns** using the `ColumnDefinition` interface

**Before (PackageList):**
```typescript
<Table>
    <TableHeader>
        <TableRow>
            <TableHead>Tracking Number</TableHead>
            <TableHead>Status</TableHead>
        </TableRow>
    </TableHeader>
    <TableBody>
        {packages.map(pkg => (
            <TableRow key={pkg.id}>
                <TableCell>{pkg.tracking_number}</TableCell>
                <TableCell>{pkg.status}</TableCell>
            </TableRow>
        ))}
    </TableBody>
</Table>
```

**After (PaginatedDataTable):**
```typescript
const columns: ColumnDefinition<Package>[] = [
    { key: 'tracking_number', header: 'Tracking Number', sortable: true },
    { key: 'status', header: 'Status', sortable: true },
];

const renderRow = (pkg: Package) => (
    <>
        <TableCell>{pkg.tracking_number}</TableCell>
        <TableCell>{pkg.status}</TableCell>
    </>
);

<PaginatedDataTable
    data={packages}
    columns={columns}
    rowRenderer={renderRow}
    pagination={paginationState}
    paginationHandlers={paginationHandlers}
/>
```

## Benefits

1. **Reusability**: Can be used for any data type with proper typing
2. **Consistency**: Standardized pagination UI across the application
3. **Maintainability**: Centralized pagination logic
4. **Flexibility**: Custom row rendering allows for complex layouts
5. **Type Safety**: Full TypeScript support with generic types

## Integration with Existing APIs

The components are designed to work with the existing cursor-based pagination APIs:

- `services/shipments/routers/packages.py` - Shipments pagination
- `services/user/routers/users.py` - User pagination
- `frontend/lib/shipments-client.ts` - Frontend API client

The pagination state structure matches the API response format:
```typescript
{
    hasNext: boolean;
    hasPrev: boolean;
    nextCursor?: string;
    prevCursor?: string;
    loading: boolean;
}
```
