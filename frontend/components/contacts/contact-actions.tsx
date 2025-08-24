import React, { useState } from 'react';
import { Plus, RefreshCw, Settings, BarChart3, Trash2, Tag, Download, Upload, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface ContactActionsProps {
  onAddContact: () => void;
  onRefresh: () => void;
  onDiscoverySettings: () => void;
  onAnalytics: () => void;
  onBulkDelete: (contactIds: string[]) => void;
  onBulkTag: (contactIds: string[], tags: string[]) => void;
  onExport: () => void;
  onImport: () => void;
  selectedContacts: string[];
  totalContacts: number;
  isRefreshing: boolean;
  hasActiveFilters: boolean;
}

const ContactActions: React.FC<ContactActionsProps> = ({
  onAddContact,
  onRefresh,
  onDiscoverySettings,
  onAnalytics,
  onBulkDelete,
  onBulkTag,
  onExport,
  onImport,
  selectedContacts,
  totalContacts,
  isRefreshing,
  hasActiveFilters,
}) => {
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [bulkTags, setBulkTags] = useState<string[]>([]);

  const handleBulkDelete = () => {
    if (selectedContacts.length > 0) {
      onBulkDelete(selectedContacts);
      setShowBulkActions(false);
    }
  };

  const handleBulkTag = () => {
    if (selectedContacts.length > 0 && bulkTags.length > 0) {
      onBulkTag(selectedContacts, bulkTags);
      setShowBulkActions(false);
      setBulkTags([]);
    }
  };

  const handleTagInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const tags = e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
    setBulkTags(tags);
  };

  const hasSelection = selectedContacts.length > 0;

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Actions</h3>
        {hasSelection && (
          <Badge variant="secondary" className="text-sm">
            {selectedContacts.length} selected
          </Badge>
        )}
      </div>

      {/* Primary Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          onClick={onAddContact}
          className="w-full"
          size="sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Contact
        </Button>

        <Button
          onClick={onRefresh}
          disabled={isRefreshing}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {/* Management Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          onClick={onDiscoverySettings}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <Settings className="w-4 h-4 mr-2" />
          Discovery Settings
        </Button>

        <Button
          onClick={onAnalytics}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <BarChart3 className="w-4 h-4 mr-2" />
          Analytics
        </Button>
      </div>

      {/* Import/Export Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          onClick={onImport}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <Upload className="w-4 h-4 mr-2" />
          Import
        </Button>

        <Button
          onClick={onExport}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Bulk Actions */}
      {hasSelection && (
        <div className="border-t border-gray-200 pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">Bulk Actions</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowBulkActions(!showBulkActions)}
            >
              <Filter className="w-4 h-4 mr-1" />
              {showBulkActions ? 'Hide' : 'Show'}
            </Button>
          </div>

          {showBulkActions && (
            <div className="space-y-3">
              {/* Bulk Tag */}
              <div className="space-y-2">
                <label className="text-sm text-gray-600">Add tags (comma-separated):</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="work, important, client"
                    value={bulkTags.join(', ')}
                    onChange={handleTagInputChange}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <Button
                    onClick={handleBulkTag}
                    disabled={bulkTags.length === 0}
                    size="sm"
                    variant="outline"
                  >
                    <Tag className="w-4 h-4 mr-1" />
                    Tag
                  </Button>
                </div>
              </div>

              {/* Bulk Delete */}
              <div className="flex gap-2">
                <Button
                  onClick={handleBulkDelete}
                  variant="destructive"
                  size="sm"
                  className="flex-1"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Selected ({selectedContacts.length})
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Statistics */}
      <div className="border-t border-gray-200 pt-4">
        <div className="text-sm text-gray-600">
          <div className="flex justify-between">
            <span>Total Contacts:</span>
            <span className="font-medium">{totalContacts}</span>
          </div>
          {hasActiveFilters && (
            <div className="flex justify-between mt-1">
              <span>Filtered:</span>
              <span className="font-medium text-blue-600">Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Quick Tips */}
      <div className="border-t border-gray-200 pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Quick Tips</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• Use filters to find specific contacts</li>
          <li>• Select multiple contacts for bulk actions</li>
          <li>• Tags help organize your contact list</li>
          <li>• Relevance scores show contact importance</li>
        </ul>
      </div>
    </div>
  );
};

export default ContactActions;
