import { EmailMessage } from '@/types/office-service';
import React from 'react';
import AISummary from './ai-summary';

interface EmailCardProps {
    email: EmailMessage;
}

const EmailCard: React.FC<EmailCardProps> = ({ email }) => {
    // Placeholder logic for flags (customize as needed)
    // const isHighPriority = email.labels?.includes('important');
    // const hasCalendarEvent = false; // Not available in EmailMessage
    // const hasPackageTracking = false; // Not available in EmailMessage

    return (
        <div className="bg-white dark:bg-muted rounded-lg shadow p-4 mb-2 border">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {/* {isHighPriority && <span className="text-red-500 font-bold">! </span>} */}
                    <span className="font-medium">{email.subject || '(No subject)'}</span>
                </div>
                <span className="text-xs text-muted-foreground">{new Date(email.date).toLocaleString()}</span>
            </div>
            <div className="mt-1 text-sm text-muted-foreground">From: {email.from_address?.name || email.from_address?.email || 'Unknown'}</div>
            <div className="mt-1 text-sm text-muted-foreground">To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}</div>
            {/* <div className="mt-2">
                {hasCalendarEvent && <span className="mr-2 px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">Calendar</span>}
                {hasPackageTracking && <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">Package</span>}
            </div> */}
            <div className="mt-2">
                <AISummary email={email} />
            </div>
            <div className="mt-2 flex gap-2">
                <button className="text-primary underline text-sm">Reply</button>
                {/* This should open the draft pane with a reply draft */}
            </div>
        </div>
    );
};

export default EmailCard; 