'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Calendar, FileText, Lock, Mail, Shield, User } from 'lucide-react';

export interface OAuthScope {
    name: string;
    description: string;
    required: boolean;
    sensitive: boolean;
}

interface ScopeSelectorProps {
    provider: string;
    scopes: OAuthScope[];
    selectedScopes: string[];
    onScopeChange: (scopes: string[]) => void;
}

function getScopeIcon(scopeName: string) {
    if (scopeName.includes('mail') || scopeName.includes('gmail')) {
        return <Mail className="h-4 w-4" />;
    }
    if (scopeName.includes('calendar')) {
        return <Calendar className="h-4 w-4" />;
    }
    if (scopeName.includes('drive') || scopeName.includes('files')) {
        return <FileText className="h-4 w-4" />;
    }
    if (scopeName.includes('profile') || scopeName.includes('User.Read')) {
        return <User className="h-4 w-4" />;
    }
    return <Shield className="h-4 w-4" />;
}

export function ScopeSelector({ provider, scopes, selectedScopes, onScopeChange }: ScopeSelectorProps) {
    const requiredScopes = scopes.filter(scope => scope.required);
    const optionalScopes = scopes.filter(scope => !scope.required);

    const handleScopeToggle = (scopeName: string, checked: boolean) => {
        if (checked) {
            onScopeChange([...selectedScopes, scopeName]);
        } else {
            onScopeChange(selectedScopes.filter(s => s !== scopeName));
        }
    };

    const handleSelectAll = () => {
        const allOptionalScopes = optionalScopes.map(scope => scope.name);
        onScopeChange([...requiredScopes.map(scope => scope.name), ...allOptionalScopes]);
    };

    const handleSelectNone = () => {
        onScopeChange(requiredScopes.map(scope => scope.name));
    };

    return (
        <div className="space-y-4">
            {/* Required Scopes */}
            {requiredScopes.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Lock className="h-4 w-4 text-blue-600" />
                            Required Permissions
                        </CardTitle>
                        <CardDescription>
                            These permissions are required for basic functionality and cannot be disabled.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {requiredScopes.map((scope) => (
                                <div key={scope.name} className="flex items-start gap-3 p-2 rounded-lg bg-blue-50 border border-blue-200">
                                    <div className="flex items-center gap-2 text-blue-600">
                                        {getScopeIcon(scope.name)}
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm font-medium text-gray-900">
                                            {scope.description}
                                        </div>
                                        <div className="text-xs text-gray-500 font-mono">
                                            {scope.name}
                                        </div>
                                    </div>
                                    <Badge variant="secondary" className="text-xs">
                                        Required
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Optional Scopes */}
            {optionalScopes.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Shield className="h-4 w-4 text-green-600" />
                            Optional Permissions
                        </CardTitle>
                        <CardDescription>
                            Select the additional permissions you'd like to grant. You can change these later.
                        </CardDescription>
                        <div className="flex gap-2">
                            <button
                                onClick={handleSelectAll}
                                className="text-xs text-blue-600 hover:text-blue-800 underline"
                            >
                                Select All
                            </button>
                            <button
                                onClick={handleSelectNone}
                                className="text-xs text-gray-600 hover:text-gray-800 underline"
                            >
                                Select None
                            </button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {optionalScopes.map((scope) => {
                                const isChecked = selectedScopes.includes(scope.name);
                                return (
                                    <div key={scope.name} className="flex items-start gap-3">
                                        <Checkbox
                                            id={scope.name}
                                            checked={isChecked}
                                            onCheckedChange={(checked) => handleScopeToggle(scope.name, checked as boolean)}
                                            className="mt-1"
                                        />
                                        <Label htmlFor={scope.name} className="flex-1 cursor-pointer">
                                            <div className="flex items-start gap-2">
                                                <div className="flex items-center gap-2 text-gray-700">
                                                    {getScopeIcon(scope.name)}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="text-sm font-medium text-gray-900">
                                                        {scope.description}
                                                    </div>
                                                    <div className="text-xs text-gray-500 font-mono">
                                                        {scope.name}
                                                    </div>
                                                </div>
                                            </div>
                                        </Label>
                                        {scope.sensitive && (
                                            <Badge variant="outline" className="text-xs">
                                                Sensitive
                                            </Badge>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Summary */}
            <Card className="bg-gray-50">
                <CardHeader>
                    <CardTitle className="text-sm font-medium">Selected Permissions</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-sm text-gray-600">
                        <div className="font-medium mb-2">
                            Total: {selectedScopes.length} permission{selectedScopes.length !== 1 ? 's' : ''}
                        </div>
                        <div className="space-y-1">
                            {selectedScopes.map((scopeName) => {
                                const scope = scopes.find(s => s.name === scopeName);
                                return (
                                    <div key={scopeName} className="flex items-center gap-2 text-xs">
                                        {getScopeIcon(scopeName)}
                                        <span className="font-mono">{scopeName}</span>
                                        {scope?.sensitive && (
                                            <Badge variant="outline" className="text-xs">
                                                Sensitive
                                            </Badge>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 