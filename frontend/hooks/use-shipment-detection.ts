import { EmailMessage } from '@/types/office-service';
import { useMemo } from 'react';

export interface ShipmentDetectionResult {
    isShipmentEmail: boolean;
    detectedCarrier?: string;
    trackingNumbers: Array<{
        trackingNumber: string;
        carrier: string;
        confidence: number;
    }>;
    confidence: number;
    detectedFrom: 'sender' | 'subject' | 'body' | 'multiple';
}

// Carrier-specific tracking number patterns
const TRACKING_PATTERNS = {
    ups: {
        primary: /1Z[0-9A-Z]{15,}/g, // UPS 1Z format
        alternate: [/[0-9]{9}/g, /[0-9]{10}/g, /[0-9]{12}/g] // UPS numeric formats (excluding 26-digit to avoid USPS conflict)
    },
    fedex: {
        primary: /[0-9]{12}/g, // FedEx 12-digit
        alternate: [/[0-9]{15}/g, /[0-9]{22}/g] // FedEx alternate formats
    },
    usps: {
        primary: /[0-9]{20}/g, // USPS 20-digit
        alternate: [/[0-9]{22}/g, /[0-9]{13}/g, /[0-9]{15}/g, /[0-9]{26}/g] // USPS alternate formats including 26-digit
    },
    dhl: {
        primary: /[0-9]{10}/g, // DHL 10-digit
        alternate: [/[0-9]{11}/g, /[0-9]{12}/g, /[0-9]{13}/g] // DHL alternate formats
    },
    amazon: {
        primary: /TBA[0-9]{10}/g, // Amazon TBA format
        alternate: [/[0-9]{10,}/g] // Generic numeric fallback
    }
};

// Generic tracking patterns for fallback
const GENERIC_TRACKING_PATTERNS = [
    /[0-9]{10,}/g, // 10+ digits
    /[A-Z]{2}[0-9]{9}[A-Z]{2}/g, // Generic alphanumeric format
    /[0-9]{3}-[0-9]{3}-[0-9]{4}/g, // XXX-XXX-XXXX format
];

// Shipment-related keywords
const SHIPMENT_KEYWORDS = [
    'shipment', 'package', 'order', 'delivery', 'tracking',
    'shipped', 'out for delivery', 'arriving', 'on the way'
];

// Amazon-specific domains for special casing
const AMAZON_DOMAINS = [
    'amazon.com', 'amazon.ca', 'amazon.co.uk', 'amazon.de',
    'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp'
];

/**
 * Extracts tracking numbers from text, prioritizing carrier-specific patterns
 */
function extractTrackingNumbers(text: string, body: string = ""): Array<{ trackingNumber: string; carrier: string; confidence: number }> {
    const matches = new Map<string, {
        trackingNumber: string;
        carrier: string;
        confidence: number;
        start: number;
        end: number;
        priority: number
    }>();

    // Helper function to add match with deduplication
    const addMatch = (trackingNumber: string, carrier: string, confidence: number, start: number, end: number, priority: number) => {
        const existing = matches.get(trackingNumber);

        // Check if this number overlaps with any existing number in position
        const hasPositionalOverlap = Array.from(matches.values()).some(match =>
            !(end <= match.start || start >= match.end)
        );

        // If there's positional overlap, prioritize longer matches
        if (hasPositionalOverlap) {
            const overlappingMatch = Array.from(matches.values()).find(match =>
                !(end <= match.start || start >= match.end)
            );

            if (overlappingMatch) {
                // If this match is longer than the overlapping match, remove the shorter one
                if (trackingNumber.length > overlappingMatch.trackingNumber.length) {
                    // Remove only the overlapping match with lower length
                    matches.delete(overlappingMatch.trackingNumber);
                } else if (trackingNumber.length < overlappingMatch.trackingNumber.length) {
                    // If this match is shorter, don't add it
                    return;
                } else {
                    // Same length, use confidence as tiebreaker
                    if (confidence <= overlappingMatch.confidence) {
                        return;
                    } else {
                        // Remove only the lower confidence overlapping match
                        matches.delete(overlappingMatch.trackingNumber);
                    }
                }
            }
        }

        // Only add if no existing match or if this match has higher confidence
        if (!existing || confidence > existing.confidence) {
            matches.set(trackingNumber, {
                trackingNumber,
                carrier,
                confidence,
                start,
                end,
                priority
            });
        }
    };

    // Collect all carrier-specific matches with priority
    for (const [carrier, patterns] of Object.entries(TRACKING_PATTERNS)) {
        // Primary patterns get highest confidence
        const primaryMatches = text.matchAll(patterns.primary);
        for (const match of primaryMatches) {
            addMatch(match[0], carrier, 0.9, match.index!, match.index! + match[0].length, 1);
        }

        // Alternate patterns get medium confidence
        for (const pattern of patterns.alternate) {
            const alternateMatches = text.matchAll(pattern);
            for (const match of alternateMatches) {
                addMatch(match[0], carrier, 0.7, match.index!, match.index! + match[0].length, 2);
            }
        }
    }

    // Add generic patterns with lowest priority and confidence
    for (const pattern of GENERIC_TRACKING_PATTERNS) {
        const genericMatches = text.matchAll(pattern);
        for (const match of genericMatches) {
            addMatch(match[0], 'unknown', 0.4, match.index!, match.index! + match[0].length, 3);
        }
    }

    // Special handling for 26-digit patterns that could be UPS Mail Innovations or USPS
    const twentySixDigitPattern = /[0-9]{26}/g;
    const twentySixDigitMatches = text.matchAll(twentySixDigitPattern);
    for (const match of twentySixDigitMatches) {
        const bodyLower = body.toLowerCase();
        let carrier = 'usps'; // Default to USPS
        if (bodyLower.includes('ups.com') || bodyLower.includes('united parcel service')) {
            carrier = 'ups';
        }
        addMatch(match[0], carrier, 0.7, match.index!, match.index! + match[0].length, 2);
    }

    // Only deduplicate by tracking number value and confidence
    const selected: Array<{ trackingNumber: string; carrier: string; confidence: number; start: number; end: number }> = [];
    const deduplicatedMatches = Array.from(matches.values());

    for (const match of deduplicatedMatches) {
        // Check if this match overlaps with any already selected match
        const hasPositionalOverlap = selected.some(selectedMatch =>
            !(match.end <= selectedMatch.start || match.start >= selectedMatch.end)
        );

        if (!hasPositionalOverlap) {
            selected.push({
                trackingNumber: match.trackingNumber,
                carrier: match.carrier,
                confidence: match.confidence,
                start: match.start,
                end: match.end
            });
        }
    }

    // Return only the tracking number objects without position data
    return selected.map(({ trackingNumber, carrier, confidence }) => ({
        trackingNumber,
        carrier,
        confidence
    }));
}

