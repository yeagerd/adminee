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
        alternate: [/[0-9]{9}/g, /[0-9]{10}/g, /[0-9]{12}/g, /[0-9]{26}/g] // UPS numeric formats including 26-digit
    },
    fedex: {
        primary: /[0-9]{12}/g, // FedEx 12-digit
        alternate: [/[0-9]{15}/g, /[0-9]{22}/g] // FedEx alternate formats
    },
    usps: {
        primary: /[0-9]{20}/g, // USPS 20-digit
        alternate: [/[0-9]{22}/g, /[0-9]{13}/g, /[0-9]{15}/g] // USPS alternate formats
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
function extractTrackingNumbers(text: string): Array<{ trackingNumber: string; carrier: string; confidence: number }> {
    const matches: Array<{
        trackingNumber: string;
        carrier: string;
        confidence: number;
        start: number;
        end: number;
        priority: number
    }> = [];

    // Collect all carrier-specific matches with priority
    for (const [carrier, patterns] of Object.entries(TRACKING_PATTERNS)) {
        // Primary patterns get highest confidence
        const primaryMatches = text.matchAll(patterns.primary);
        for (const match of primaryMatches) {
            matches.push({
                trackingNumber: match[0],
                carrier,
                confidence: 0.9, // High confidence for primary patterns
                start: match.index!,
                end: match.index! + match[0].length,
                priority: 1
            });
        }

        // Alternate patterns get medium confidence
        for (const pattern of patterns.alternate) {
            const alternateMatches = text.matchAll(pattern);
            for (const match of alternateMatches) {
                matches.push({
                    trackingNumber: match[0],
                    carrier,
                    confidence: 0.7, // Medium confidence for alternate patterns
                    start: match.index!,
                    end: match.index! + match[0].length,
                    priority: 2
                });
            }
        }
    }

    // Add generic patterns with lowest priority and confidence
    for (const pattern of GENERIC_TRACKING_PATTERNS) {
        const genericMatches = text.matchAll(pattern);
        for (const match of genericMatches) {
            matches.push({
                trackingNumber: match[0],
                carrier: 'generic',
                confidence: 0.4, // Low confidence for generic patterns
                start: match.index!,
                end: match.index! + match[0].length,
                priority: 3
            });
        }
    }

    // Sort by priority (lower number = higher priority), then by confidence, then by length
    matches.sort((a, b) => {
        if (a.priority !== b.priority) {
            return a.priority - b.priority;
        }
        if (a.confidence !== b.confidence) {
            return b.confidence - a.confidence; // Higher confidence first
        }
        return b.trackingNumber.length - a.trackingNumber.length;
    });

    // Deduplicate by tracking number, keeping highest confidence match
    const trackingNumberMap = new Map<string, { trackingNumber: string; carrier: string; confidence: number; start: number; end: number }>();

    for (const match of matches) {
        const existing = trackingNumberMap.get(match.trackingNumber);
        if (!existing || match.confidence > existing.confidence) {
            trackingNumberMap.set(match.trackingNumber, match);
        }
    }

    // Select non-overlapping matches from deduplicated results
    const selected: Array<{ trackingNumber: string; carrier: string; confidence: number; start: number; end: number }> = [];
    const deduplicatedMatches = Array.from(trackingNumberMap.values());

    for (const match of deduplicatedMatches) {
        const overlaps = selected.some(selected =>
            !(match.end <= selected.start || match.start >= selected.end)
        );

        if (!overlaps) {
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

    return selected;
}

/**
 * Checks if email is from Amazon domain and contains shipment keywords
 */
function isAmazonShipment(senderEmail: string, subject: string, body: string): boolean {
    const domain = senderEmail.split('@')[1]?.toLowerCase();
    if (!domain || !AMAZON_DOMAINS.some(amazonDomain => domain.includes(amazonDomain))) {
        return false;
    }

    const allText = `${subject} ${body}`.toLowerCase();
    return SHIPMENT_KEYWORDS.some(keyword => allText.includes(keyword));
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

        result.trackingNumbers = extractTrackingNumbers(originalText);

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