/* 
 * Package types for the frontend application.
 */

export interface Package {
    id: string;
    name: string;
    description?: string;
    labels?: string[];
    status: string;
    created_at: string;
    updated_at: string;
    [key: string]: any;
}

export type PackageStatus = 'pending' | 'in_transit' | 'delivered' | 'failed' | 'returned';