/**
 * Checks if email is from Amazon domain and contains shipment keywords
 */
function isAmazonShipment(senderEmail: string, subject: string, body: string): boolean {
    // Check sender domain
    const address = senderEmail.split('@')[0]?.toLowerCase();
    const domainParts = senderEmail.split('@')[1]?.toLowerCase().split('.');
    if (domainParts.includes('amazon')) {
        // Check if shipping is in the address part
        if (address?.includes('shipment')) {
            return true;
        }
    }
    // Check for Amazon sender addresses/domains in the body (for forwarded emails)
    const amazonSenderRegex = /[\w.-]*shipment[\w.-]*@.*amazon\.[a-z.]+/gi;
    if (amazonSenderRegex.test(body)) {
        return true;
    }

    return false;
}

export const useShipmentDetection = (email: EmailMessage): ShipmentDetectionResult => {
    return useMemo(() => {
        const result: ShipmentDetectionResult = {
            isShipmentEmail: false,
            trackingNumbers: [],
            confidence: 0,
            detectedFrom: 'sender'
        };

        const senderEmail = email.from_address?.email?.toLowerCase() || '';
        const subject = email.subject?.toLowerCase() || '';
        const body = (email.body_text || email.body_html || '').toLowerCase();
        const allText = `${subject} ${body}`;

        // Extract tracking numbers from original case text
        const originalSubject = email.subject || '';
        const originalBody = email.body_text || email.body_html || '';
        const originalText = `${originalSubject} ${originalBody}`;

        result.trackingNumbers = extractTrackingNumbers(originalText, originalBody);

        // Set as shipment email if tracking numbers are found
        if (result.trackingNumbers.length > 0) {
            result.isShipmentEmail = true;
            result.confidence += 0.3;

            // Set detected carrier based on the highest confidence tracking number
            const bestTracking = result.trackingNumbers.reduce((best, current) =>
                current.confidence > best.confidence ? current : best
            );
            result.detectedCarrier = bestTracking.carrier;
        }

        // Special case: Amazon shipments - boost confidence for Amazon tracking numbers
        if (isAmazonShipment(senderEmail, subject, body)) {
            result.isShipmentEmail = true;
            result.detectedCarrier = 'amazon';
            result.confidence = 0.8;
            result.detectedFrom = 'sender';

            // Boost confidence for Amazon tracking numbers
            result.trackingNumbers = result.trackingNumbers.map(tracking => {
                if (tracking.carrier === 'amazon') {
                    return { ...tracking, confidence: Math.min(tracking.confidence + 0.1, 1.0) };
                }
                return tracking;
            });
        }

        // Cap confidence at 1.0
        result.confidence = Math.min(result.confidence, 1.0);

        return result;
    }, [email]);
}; 