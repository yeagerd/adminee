import type { EmailFilters } from '@/types/office-service';
import React from 'react';

interface EmailFiltersProps {
    filters: Record<string, unknown>;
    setFilters: (filters: Record<string, unknown>) => void;
}

const EmailFilters: React.FC<EmailFiltersProps> = ({ filters, setFilters }) => {
    return (
        <div className="flex gap-2">
            <input
                type="text"
                placeholder="Search emails…"
                className="border rounded px-2 py-1 text-sm w-full"
                value={typeof filters.query === 'string' ? filters.query : ''}
                onChange={e => setFilters({ ...filters, query: e.target.value })}
            />
            {/* Add more filter controls here as needed */}
        </div>
    );
};

export default EmailFilters; 