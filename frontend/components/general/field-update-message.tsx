import React from 'react';

// Component for showing field update messages
interface FieldUpdateMessageProps {
    existingPackage: unknown; // Using 'unknown' for flexibility across different package types
    currentValue: string;
    originalValue?: string;
}

const FieldUpdateMessage: React.FC<FieldUpdateMessageProps> = ({
    existingPackage,
    currentValue,
    originalValue
}) => {
    if (!existingPackage || !currentValue) {
        return null;
    }

    const message = originalValue ?
        (currentValue !== originalValue ? `Will be updated from: ${originalValue}` : null) :
        `Adding value: ${currentValue}`;

    if (!message) {
        return null;
    }

    return (
        <div className="text-xs text-blue-600 ml-28">
            {message}
        </div>
    );
};

export default FieldUpdateMessage; 