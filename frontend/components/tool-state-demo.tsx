'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { TOOL_NAMES } from '@/lib/tool-routing';
import { Tool } from '@/types/navigation';

export function ToolStateDemo() {
    const {
        activeTool,
        toolSettings,
        setActiveTool,
        toggleTool,
        updateToolPreference,
        getEnabledTools,
        getDisabledTools,
        isActiveTool,
        getNextTool,
        getPreviousTool,
    } = useToolStateUtils();

    const handleNextTool = () => {
        const next = getNextTool();
        if (next) setActiveTool(next);
    };

    const handlePreviousTool = () => {
        const prev = getPreviousTool();
        if (prev) setActiveTool(prev);
    };

    return (
        <div className="p-6 space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Tool State Management Demo</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <h3 className="font-semibold mb-2">Current Active Tool</h3>
                        <div className="flex items-center gap-2">
                            <Badge variant="default">{TOOL_NAMES[activeTool]}</Badge>
                            <span className="text-sm text-muted-foreground">({activeTool})</span>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <Button onClick={handlePreviousTool} variant="outline" size="sm">
                            ← Previous Tool
                        </Button>
                        <Button onClick={handleNextTool} variant="outline" size="sm">
                            Next Tool →
                        </Button>
                    </div>

                    <div>
                        <h3 className="font-semibold mb-2">All Tools</h3>
                        <div className="grid grid-cols-2 gap-2">
                            {(Object.keys(toolSettings) as Tool[]).map((tool) => (
                                <div
                                    key={tool}
                                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${isActiveTool(tool)
                                        ? 'border-primary bg-primary/5'
                                        : 'border-border hover:border-primary/50'
                                        }`}
                                    onClick={() => setActiveTool(tool)}
                                >
                                    <div className="flex items-center justify-between">
                                        <span className="font-medium">{TOOL_NAMES[tool]}</span>
                                        <div className="flex items-center gap-1">
                                            {toolSettings[tool].enabled ? (
                                                <Badge variant="secondary" className="text-xs">
                                                    Enabled
                                                </Badge>
                                            ) : (
                                                <Badge variant="outline" className="text-xs">
                                                    Disabled
                                                </Badge>
                                            )}
                                            {isActiveTool(tool) && (
                                                <Badge variant="default" className="text-xs">
                                                    Active
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                    <div className="mt-2">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                toggleTool(tool);
                                            }}
                                        >
                                            {toolSettings[tool].enabled ? 'Disable' : 'Enable'}
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h3 className="font-semibold mb-2">Enabled Tools</h3>
                        <div className="flex flex-wrap gap-1">
                            {getEnabledTools().map((tool) => (
                                <Badge key={tool} variant="secondary">
                                    {TOOL_NAMES[tool]}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h3 className="font-semibold mb-2">Disabled Tools</h3>
                        <div className="flex flex-wrap gap-1">
                            {getDisabledTools().map((tool) => (
                                <Badge key={tool} variant="outline">
                                    {TOOL_NAMES[tool]}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h3 className="font-semibold mb-2">Tool Preferences</h3>
                        <div className="space-y-2">
                            {(Object.keys(toolSettings) as Tool[]).map((tool) => (
                                <div key={tool} className="p-3 border rounded">
                                    <h4 className="font-medium mb-2">{TOOL_NAMES[tool]}</h4>
                                    <div className="text-sm text-muted-foreground">
                                        <pre className="whitespace-pre-wrap">
                                            {JSON.stringify(toolSettings[tool].preferences, null, 2)}
                                        </pre>
                                    </div>
                                    <div className="mt-2">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() =>
                                                updateToolPreference(tool, 'lastUpdated', new Date().toISOString())
                                            }
                                        >
                                            Update Timestamp
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 