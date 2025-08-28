'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandItem } from '@/components/ui/command';
import { Checkbox } from '@/components/ui/checkbox';
import { Check, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SourceFilterProps {
    sourceFilter?: string[];
    onSourceFilterChange: (sources: string[]) => void;
    availableSources: string[];
    providerInfo?: Record<string, string>; // e.g., { 'contacts': 'microsoft' }
}

const SourceFilter: React.FC<SourceFilterProps> = ({
    sourceFilter,
    onSourceFilterChange,
    availableSources,
    providerInfo = {},
}) => {
    const [open, setOpen] = React.useState(false);
    const allSources = ['contacts', 'email', 'calendar', 'documents'];
    
    // "All Sources" is selected when sourceFilter is undefined
    const allSourcesSelected = sourceFilter === undefined;
    
    // Get the sources that are actually available in the data
    const effectiveAvailableSources = allSources.filter(source => availableSources.includes(source));

    const handleAllSourcesToggle = () => {
        if (allSourcesSelected) {
            // If "All Sources" is selected, switch to explicit selection mode with none selected
            onSourceFilterChange([]);
        } else {
            // Switch back to "All Sources" mode (undefined)
            onSourceFilterChange([]);
            // The parent component should interpret empty array as "show all" by setting to undefined
            // We'll handle this in the parent
        }
    };

    const handleSourceToggle = (source: string) => {
        const current = sourceFilter ?? [];
        if (current.includes(source)) {
            // Remove source from filter
            const newFilter = current.filter(s => s !== source);
            onSourceFilterChange(newFilter);
        } else {
            // Add source to filter
            onSourceFilterChange([...current, source]);
        }
    };

    const getSourceLabel = (source: string) => {
        switch (source) {
            case 'contacts':
                const provider = providerInfo[source];
                if (provider) {
                    return `${provider.charAt(0).toUpperCase() + provider.slice(1)} Contacts`;
                }
                return 'Contacts';
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
            case 'contacts':
                return '👥';
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

    // Get display text for the trigger button
    const getTriggerText = () => {
        if (allSourcesSelected) {
            return 'All Sources';
        }
        if (sourceFilter && sourceFilter.length > 0) {
            if (sourceFilter.length === 1) {
                return getSourceLabel(sourceFilter[0]);
            }
            return `${sourceFilter.length} sources`;
        }
        return 'No sources';
    };

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="min-w-[140px] justify-between"
                >
                    {getTriggerText()}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[280px] p-0" align="start">
                <Command>
                    <CommandGroup>
                        {/* All Sources Option */}
                        <CommandItem
                            onSelect={handleAllSourcesToggle}
                            className="flex items-center space-x-2 px-2 py-1.5"
                        >
                            <Checkbox
                                checked={allSourcesSelected}
                                className="mr-2"
                            />
                            <span className="font-medium">All Sources</span>
                        </CommandItem>
                        
                        {/* Individual Source Options */}
                        {allSources.map((source) => {
                            const isAvailable = availableSources.includes(source);
                            const isSelected = (sourceFilter ?? []).includes(source);
                            const isDisabled = allSourcesSelected;

                            return (
                                <CommandItem
                                    key={source}
                                    onSelect={() => !isDisabled && handleSourceToggle(source)}
                                    className={cn(
                                        "flex items-center space-x-2 px-2 py-1.5",
                                        isDisabled && "opacity-50 cursor-not-allowed"
                                    )}
                                    disabled={isDisabled}
                                >
                                    <Checkbox
                                        checked={isSelected}
                                        disabled={isDisabled}
                                        className="mr-2"
                                    />
                                    <span className="text-sm">
                                        {getSourceIcon(source)} {getSourceLabel(source)}
                                        {!isAvailable && (
                                            <span className="text-xs text-muted-foreground ml-1">(No data)</span>
                                        )}
                                    </span>
                                </CommandItem>
                            );
                        })}
                    </CommandGroup>
                    
                    {sourceFilter && sourceFilter.length > 0 && (
                        <>
                            <CommandEmpty>No sources available</CommandEmpty>
                            <div className="border-t p-2">
                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>Selected:</span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => onSourceFilterChange([])}
                                        className="h-6 px-2 text-xs"
                                    >
                                        Clear all
                                    </Button>
                                </div>
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {sourceFilter.map(source => (
                                        <span
                                            key={source}
                                            className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded-md"
                                        >
                                            {getSourceIcon(source)} {getSourceLabel(source)}
                                            <button
                                                onClick={() => handleSourceToggle(source)}
                                                className="ml-1 hover:text-destructive"
                                            >
                                                <Check className="w-3 h-3" />
                                            </button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </Command>
            </PopoverContent>
        </Popover>
    );
};

export default SourceFilter;
