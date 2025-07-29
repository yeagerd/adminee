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
        trackingPatterns: [/1Z[0-9A-Z]{16}/, /TBA[0-9]{10}/, /[0-9]{10,}/]
    },
    ups: {
        domains: ['ups.com', 'ups.ca'],
        keywords: ['ups', 'united parcel service', 'tracking'],
        trackingPatterns: [/1Z[0-9A-Z]{16}/, /[0-9]{9}/, /[0-9]{10}/, /[0-9]{12}/]
    },
    fedex: {
        domains: ['fedex.com', 'fedex.ca'],
        keywords: ['fedex', 'federal express', 'tracking'],
        trackingPatterns: [/[0-9]{12}/, /[0-9]{15}/, /[0-9]{22}/]
    },
    usps: {
        domains: ['usps.com'],
        keywords: ['usps', 'united states postal service', 'tracking'],
        trackingPatterns: [/[0-9]{20}/, /[0-9]{22}/, /[0-9]{13}/, /[0-9]{15}/]
    },
    dhl: {
        domains: ['dhl.com', 'dhl.de'],
        keywords: ['dhl', 'tracking'],
        trackingPatterns: [/[0-9]{10}/, /[0-9]{11}/, /[0-9]{12}/, /[0-9]{13}/]
    }
};

// Generic tracking number patterns
const GENERIC_TRACKING_PATTERNS = [
    /[0-9]{10,}/, // 10+ digits
    /[A-Z]{2}[0-9]{9}[A-Z]{2}/, // Generic format
    /[0-9]{3}-[0-9]{3}-[0-9]{4}/, // XXX-XXX-XXXX format
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

        // Extract tracking numbers
        const allText = `${subject} ${body}`;
        const foundTrackingNumbers = new Set<string>();

        // Check carrier-specific patterns first
        if (detectedCarrier) {
            const patterns = CARRIER_PATTERNS[detectedCarrier as keyof typeof CARRIER_PATTERNS];
            for (const pattern of patterns.trackingPatterns) {
                const matches = allText.match(pattern);
                if (matches) {
                    matches.forEach(match => foundTrackingNumbers.add(match));
                }
            }
        }

        // Check generic patterns
        for (const pattern of GENERIC_TRACKING_PATTERNS) {
            const matches = allText.match(pattern);
            if (matches) {
                matches.forEach(match => foundTrackingNumbers.add(match));
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