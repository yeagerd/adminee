import { EmailMessage } from '@/types/office-service';
import { useMemo } from 'react';

export interface ShipmentDetectionResult {
    isShipmentEmail: boolean;
    detectedCarrier?: string;
    trackingNumbers: string[];
    confidence: number;
    detectedFrom: 'sender' | 'subject' | 'body' | 'multiple';
}

// Common carrier domains and patterns
const CARRIER_PATTERNS = {
    amazon: {
        domains: ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp'],
        keywords: ['shipment', 'package', 'order', 'delivery', 'tracking'],
        trackingPatterns: [/1Z[0-9A-Z]{15,}/g, /TBA[0-9]{10}/g, /\b[0-9]{10,}\b/g]
    },
    ups: {
        domains: ['ups.com', 'ups.ca'],
        keywords: ['ups', 'united parcel service', 'tracking'],
        trackingPatterns: [/1Z[0-9A-Z]{15,}/g, /[0-9]{9}/g, /[0-9]{10}/g, /[0-9]{12}/g]
    },
    fedex: {
        domains: ['fedex.com', 'fedex.ca'],
        keywords: ['fedex', 'federal express', 'tracking'],
        trackingPatterns: [/[0-9]{12}/g, /[0-9]{15}/g, /[0-9]{22}/g]
    },
    usps: {
        domains: ['usps.com'],
        keywords: ['usps', 'united states postal service', 'tracking'],
        trackingPatterns: [/[0-9]{20}/g, /[0-9]{22}/g, /[0-9]{13}/g, /[0-9]{15}/g]
    },
    dhl: {
        domains: ['dhl.com', 'dhl.de'],
        keywords: ['dhl', 'tracking'],
        trackingPatterns: [/[0-9]{10}/g, /[0-9]{11}/g, /[0-9]{12}/g, /[0-9]{13}/g]
    }
};

// Generic tracking number patterns
const GENERIC_TRACKING_PATTERNS = [
    /[0-9]{10,}/g, // 10+ digits
    /[A-Z]{2}[0-9]{9}[A-Z]{2}/g, // Generic format
    /[0-9]{3}-[0-9]{3}-[0-9]{4}/g, // XXX-XXX-XXXX format
];

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

        // Check sender domain
        let detectedCarrier: string | undefined;
        for (const [carrier, patterns] of Object.entries(CARRIER_PATTERNS)) {
            if (patterns.domains.some(domain => senderEmail.includes(domain))) {
                detectedCarrier = carrier;
                result.isShipmentEmail = true;
                result.confidence += 0.4;
                break;
            }
        }

        // Check subject line for shipment keywords
        const shipmentKeywords = ['shipment', 'package', 'order', 'delivery', 'tracking', 'shipped', 'out for delivery'];
        const subjectHasKeywords = shipmentKeywords.some(keyword => subject.includes(keyword));
        if (subjectHasKeywords) {
            result.isShipmentEmail = true;
            result.confidence += 0.3;
            if (!result.detectedFrom || result.detectedFrom === 'sender') {
                result.detectedFrom = 'subject';
            } else {
                result.detectedFrom = 'multiple';
            }
        }

        // Check body for shipment keywords
        const bodyHasKeywords = shipmentKeywords.some(keyword => body.includes(keyword));
        if (bodyHasKeywords) {
            result.isShipmentEmail = true;
            result.confidence += 0.2;
            if (!result.detectedFrom || result.detectedFrom === 'sender') {
                result.detectedFrom = 'body';
            } else {
                result.detectedFrom = 'multiple';
            }
        }

        // Extract tracking numbers (use original case for regex matching)
        const originalSubject = email.subject || '';
        const originalBody = email.body_text || email.body_html || '';
        const allText = `${originalSubject} ${originalBody}`;
        const foundTrackingNumbers = new Set<string>();

        // Collect all possible matches with their positions
        const allMatches: Array<{ match: string; start: number; end: number }> = [];

        // Check carrier-specific patterns first
        if (detectedCarrier) {
            const patterns = CARRIER_PATTERNS[detectedCarrier as keyof typeof CARRIER_PATTERNS];
            for (const pattern of patterns.trackingPatterns) {
                const matches = allText.matchAll(pattern);
                for (const match of matches) {
                    allMatches.push({
                        match: match[0],
                        start: match.index!,
                        end: match.index! + match[0].length
                    });
                }
            }
        }

        // Check generic patterns if no carrier-specific patterns were found
        if (allMatches.length === 0) {
            for (const pattern of GENERIC_TRACKING_PATTERNS) {
                const matches = allText.matchAll(pattern);
                for (const match of matches) {
                    allMatches.push({
                        match: match[0],
                        start: match.index!,
                        end: match.index! + match[0].length
                    });
                }
            }
        }

        // Sort matches by length (longest first) and remove overlapping matches
        allMatches.sort((a, b) => b.match.length - a.match.length);

        // Track selected matches with their positions to avoid re-finding with indexOf
        const selectedMatches: Array<{ match: string; start: number; end: number }> = [];

        for (const match of allMatches) {
            // Check if this match overlaps with any already selected match
            const overlaps = selectedMatches.some(selected => {
                return !(match.end <= selected.start || match.start >= selected.end);
            });

            if (!overlaps) {
                foundTrackingNumbers.add(match.match);
                selectedMatches.push(match);
            }
        }

        result.trackingNumbers = Array.from(foundTrackingNumbers);

        // Boost confidence if tracking numbers found
        if (result.trackingNumbers.length > 0) {
            result.confidence += 0.3;
        }

        // Cap confidence at 1.0
        result.confidence = Math.min(result.confidence, 1.0);

        // Set carrier if detected
        if (detectedCarrier) {
            result.detectedCarrier = detectedCarrier;
        }

        return result;
    }, [email]);
}; 