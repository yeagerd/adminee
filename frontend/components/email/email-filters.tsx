import type { EmailFilters } from '@/types/office-service';
import React from 'react';

interface EmailFiltersProps {
    filters: EmailFilters;
    setFilters: (filters: EmailFilters) => void;
}

const EmailFilters: React.FC<EmailFiltersProps> = ({ filters, setFilters }) => {
    return (
        <div className="mt-2 flex gap-2">
            <input
                type="text"
                placeholder="Search emails…"
                className="border rounded px-2 py-1 text-sm"
                value={filters.query || ''}
                onChange={e => setFilters({ ...filters, query: e.target.value })}
            />
            {/* Add more filter controls here as needed */}
        </div>
    );
};

export default EmailFilters; 