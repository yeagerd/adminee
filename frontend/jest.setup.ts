import '@testing-library/jest-dom';

// Mock environment variables for tests
process.env.NEXT_PUBLIC_GATEWAY_URL = 'http://localhost:3001';

// Suppress console warnings for missing environment variables during tests
const originalWarn = console.warn;
console.warn = (...args) => {
    if (args[0] && typeof args[0] === 'string' && args[0].includes('Missing optional client environment variable')) {
        return; // Suppress environment variable warnings
    }
    originalWarn(...args);
};

// Configure React 18 testing environment
import { configure } from '@testing-library/react';

// Configure testing library to use act by default
configure({ asyncUtilTimeout: 10000 });

// Suppress act warnings in tests
const originalError = console.error;
console.error = (...args) => {
    if (
        args[0] &&
        typeof args[0] === 'string' &&
        (args[0].includes('The current testing environment is not configured to support act(...)') ||
            args[0].includes('An update to') && args[0].includes('inside a test was not wrapped in act(...)'))
    ) {
        return; // Suppress act warnings
    }
    originalError(...args);
};

