import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { safeParseDate } from '@/lib/utils';
import type { EmailThread as EmailThreadType } from "@/types/api/office";
import { Archive, CalendarRange, Clock, Download, MoreHorizontal, Reply, Star, Trash2 } from 'lucide-react';
import React, { useState } from 'react';
import EmailThreadCard from './email-thread-card';
// removed global draft pane wiring for thread-level drafts
import { Draft } from '@/types/draft';
import { getSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import EmailThreadDraft from './email-thread-draft';

interface EmailThreadProps {
    thread: EmailThreadType;
    onSelectMessage?: (messageId: string) => void;
    selectedMessageId?: string;
}

const EmailThread: React.FC<EmailThreadProps> = ({
    thread,
    onSelectMessage,
    selectedMessageId
}) => {
    const router = useRouter();
    const [isStarred, setIsStarred] = useState(false);
    const [threadDrafts, setThreadDrafts] = useState<Draft[]>([]);

    // Handle null/undefined thread or messages
    if (!thread || !thread.messages || thread.messages.length === 0) {
        return (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                No thread data available
            </div>
        );
    }

    // Use the first message for reference
    const firstMessage = thread.messages[0];

    const handleDownload = async () => {
        if (!firstMessage) {
            console.error('No message available for download');
            return;
        }

        try {
            const testData = {
                provider: firstMessage.provider,
                date: firstMessage.date,
                subject: firstMessage.subject,
                sender: firstMessage.from_address?.email || '',
                body_data: {
                    contentType: firstMessage.body_html ? "HTML" : "Text",
                    content: firstMessage.body_html || firstMessage.body_text || ""
                }
            };

            const blob = new Blob([JSON.stringify(testData, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `email_test_${firstMessage.id}_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Failed to download email:', error);
            alert('Failed to download email. Please try again.');
        }
    };

    const handleStarToggle = () => {
        setIsStarred(!isStarred);
        // TODO: Implement actual star functionality
    };

    const startEmailDraft = async (
        mode: 'reply' | 'reply_all' | 'forward',
        sourceMessageId: string
    ) => {
        const source = thread.messages.find(m => m.id === sourceMessageId) || thread.messages[thread.messages.length - 1];
        const provider = source.provider;
        const session = await getSession();
        const userEmail = session?.user?.email || '';

        // Build recipients per mode
        const from = source.from_address?.email || '';
        const toSet = new Set<string>();
        const ccSet = new Set<string>();

        if (mode === 'reply') {
            if (from) toSet.add(from);
        } else if (mode === 'reply_all') {
            if (from) toSet.add(from);
            source.to_addresses?.forEach(a => { if (a.email && a.email !== userEmail) toSet.add(a.email); });
            source.cc_addresses?.forEach(a => { if (a.email && a.email !== userEmail) ccSet.add(a.email); });
        }
        // For forward, no default recipients

        const subjectBase = source.subject || thread.subject || '';
        const subject = mode === 'forward'
            ? (subjectBase?.startsWith('Fwd:') ? subjectBase : `Fwd: ${subjectBase || ''}`)
            : (subjectBase?.startsWith('Re:') ? subjectBase : `Re: ${subjectBase || ''}`);

        const newDraft: Draft = {
            id: `local_${Date.now()}`,
            type: 'email',
            status: 'draft',
            content: '',
            metadata: {
                subject: subject?.trim(),
                recipients: Array.from(toSet),
                cc: Array.from(ccSet),
                bcc: [],
                provider,
                replyToMessageId: source.provider_message_id,
            },
            isAIGenerated: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            userId: session?.user?.id || '',
            threadId: thread.id,
        };
        setThreadDrafts((prev) => [...prev, newDraft]);
        // Scroll to the newly added draft card on next animation frame
        setTimeout(() => {
            requestAnimationFrame(() => {
                const el = document.getElementById(`thread-draft-${newDraft.id}`);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        }, 50);
    };

    const handleReplyClick = () => {
        const srcId = thread.messages[thread.messages.length - 1].id;
        startEmailDraft('reply', srcId);
    };

    const handleArchive = () => {
        // TODO: Implement archive functionality
        console.log('Archive thread:', thread.id);
    };

    const handleSnooze = () => {
        // TODO: Implement snooze functionality
        console.log('Snooze thread:', thread.id);
    };

    const handleDelete = () => {
        // TODO: Implement delete functionality
        console.log('Delete thread:', thread.id);
    };

    // Sort messages by date (oldest first for threading) with defensive date parsing
    const sortedMessages = [...thread.messages].sort((a, b) => {
        const dateA = safeParseDate(a.date);
        const dateB = safeParseDate(b.date);

        // If either date is invalid, put it at the end
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;

        return dateA.getTime() - dateB.getTime();
    });

    return (
        <>
            <div className="space-y-4">
                <div className="border-b pb-2 mb-4">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                {thread.subject || 'No Subject'}
                            </h3>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleStarToggle}
                                title="Star"
                            >
                                <Star className={`h-4 w-4 ${isStarred ? 'fill-current text-yellow-500' : ''}`} />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleSnooze}
                                title="Snooze"
                            >
                                <Clock className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleDelete}
                                title="Delete"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        title="More actions"
                                    >
                                        <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={handleReplyClick}>
                                        <Reply className="h-4 w-4 mr-2" />
                                        Reply
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => startEmailDraft('reply_all', thread.messages[thread.messages.length - 1].id)}>
                                        <Reply className="h-4 w-4 mr-2" />
                                        Reply All
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => startEmailDraft('forward', thread.messages[thread.messages.length - 1].id)}>
                                        <Reply className="h-4 w-4 mr-2" />
                                        Forward
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleArchive}>
                                        <Archive className="h-4 w-4 mr-2" />
                                        Archive
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleDownload}>
                                        <Download className="h-4 w-4 mr-2" />
                                        Download
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => {
                                        try {
                                            const latest = thread.messages[thread.messages.length - 1];
                                            const parts: string[] = [];
                                            const seenEmails = new Set<string>();
                                            const addAddr = (addr?: { email?: string; name?: string } | null) => {
                                                if (!addr || !addr.email) return;
                                                const emailLower = addr.email.toLowerCase().trim();
                                                if (seenEmails.has(emailLower)) return;
                                                seenEmails.add(emailLower);
                                                const name = (addr.name || '').trim();
                                                if (name) {
                                                    parts.push(`${name} <${addr.email}>`);
                                                } else {
                                                    parts.push(addr.email);
                                                }
                                            };
                                            latest.to_addresses?.forEach(a => addAddr({ email: a.email || undefined, name: a.name || undefined }));
                                            latest.cc_addresses?.forEach(a => addAddr({ email: a.email || undefined, name: a.name || undefined }));
                                            const params = new URLSearchParams();
                                            params.set('tool', 'meetings');
                                            params.set('view', 'new');
                                            params.set('step', '1');
                                            if (latest.subject) params.set('title', latest.subject);
                                            params.set('participants', parts.join(', '));
                                            router.replace(`/dashboard?${params.toString()}`);
                                        } catch (err) {
                                            console.error('Failed to navigate to meeting poll creator:', err);
                                        }
                                    }}>
                                        <CalendarRange className="h-4 w-4 mr-2" />
                                        Create Meeting Poll
                                    </DropdownMenuItem>

                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </div>

                {sortedMessages.map((message) => (
                    <EmailThreadCard
                        key={message.id}
                        email={message}
                        isSelected={selectedMessageId === message.id}
                        onSelect={onSelectMessage}
                        onReply={(email) => startEmailDraft('reply', email.id)}
                        onReplyAll={(email) => startEmailDraft('reply_all', email.id)}
                        onForward={(email) => startEmailDraft('forward', email.id)}
                    />
                ))}

                {threadDrafts.map((d) => {
                    const src = thread.messages.find(m => m.provider_message_id === d.metadata.replyToMessageId) || thread.messages[thread.messages.length - 1];
                    const quotedHeader = `From: ${src.from_address?.name || src.from_address?.email || ''}\nSent: ${new Date(src.date).toLocaleString()}\nTo: ${src.to_addresses?.map(a => a.name || a.email).join(', ') || 'No recipients'}\nSubject: ${src.subject || ''}`;
                    const quotedBody = src.body_html || src.body_text || '';
                    const quotedIsHtml = !!src.body_html;
                    return (
                        <EmailThreadDraft
                            key={d.id}
                            initialDraft={d}
                            quotedHeader={quotedHeader}
                            quotedBody={quotedBody}
                            quotedIsHtml={quotedIsHtml}
                            onClose={() => setThreadDrafts((prev) => prev.filter((x) => x.id !== d.id))}
                        />
                    );
                })}
            </div>

        </>
    );
};

export default EmailThread;
