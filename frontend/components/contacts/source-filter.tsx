import React from 'react';
import { Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface SourceFilterProps {
    sourceFilter: string[];
    onSourceFilterChange: (sources: string[]) => void;
    availableSources: string[];
    providerInfo?: Record<string, string>; // e.g., { 'office': 'microsoft' }
}

const SourceFilter: React.FC<SourceFilterProps> = ({
    sourceFilter,
    onSourceFilterChange,
    availableSources,
    providerInfo = {},
}) => {
    const [isOpen, setIsOpen] = React.useState(false);
    const allSources = ['office', 'email', 'calendar', 'documents'];
    
    // "All Sources" is selected when explicitly chosen (empty array means no filter applied)
    const allSourcesSelected = sourceFilter.length === 0;
    
    // Get the sources that are actually available in the data
    const effectiveAvailableSources = allSources.filter(source => availableSources.includes(source));

    const handleAllSourcesToggle = () => {
        if (allSourcesSelected) {
            // If "All Sources" is selected, select all available sources
            onSourceFilterChange([...effectiveAvailableSources]);
        } else {
            // If specific sources are selected, clear the selection (back to "All Sources")
            onSourceFilterChange([]);
        }
    };

    const handleSourceToggle = (source: string) => {
        if (sourceFilter.includes(source)) {
            // Remove source from filter
            const newFilter = sourceFilter.filter(s => s !== source);
            onSourceFilterChange(newFilter);
        } else {
            // Add source to filter
            onSourceFilterChange([...sourceFilter, source]);
        }
    };



    const getSourceLabel = (source: string) => {
        switch (source) {
            case 'office':
                const provider = providerInfo[source];
                if (provider) {
                    return `${provider.charAt(0).toUpperCase() + provider.slice(1)} Contacts`;
                }
                return 'Office Contacts';
            case 'email':
                return 'Email';
            case 'calendar':
                return 'Calendar';
            case 'documents':
                return 'Documents';
            default:
                return source;
        }
    };

    const getSourceIcon = (source: string) => {
        switch (source) {
            case 'office':
                return '🏢';
            case 'email':
                return '📧';
            case 'calendar':
                return '📅';
            case 'documents':
                return '📄';
            default:
                return '📋';
        }
    };

    // Handle click outside to close dropdown
    React.useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Element;
            if (!target.closest('.source-filter-dropdown')) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="relative source-filter-dropdown">
            <Button
                variant="outline"
                size="sm"
                onClick={() => setIsOpen(!isOpen)}
                className="min-w-[140px] justify-between"
            >
                <span>Source Filter</span>
                <span className={`ml-2 transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
            </Button>

            {isOpen && (
                <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 min-w-[200px] z-10">
                <div className="space-y-3">
                    {/* All Sources Option */}
                    <div className="border-b border-gray-200 pb-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={allSourcesSelected}
                                onChange={handleAllSourcesToggle}
                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className={`font-medium ${allSourcesSelected ? 'text-gray-900' : 'text-gray-600'}`}>
                                All Sources
                            </span>
                        </label>
                    </div>

                    {/* Individual Source Options */}
                    <div className="space-y-2">
                        {allSources.map(source => {
                            const isAvailable = availableSources.includes(source);
                            const isSelected = sourceFilter.includes(source);
                            const isDisabled = allSourcesSelected;

                            return (
                                <label
                                    key={source}
                                    className={`flex items-center gap-2 cursor-pointer ${
                                        isDisabled ? 'opacity-50 cursor-not-allowed' : ''
                                    }`}
                                >
                                    <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={() => handleSourceToggle(source)}
                                        disabled={isDisabled}
                                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                                    />
                                    <span className="text-sm">{getSourceIcon(source)} {getSourceLabel(source)}</span>
                                    {!isAvailable && (
                                        <span className="text-xs text-gray-400">(No data)</span>
                                    )}
                                </label>
                            );
                        })}
                    </div>


                </div>
                </div>
            )}
        </div>
    );
};

export default SourceFilter;
