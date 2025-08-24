import React from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface ContactFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  sourceFilter: string;
  onSourceFilterChange: (value: string) => void;
  providerFilter: string[];
  onProviderFilterChange: (providers: string[]) => void;
  relevanceFilter: [number, number];
  onRelevanceFilterChange: (range: [number, number]) => void;
  eventTypeFilter: string[];
  onEventTypeFilterChange: (types: string[]) => void;
  tagFilter: string[];
  onTagFilterChange: (tags: string[]) => void;
  availableTags: string[];
  onClearAll: () => void;
}

const ContactFilters: React.FC<ContactFiltersProps> = ({
  search,
  onSearchChange,
  sourceFilter,
  onSourceFilterChange,
  providerFilter,
  onProviderFilterChange,
  relevanceFilter,
  onRelevanceFilterChange,
  eventTypeFilter,
  onEventTypeFilterChange,
  tagFilter,
  onTagFilterChange,
  availableTags,
  onClearAll,
}) => {
  const sourceOptions = [
    { value: 'all', label: 'All Sources' },
    { value: 'office', label: 'Office Only' },
    { value: 'discovered', label: 'Discovered Only' },
    { value: 'both', label: 'Both Sources' },
  ];

  const providerOptions = [
    { value: 'google', label: 'Google' },
    { value: 'microsoft', label: 'Microsoft' },
  ];

  const eventTypeOptions = [
    { value: 'email', label: 'Email' },
    { value: 'calendar', label: 'Calendar' },
    { value: 'documents', label: 'Documents' },
  ];

  const handleProviderToggle = (provider: string) => {
    if (providerFilter.includes(provider)) {
      onProviderFilterChange(providerFilter.filter(p => p !== provider));
    } else {
      onProviderFilterChange([...providerFilter, provider]);
    }
  };

  const handleEventTypeToggle = (eventType: string) => {
    if (eventTypeFilter.includes(eventType)) {
      onEventTypeFilterChange(eventTypeFilter.filter(t => t !== eventType));
    } else {
      onEventTypeFilterChange([...eventTypeFilter, eventType]);
    }
  };

  const handleTagToggle = (tag: string) => {
    if (tagFilter.includes(tag)) {
      onTagFilterChange(tagFilter.filter(t => t !== tag));
    } else {
      onTagFilterChange([...tagFilter, tag]);
    }
  };

  const hasActiveFilters = 
    search || 
    sourceFilter !== 'all' || 
    providerFilter.length > 0 || 
    relevanceFilter[0] > 0 || 
    relevanceFilter[1] < 1 || 
    eventTypeFilter.length > 0 || 
    tagFilter.length > 0;

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="w-4 h-4 mr-1" />
            Clear All
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Search</label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search name, email, or notes..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Source Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Source</label>
        <div className="grid grid-cols-2 gap-2">
          {sourceOptions.map((option) => (
            <Button
              key={option.value}
              variant={sourceFilter === option.value ? "default" : "outline"}
              size="sm"
              onClick={() => onSourceFilterChange(option.value)}
              className="justify-start"
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Provider Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Provider</label>
        <div className="flex flex-wrap gap-2">
          {providerOptions.map((option) => (
            <Button
              key={option.value}
              variant={providerFilter.includes(option.value) ? "default" : "outline"}
              size="sm"
              onClick={() => handleProviderToggle(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Relevance Score Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">
          Relevance Score: {Math.round(relevanceFilter[0] * 100)}% - {Math.round(relevanceFilter[1] * 100)}%
        </label>
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={relevanceFilter[0]}
              onChange={(e) => onRelevanceFilterChange([parseFloat(e.target.value), relevanceFilter[1]])}
              className="flex-1"
            />
            <span className="text-sm text-gray-500 min-w-[3rem]">
              {Math.round(relevanceFilter[0] * 100)}%
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={relevanceFilter[1]}
              onChange={(e) => onRelevanceFilterChange([relevanceFilter[0], parseFloat(e.target.value)])}
              className="flex-1"
            />
            <span className="text-sm text-gray-500 min-w-[3rem]">
              {Math.round(relevanceFilter[1] * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Event Type Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Event Types</label>
        <div className="flex flex-wrap gap-2">
          {eventTypeOptions.map((option) => (
            <Button
              key={option.value}
              variant={eventTypeFilter.includes(option.value) ? "default" : "outline"}
              size="sm"
              onClick={() => handleEventTypeToggle(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Tags Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Tags</label>
        <div className="flex flex-wrap gap-2">
          {availableTags.map((tag) => (
            <Button
              key={tag}
              variant={tagFilter.includes(tag) ? "default" : "outline"}
              size="sm"
              onClick={() => handleTagToggle(tag)}
            >
              {tag}
            </Button>
          ))}
        </div>
        {tagFilter.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <span className="text-xs text-gray-500">Selected:</span>
            {tagFilter.map((tag) => (
              <Badge
                key={tag}
                variant="secondary"
                className="text-xs"
              >
                {tag}
                <button
                  onClick={() => handleTagToggle(tag)}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {search && (
              <Badge variant="outline" className="text-xs">
                Search: "{search}"
                <button
                  onClick={() => onSearchChange('')}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
            {sourceFilter !== 'all' && (
              <Badge variant="outline" className="text-xs">
                Source: {sourceOptions.find(o => o.value === sourceFilter)?.label}
                <button
                  onClick={() => onSourceFilterChange('all')}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
            {providerFilter.map((provider) => (
              <Badge key={provider} variant="outline" className="text-xs">
                Provider: {provider}
                <button
                  onClick={() => handleProviderToggle(provider)}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
            {(relevanceFilter[0] > 0 || relevanceFilter[1] < 1) && (
              <Badge variant="outline" className="text-xs">
                Relevance: {Math.round(relevanceFilter[0] * 100)}% - {Math.round(relevanceFilter[1] * 100)}%
                <button
                  onClick={() => onRelevanceFilterChange([0, 1])}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
            {eventTypeFilter.map((eventType) => (
              <Badge key={eventType} variant="outline" className="text-xs">
                Event: {eventType}
                <button
                  onClick={() => handleEventTypeToggle(eventType)}
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
  );
};

export default ContactFilters;
