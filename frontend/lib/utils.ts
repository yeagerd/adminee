import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * Format UTC date string to local time for display
 * @param utcDateString - ISO date string in UTC
 * @param options - Intl.DateTimeFormat options
 */
export function formatUtcToLocal(
    utcDateString: string,
    options: Intl.DateTimeFormatOptions = {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    }
): string {
    try {
        const date = new Date(utcDateString);
        return date.toLocaleTimeString([], options);
    } catch (error) {
        console.error("Failed to format date:", error);
        return utcDateString; // fallback to original string
    }
}

/**
 * Get user's timezone
 */
export function getUserTimezone(): string {
    try {
        return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (error) {
        console.error("Failed to detect timezone:", error);
        return "UTC";
    }
}

/**
 * Format a time range from UTC to local timezone
 * @param startTimeUtc - Start time in UTC ISO string
 * @param endTimeUtc - End time in UTC ISO string
 */
export function formatTimeRange(startTimeUtc: string, endTimeUtc: string): string {
    const startLocal = formatUtcToLocal(startTimeUtc);
    const endLocal = formatUtcToLocal(endTimeUtc, { hour: "2-digit", minute: "2-digit", hour12: true });
    return `${startLocal} to ${endLocal}`;
}

/**
 * Parse and format calendar event times from chat responses
 * This function looks for time patterns in chat text and converts them to local time
 */
export function formatCalendarTimesInText(text: string): string {
    // Pattern to match "Time: HH:MM AM/PM to HH:MM AM/PM" 
    const timePattern = /Time:\s*(\d{1,2}:\d{2}\s*(?:AM|PM))\s*to\s*(\d{1,2}:\d{2}\s*(?:AM|PM))/gi;

    return text.replace(timePattern, (match) => {
        // Since the backend now handles timezone conversion, we can return the formatted times as-is
        // The chat service already converts UTC to local time before sending the response
        return match;
    });
}

/**
 * Safely parse a date string and return a Date object or null if invalid
 * @param dateString - The date string to parse
 * @returns Date object if valid, null if invalid
 */
export function safeParseDate(dateString: string | null | undefined): Date | null {
    if (!dateString || typeof dateString !== 'string') {
        return null;
    }

    try {
        const date = new Date(dateString);
        // Check if the date is valid (not NaN)
        return isNaN(date.getTime()) ? null : date;
    } catch (error) {
        console.warn('Failed to parse date:', dateString, error);
        return null;
    }
}

/**
 * Safely parse a date string and return an ISO date string (YYYY-MM-DD) or empty string if invalid
 * @param dateString - The date string to parse
 * @returns ISO date string if valid, empty string if invalid
 */
export function safeParseDateToISOString(dateString: string | null | undefined): string {
    const date = safeParseDate(dateString);
    return date ? date.toISOString().split('T')[0] : '';
}

/**
 * Safely parse a date string and return a localized date string or empty string if invalid
 * @param dateString - The date string to parse
 * @param options - Intl.DateTimeFormat options
 * @returns Localized date string if valid, empty string if invalid
 */
export function safeParseDateToLocaleString(
    dateString: string | null | undefined,
    options: Intl.DateTimeFormatOptions = {}
): string {
    const date = safeParseDate(dateString);
    return date ? date.toLocaleDateString([], options) : '';
}
