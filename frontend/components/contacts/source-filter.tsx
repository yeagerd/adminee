import React from 'react';
import { Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface SourceFilterProps {
    sourceFilter: string[];
    onSourceFilterChange: (sources: string[]) => void;
    availableSources: string[];
}

const SourceFilter: React.FC<SourceFilterProps> = ({
    sourceFilter,
    onSourceFilterChange,
    availableSources,
}) => {
    const allSources = ['office', 'email', 'calendar', 'documents'];
    const allSourcesSelected = sourceFilter.length === 0 || sourceFilter.length === allSources.length;

    const handleAllSourcesToggle = () => {
        if (allSourcesSelected) {
            // If all sources are selected, clear the selection
            onSourceFilterChange([]);
        } else {
            // If not all sources are selected, select all available sources
            onSourceFilterChange([...availableSources]);
        }
    };

    const handleSourceToggle = (source: string) => {
        if (sourceFilter.includes(source)) {
            // Remove source from filter
            onSourceFilterChange(sourceFilter.filter(s => s !== source));
        } else {
            // Add source to filter
            onSourceFilterChange([...sourceFilter, source]);
        }
    };

    const handleClearAll = () => {
        onSourceFilterChange([]);
    };

    const getSourceLabel = (source: string) => {
        switch (source) {
            case 'office':
                return 'Office';
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

    return (
        <div className="relative">
            <Button
                variant="outline"
                size="sm"
                onClick={() => {}} // This will be controlled by parent
                className="min-w-[140px] justify-between"
            >
                <span>Source Filter</span>
                <span className="ml-2">▼</span>
            </Button>

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

                    {/* Active Filters Summary */}
                    {sourceFilter.length > 0 && (
                        <div className="border-t border-gray-200 pt-2">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-gray-600">Active:</span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleClearAll}
                                    className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"
                                >
                                    <X className="w-3 h-3 mr-1" />
                                    Clear
                                </Button>
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {sourceFilter.map(source => (
                                    <Badge
                                        key={source}
                                        variant="secondary"
                                        className="text-xs"
                                    >
                                        {getSourceIcon(source)} {getSourceLabel(source)}
                                        <button
                                            onClick={() => handleSourceToggle(source)}
                                            className="ml-1 hover:text-red-500"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SourceFilter;
