import { EmailMessage } from '@/types/office-service';
import React from 'react';
import EmailThreadCard from './email-thread-card';

interface EmailThreadProps {
    emails: EmailMessage[];
    threadId: string;
}

const EmailThread: React.FC<EmailThreadProps> = ({ emails, threadId }) => {
    // Sort emails by date (oldest first for threading)
    const sortedEmails = [...emails].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    return (
        <div className="space-y-4">
            {sortedEmails.map((email, index) => (
                <EmailThreadCard
                    key={email.id}
                    email={email}
                    isFirstInThread={index === 0}
                    threadId={threadId}
                />
            ))}
        </div>
    );
};

export default EmailThread;
