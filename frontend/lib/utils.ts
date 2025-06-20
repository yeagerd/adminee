import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

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
  
  return text.replace(timePattern, (match, startTime, endTime) => {
    // For now, just return the original match - this would need more sophisticated parsing
    // to convert from UTC to local time if the backend is sending UTC times
    return match;
  });
}
