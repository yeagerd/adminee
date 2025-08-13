import '@testing-library/jest-dom';

// Jest setup file

// Mock GatewayClient to avoid real network and constructor issues in tests
jest.mock('@/lib/gateway-client', () => {
  const actual = jest.requireActual('@/lib/gateway-client');
  class MockGatewayClient {
    request = jest.fn(async () => ({}));
    // Add any methods used in tests as no-ops returning empty data
    listDrafts = jest.fn(async () => ({ drafts: [], total_count: 0, has_more: false }));
    createDraft = jest.fn(async () => ({ id: '1', type: 'email', status: 'draft', content: '', metadata: {}, created_at: '', updated_at: '', user_id: '' }));
  }
  return {
    ...actual,
    GatewayClient: MockGatewayClient,
    gatewayClient: new MockGatewayClient(),
    default: new MockGatewayClient(),
  };
});
