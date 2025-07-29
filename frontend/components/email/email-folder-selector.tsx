import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useIntegrations } from '@/contexts/integrations-context';
import { Inbox, Mail, Menu, Send, Trash2 } from 'lucide-react';
import React from 'react';

export interface EmailFolder {
    id: string;
    name: string;
    icon: React.ReactNode;
    label: string;
}

const DEFAULT_FOLDERS: EmailFolder[] = [
    {
        id: 'inbox',
        name: 'Inbox',
        icon: <Inbox className="h-4 w-4" />,
        label: 'inbox',
    },
    {
        id: 'sent',
        name: 'Sent',
        icon: <Send className="h-4 w-4" />,
        label: 'sent',
    },
    {
        id: 'draft',
        name: 'Drafts',
        icon: <Mail className="h-4 w-4" />,
        label: 'draft',
    },
    {
        id: 'spam',
        name: 'Spam',
        icon: <Mail className="h-4 w-4" />,
        label: 'spam',
    },
    {
        id: 'trash',
        name: 'Trash',
        icon: <Trash2 className="h-4 w-4" />,
        label: 'trash',
    },
];

interface EmailFolderSelectorProps {
    onFolderSelect: (folder: EmailFolder) => void;
    customFolders?: EmailFolder[];
}

export default function EmailFolderSelector({
    onFolderSelect,
    customFolders = [],
}: EmailFolderSelectorProps) {
    const { integrations } = useIntegrations();

    // Check if user has Microsoft integration for custom folders
    const hasMicrosoft = integrations.some(
        integration => integration.provider === 'microsoft' && integration.status === 'active'
    );

    const allFolders = [...DEFAULT_FOLDERS, ...customFolders];

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <Menu className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
                {allFolders.map((folder) => (
                    <DropdownMenuItem
                        key={folder.id}
                        onClick={() => onFolderSelect(folder)}
                        className="flex items-center gap-2"
                    >
                        {folder.icon}
                        <span>{folder.name}</span>
                    </DropdownMenuItem>
                ))}

                {hasMicrosoft && customFolders.length === 0 && (
                    <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                            Custom folders available for Microsoft accounts
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

export { DEFAULT_FOLDERS };
