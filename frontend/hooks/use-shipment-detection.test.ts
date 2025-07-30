import { EmailMessage } from '@/types/office-service';
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
                email: 'shipping@amazon.com'
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
        expect(result.current.trackingNumbers).toContain('1Z999AA1234567890');
        expect(result.current.trackingNumbers).toContain('1Z999AA9876543210');
        expect(result.current.trackingNumbers).toContain('1Z999AA1111111111');
        expect(result.current.trackingNumbers).toContain('1Z999AA2222222222');
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
        expect(result.current.trackingNumbers).toContain('12345678901234567890');
        expect(result.current.trackingNumbers).toContain('98765432109876543210');
    });

    it('should detect shipment email from Amazon domain', () => {
        const email: EmailMessage = {
            id: '3',
            subject: 'Your Amazon order has shipped',
            body_text: 'Your order has been shipped with tracking number 1Z999AA1234567890',
            from_address: {
                name: 'Amazon',
                email: 'shipping@amazon.com'
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
        expect(result.current.trackingNumbers).toContain('1Z999AA1234567890');
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

        // Should only detect the tracking number once, even though it appears multiple times
        expect(result.current.trackingNumbers).toHaveLength(1);
        expect(result.current.trackingNumbers).toContain('1Z999AA1234567890');

        // Verify that the tracking number appears multiple times in the text but is only detected once
        const allText = `${email.subject} ${email.body_text}`;
        const occurrences = (allText.match(/1Z999AA1234567890/g) || []).length;
        expect(occurrences).toBeGreaterThan(1); // Verify it appears multiple times
        expect(result.current.trackingNumbers).toHaveLength(1); // But only detected once
    });
}); 