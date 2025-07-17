import { EmailMessage } from '@/types/office-service';
import React from 'react';

const AISummary: React.FC<{ email: EmailMessage }> = ({ email }) => {
    // Placeholder for AI summary
    return (
        <div className="italic text-muted-foreground text-xs">
            [AI summary coming soon]
        </div>
    );
};

export default AISummary; 