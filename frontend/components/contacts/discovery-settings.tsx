import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Calendar, FileText, Mail, Play, RefreshCw, Settings, Stop, X } from 'lucide-react';
import React, { useState } from 'react';

interface DiscoverySettingsProps {
    onClose: () => void;
}

interface DiscoveryConfig {
    email: boolean;
    calendar: boolean;
    documents: boolean;
    frequency: 'realtime' | 'hourly' | 'daily' | 'weekly';
    batchSize: number;
    maxConcurrent: number;
}

interface DiscoveryStats {
    lastRun: string;
    nextRun: string;
    totalContacts: number;
    newContacts: number;
    updatedContacts: number;
    errors: number;
    processingTime: number;
}

const ContactDiscoverySettings: React.FC<DiscoverySettingsProps> = ({ onClose }) => {
    const [config, setConfig] = useState<DiscoveryConfig>({
        email: true,
        calendar: true,
        documents: true,
        frequency: 'hourly',
        batchSize: 100,
        maxConcurrent: 5,
    });

    const [stats, setStats] = useState<DiscoveryStats>({
        lastRun: '2024-01-15T10:30:00Z',
        nextRun: '2024-01-15T11:30:00Z',
        totalContacts: 1247,
        newContacts: 23,
        updatedContacts: 45,
        errors: 2,
        processingTime: 45,
    });

    const [isRunning, setIsRunning] = useState(false);
    const [logs, setLogs] = useState<string[]>([
        '2024-01-15 10:30:15 - Discovery started',
        '2024-01-15 10:30:20 - Processing email events (batch 1/5)',
        '2024-01-15 10:30:25 - Found 12 new contacts in email',
        '2024-01-15 10:30:30 - Processing calendar events (batch 2/5)',
        '2024-01-15 10:30:35 - Found 8 new contacts in calendar',
        '2024-01-15 10:30:40 - Processing document events (batch 3/5)',
        '2024-01-15 10:30:45 - Found 3 new contacts in documents',
        '2024-01-15 10:30:50 - Discovery completed successfully',
    ]);

    const handleConfigChange = (field: keyof DiscoveryConfig, value: any) => {
        setConfig(prev => ({ ...prev, [field]: value }));
    };

    const handleStartDiscovery = () => {
        setIsRunning(true);
        setLogs(prev => [`${new Date().toISOString()} - Manual discovery started`, ...prev.slice(0, 9)]);

        // Simulate discovery process
        setTimeout(() => {
            setLogs(prev => [`${new Date().toISOString()} - Manual discovery completed`, ...prev.slice(0, 9)]);
            setIsRunning(false);
        }, 3000);
    };

    const handleStopDiscovery = () => {
        setIsRunning(false);
        setLogs(prev => [`${new Date().toISOString()} - Discovery stopped by user`, ...prev.slice(0, 9)]);
    };

    const frequencyOptions = [
        { value: 'realtime', label: 'Real-time', description: 'Process events as they occur' },
        { value: 'hourly', label: 'Hourly', description: 'Process events every hour' },
        { value: 'daily', label: 'Daily', description: 'Process events once per day' },
        { value: 'weekly', label: 'Weekly', description: 'Process events once per week' },
    ];

    const eventTypes = [
        { key: 'email', label: 'Email Events', icon: Mail, description: 'Discover contacts from email communications' },
        { key: 'calendar', label: 'Calendar Events', icon: Calendar, description: 'Discover contacts from calendar events' },
        { key: 'documents', label: 'Document Events', icon: FileText, description: 'Discover contacts from document interactions' },
    ];

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Contact Discovery Settings</h2>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                >
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Discovery Configuration */}
                <div className="space-y-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Discovery Configuration</h3>

                        {/* Event Type Toggles */}
                        <div className="space-y-4">
                            {eventTypes.map(({ key, label, icon: Icon, description }) => (
                                <div key={key} className="flex items-start gap-3">
                                    <Switch
                                        checked={config[key as keyof DiscoveryConfig] as boolean}
                                        onCheckedChange={(checked) => handleConfigChange(key as keyof DiscoveryConfig, checked)}
                                    />
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Icon className="w-4 h-4 text-gray-600" />
                                            <Label className="font-medium">{label}</Label>
                                        </div>
                                        <p className="text-sm text-gray-600">{description}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Frequency Settings */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Discovery Frequency</h4>
                        <div className="space-y-3">
                            {frequencyOptions.map(({ value, label, description }) => (
                                <div key={value} className="flex items-start gap-3">
                                    <input
                                        type="radio"
                                        id={value}
                                        name="frequency"
                                        value={value}
                                        checked={config.frequency === value}
                                        onChange={(e) => handleConfigChange('frequency', e.target.value)}
                                        className="mt-1"
                                    />
                                    <div>
                                        <Label htmlFor={value} className="font-medium">{label}</Label>
                                        <p className="text-sm text-gray-600">{description}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Performance Settings */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Performance Settings</h4>
                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="batchSize" className="text-sm font-medium text-gray-700">
                                    Batch Size: {config.batchSize}
                                </Label>
                                <Input
                                    id="batchSize"
                                    type="range"
                                    min="10"
                                    max="500"
                                    step="10"
                                    value={config.batchSize}
                                    onChange={(e) => handleConfigChange('batchSize', parseInt(e.target.value))}
                                    className="mt-2"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Number of events to process in each batch
                                </p>
                            </div>

                            <div>
                                <Label htmlFor="maxConcurrent" className="text-sm font-medium text-gray-700">
                                    Max Concurrent: {config.maxConcurrent}
                                </Label>
                                <Input
                                    id="maxConcurrent"
                                    type="range"
                                    min="1"
                                    max="10"
                                    step="1"
                                    value={config.maxConcurrent}
                                    onChange={(e) => handleConfigChange('maxConcurrent', parseInt(e.target.value))}
                                    className="mt-2"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Maximum number of concurrent discovery processes
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Discovery Status & Controls */}
                <div className="space-y-6">
                    {/* Status Overview */}
                    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <h3 className="text-lg font-semibold text-blue-900 mb-4">Discovery Status</h3>

                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span className="text-blue-600">Last Run:</span>
                                <p className="font-medium text-blue-900">
                                    {new Date(stats.lastRun).toLocaleString()}
                                </p>
                            </div>
                            <div>
                                <span className="text-blue-600">Next Run:</span>
                                <p className="font-medium text-blue-900">
                                    {new Date(stats.nextRun).toLocaleString()}
                                </p>
                            </div>
                            <div>
                                <span className="text-blue-600">Status:</span>
                                <Badge variant={isRunning ? "default" : "secondary"} className="ml-2">
                                    {isRunning ? 'Running' : 'Idle'}
                                </Badge>
                            </div>
                            <div>
                                <span className="text-blue-600">Processing Time:</span>
                                <p className="font-medium text-blue-900">{stats.processingTime}s</p>
                            </div>
                        </div>
                    </div>

                    {/* Discovery Controls */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Discovery Controls</h4>

                        <div className="flex gap-3">
                            <Button
                                onClick={handleStartDiscovery}
                                disabled={isRunning}
                                className="flex-1"
                            >
                                <Play className="w-4 h-4 mr-2" />
                                {isRunning ? 'Running...' : 'Start Discovery'}
                            </Button>

                            <Button
                                onClick={handleStopDiscovery}
                                disabled={!isRunning}
                                variant="outline"
                                className="flex-1"
                            >
                                <Stop className="w-4 h-4 mr-2" />
                                Stop
                            </Button>
                        </div>
                    </div>

                    {/* Statistics */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Discovery Statistics</h4>

                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div className="text-center p-3 bg-white rounded border">
                                <div className="text-2xl font-bold text-blue-600">{stats.totalContacts}</div>
                                <div className="text-gray-600">Total Contacts</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded border">
                                <div className="text-2xl font-bold text-green-600">{stats.newContacts}</div>
                                <div className="text-gray-600">New This Run</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded border">
                                <div className="text-2xl font-bold text-purple-600">{stats.updatedContacts}</div>
                                <div className="text-gray-600">Updated</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded border">
                                <div className="text-2xl font-bold text-red-600">{stats.errors}</div>
                                <div className="text-gray-600">Errors</div>
                            </div>
                        </div>
                    </div>

                    {/* Discovery Logs */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">Discovery Logs</h4>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setLogs([])}
                            >
                                <RefreshCw className="w-4 h-4" />
                            </Button>
                        </div>

                        <div className="bg-white rounded border p-3 h-32 overflow-y-auto text-xs font-mono">
                            {logs.length > 0 ? (
                                logs.map((log, index) => (
                                    <div key={index} className="text-gray-700 py-1">
                                        {log}
                                    </div>
                                ))
                            ) : (
                                <div className="text-gray-500">No logs available</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer Actions */}
            <div className="flex justify-end gap-3 pt-6 border-t border-gray-200 mt-6">
                <Button
                    onClick={onClose}
                    variant="outline"
                >
                    Close
                </Button>

                <Button
                    onClick={() => {
                        // Save configuration
                        console.log('Saving discovery configuration:', config);
                        onClose();
                    }}
                >
                    <Settings className="w-4 h-4 mr-2" />
                    Save Configuration
                </Button>
            </div>
        </div>
    );
};

export default ContactDiscoverySettings;
