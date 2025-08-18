import { EmailMessage } from "@/types/api/office";
import { renderHook } from '@testing-library/react';
import { useShipmentDetection } from './use-shipment-detection';

describe('useShipmentDetection', () => {
    it('should detect multiple tracking numbers in the same email', () => {
        const email: EmailMessage = {
            id: '1',
            subject: 'Your shipment with tracking numbers 1Z999AA1234567890 and 1Z999AA9876543210',
            body_text: 'Your package 1Z999AA1111111111 has been shipped. Also check 1Z999AA2222222222.',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect multiple tracking numbers
        expect(result.current.trackingNumbers.length).toBeGreaterThan(1);
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA9876543210');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1111111111');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA2222222222');
    });

    it('should detect multiple generic tracking numbers', () => {
        const email: EmailMessage = {
            id: '2',
            subject: 'Multiple packages',
            body_text: 'Package 1: 12345678901234567890, Package 2: 98765432109876543210',
            from_address: {
                name: 'USPS',
                email: 'tracking@usps.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect multiple tracking numbers
        expect(result.current.trackingNumbers.length).toBeGreaterThan(1);
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('12345678901234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('98765432109876543210');
    });

    it('should detect shipment email from Amazon domain', () => {
        const email: EmailMessage = {
            id: '3',
            subject: 'Your Amazon order has shipped',
            body_text: 'Your order has been shipped with tracking number 1Z999AA1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('amazon');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.confidence).toBeGreaterThan(0);
    });

    it('should correctly handle duplicate tracking numbers in different positions', () => {
        const email: EmailMessage = {
            id: '4',
            subject: 'Your shipment with tracking number 1Z999AA1234567890',
            body_text: 'Your package 1Z999AA1234567890 has been shipped. Please track your package 1Z999AA1234567890 for updates.',
            from_address: {
                name: 'UPS',
                email: 'tracking@ups.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect both the full tracking number and the substring (DHL pattern)
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');
        // Should have exactly 2 tracking numbers
        expect(result.current.trackingNumbers).toHaveLength(2);
    });

    it('should detect UPS 1Z tracking numbers even when other order numbers are present', () => {
        const email: EmailMessage = {
            id: '5',
            subject: 'Your Amazon order has shipped',
            body_text: 'Your order #1234567890 has been shipped with UPS tracking number 1Z999AA1234567890. Order details: 9876543210',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect the UPS tracking number even with other numbers present
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('amazon');

        // Should also detect other valid tracking numbers
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('9876543210');
    });

    it('should prioritize UPS 1Z patterns over generic patterns when overlapping', () => {
        const email: EmailMessage = {
            id: '6',
            subject: 'Shipment confirmation',
            body_text: 'Your package with tracking 1Z999AA1234567890 has been shipped. Reference: 999AA1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect the full UPS tracking number, not just the partial match
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).not.toContain('999AA1234567890');
    });

    it('should handle edge case where UPS 1Z number conflicts with order number pattern', () => {
        const email: EmailMessage = {
            id: '7',
            subject: 'Order shipped',
            body_text: 'Order #1Z999AA1234567890 has been shipped. Your tracking number is 1Z999AA1234567890. Order reference: 999AA1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect the UPS tracking number correctly
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');

        // Should not detect the partial match as a separate tracking number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).not.toContain('999AA1234567890');

        // Should only detect the UPS number once (not as both order number and tracking number)
        const upsMatches = result.current.trackingNumbers.filter(num => num.trackingNumber === '1Z999AA1234567890');
        expect(upsMatches).toHaveLength(1);
    });

    it('should detect UPS 1Z numbers when they appear in different contexts', () => {
        const email: EmailMessage = {
            id: '8',
            subject: 'Multiple shipments',
            body_text: 'Package 1: 1Z999AA1111111111, Package 2: 1Z999AA2222222222, Order: 1234567890, Reference: 9876543210',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect both UPS tracking numbers
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1111111111');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA2222222222');

        // Should also detect other valid numbers
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('9876543210');

        // Should detect exactly 4 tracking numbers
        expect(result.current.trackingNumbers).toHaveLength(4);
    });

    it('should handle the specific case where UPS 1Z is missed due to pattern priority', () => {
        const email: EmailMessage = {
            id: '9',
            subject: 'Order confirmation',
            body_text: 'Your order #12345678901234567890 has been shipped via UPS. Tracking: 1Z999AA1234567890. Order reference: 999AA1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // This test specifically checks for the issue mentioned by the user
        // The UPS 1Z number should be detected even when there's a conflicting 20-digit number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');

        // Should also detect the long order number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('12345678901234567890');

        // Should not detect the partial match (999AA1234567890) because it's part of the longer UPS number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).not.toContain('999AA1234567890');

        // Should also detect the reference number 1234567890 as a separate tracking number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');

        // Should detect exactly 3 tracking numbers (UPS number, long order number, and reference number)
        expect(result.current.trackingNumbers).toHaveLength(3);
    });

    it('should debug pattern matching behavior with overlapping patterns', () => {
        const email: EmailMessage = {
            id: '10',
            subject: 'Debug test',
            body_text: 'Tracking: 1Z999AA1234567890, Order: 999AA1234567890, Reference: 1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect the UPS number (longer pattern takes priority)
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');

        // Should NOT detect the order number because it's part of the longer UPS number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).not.toContain('999AA1234567890');

        // Should detect the reference number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');

        // Should detect exactly 2 tracking numbers
        expect(result.current.trackingNumbers).toHaveLength(2);
    });

    it('should detect UPS 1Z tracking numbers in Amazon emails (original issue)', () => {
        const email: EmailMessage = {
            id: '11',
            subject: 'Your Amazon order has shipped',
            body_text: 'Your order has been shipped via UPS. Tracking number: 1Z999AA1234567890. Order #1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // This test verifies the original issue is fixed
        // UPS 1Z tracking numbers should be detected in Amazon emails
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');
        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('amazon');

        // Should also detect the order number
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1234567890');

        // Should detect exactly 2 tracking numbers
        expect(result.current.trackingNumbers).toHaveLength(2);
    });

    it('should prioritize carrier-specific patterns to avoid multiple package conflicts', () => {
        const email: EmailMessage = {
            id: '12',
            subject: 'Shipment confirmation',
            body_text: 'Your package with UPS tracking 1Z999AA1234567890 has been shipped. Order reference: 92419903029108543480127535',
            from_address: {
                name: 'Amazon',
                email: 'shipment-tracking@amazon.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };

        const { result } = renderHook(() => useShipmentDetection(email));

        // Should detect the UPS tracking number (carrier-specific pattern)
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('1Z999AA1234567890');

        // The detection logic will still detect the 20-digit number, but the modal logic
        // should prioritize the UPS number to avoid conflicts
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('92419903029108543480127535');

        // Should detect exactly 2 tracking numbers
        expect(result.current.trackingNumbers).toHaveLength(2);

        // The modal logic should prioritize the UPS number (first in the array due to sorting)
        expect(result.current.trackingNumbers[0].trackingNumber).toBe('1Z999AA1234567890');
    });

    it('should detect Amazon shipment in forwarded email (Amazon sender in body)', () => {
        const email: EmailMessage = {
            id: 'forwarded1',
            subject: 'Fwd: Your Amazon order has shipped',
            body_text: `
            ---------- Forwarded message ----------\nFrom: Amazon Shipping <shipment-tracking@amazon.com>\nSubject: Your Amazon order has shipped\n\nYour package TBA1234567890 has shipped!\nTrack it at https://www.amazon.com/track/TBA1234567890\n`,
            from_address: {
                name: 'A Friend',
                email: 'friend@example.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };
        const { result } = renderHook(() => useShipmentDetection(email));
        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('amazon');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('TBA1234567890');
        expect(result.current.confidence).toBeGreaterThanOrEqual(0.8);
    });

    it('should correctly detect 26-digit tracking numbers as USPS by default', () => {
        const email: EmailMessage = {
            id: '26digit-usps',
            subject: 'Your USPS package has shipped',
            body_text: 'Your package with tracking number 12345678901234567890123456 has been shipped.',
            from_address: {
                name: 'USPS',
                email: 'tracking@usps.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };
        const { result } = renderHook(() => useShipmentDetection(email));
        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('usps');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('12345678901234567890123456');
        // Should be detected as USPS
        const uspsTracking = result.current.trackingNumbers.find(t => t.trackingNumber === '12345678901234567890123456');
        expect(uspsTracking?.carrier).toBe('usps');
    });

    it('should detect 26-digit tracking numbers as UPS when UPS context is present', () => {
        const email: EmailMessage = {
            id: '26digit-ups',
            subject: 'Your UPS Mail Innovations package has shipped',
            body_text: 'Your package with tracking number 12345678901234567890123456 has been shipped via UPS Mail Innovations. Track at https://www.ups.com/track?tracknum=12345678901234567890123456',
            from_address: {
                name: 'UPS',
                email: 'tracking@ups.com'
            },
            to_addresses: [],
            cc_addresses: [],
            bcc_addresses: [],
            date: new Date().toISOString(),
            labels: [],
            is_read: false,
            has_attachments: false,
            provider: 'google',
            provider_message_id: 'test-message-id',
            account_email: 'test@example.com'
        };
        const { result } = renderHook(() => useShipmentDetection(email));
        expect(result.current.isShipmentEmail).toBe(true);
        expect(result.current.detectedCarrier).toBe('ups');
        expect(result.current.trackingNumbers.map(t => t.trackingNumber)).toContain('12345678901234567890123456');
        // Should be detected as UPS due to UPS context in body
        const upsTracking = result.current.trackingNumbers.find(t => t.trackingNumber === '12345678901234567890123456');
        expect(upsTracking?.carrier).toBe('ups');
    });
}); 