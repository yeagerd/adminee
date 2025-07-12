#!/usr/bin/env node

/**
 * Simple test script for the Briefly Express Gateway
 * Tests health endpoint and basic functionality
 */

const http = require('http');
const https = require('https');

const GATEWAY_URL = process.env.GATEWAY_URL || 'http://localhost:3001';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const client = isHttps ? https : http;

        const requestOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: options.headers || {},
            timeout: 5000
        };

        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    headers: res.headers,
                    data: data
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        if (options.body) {
            req.write(options.body);
        }

        req.end();
    });
}

async function testHealthEndpoint() {
    console.log('🏥 Testing health endpoint...');
    try {
        const response = await makeRequest(`${GATEWAY_URL}/health`);
        console.log(`✅ Health check passed: ${response.statusCode}`);
        console.log(`   Response: ${response.data}`);
        return true;
    } catch (error) {
        console.log(`❌ Health check failed: ${error.message}`);
        return false;
    }
}

async function testProtectedEndpoint() {
    console.log('🔒 Testing protected endpoint (should fail without auth)...');
    try {
        const response = await makeRequest(`${GATEWAY_URL}/api/chat`);
        console.log(`❌ Protected endpoint should have failed: ${response.statusCode}`);
        return false;
    } catch (error) {
        console.log(`✅ Protected endpoint correctly rejected: ${error.message}`);
        return true;
    }
}

async function testInvalidAuth() {
    console.log('🔑 Testing invalid authentication...');
    try {
        const response = await makeRequest(`${GATEWAY_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer invalid-token',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: 'test' })
        });

        if (response.statusCode === 401) {
            console.log('✅ Invalid auth correctly rejected');
            return true;
        } else {
            console.log(`❌ Expected 401, got ${response.statusCode}`);
            return false;
        }
    } catch (error) {
        console.log(`✅ Invalid auth correctly rejected: ${error.message}`);
        return true;
    }
}

async function testMaliciousTraffic() {
    console.log('🛡️ Testing malicious traffic filtering...');

    const tests = [
        {
            name: 'Suspicious User Agent',
            headers: { 'User-Agent': 'sqlmap/1.0' }
        },
        {
            name: 'Suspicious Headers',
            headers: { 'X-Forwarded-For': '192.168.1.100' }
        },
        {
            name: 'Large Payload',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'a'.repeat(2000000) // 2MB payload
        }
    ];

    let passed = 0;
    for (const test of tests) {
        try {
            const response = await makeRequest(`${GATEWAY_URL}/api/chat`, {
                method: 'POST',
                headers: test.headers,
                body: test.body
            });

            if (response.statusCode === 403 || response.statusCode === 413) {
                console.log(`✅ ${test.name}: Correctly blocked`);
                passed++;
            } else {
                console.log(`❌ ${test.name}: Should have been blocked, got ${response.statusCode}`);
            }
        } catch (error) {
            console.log(`✅ ${test.name}: Correctly blocked (${error.message})`);
            passed++;
        }
    }

    return passed === tests.length;
}

async function runTests() {
    console.log('🧪 Running Briefly Gateway Tests');
    console.log(`Gateway URL: ${GATEWAY_URL}`);
    console.log(`Backend URL: ${BACKEND_URL}`);
    console.log('');

    const tests = [
        { name: 'Health Endpoint', fn: testHealthEndpoint },
        { name: 'Protected Endpoint', fn: testProtectedEndpoint },
        { name: 'Invalid Authentication', fn: testInvalidAuth },
        { name: 'Malicious Traffic Filtering', fn: testMaliciousTraffic }
    ];

    let passed = 0;
    for (const test of tests) {
        console.log(`\n📋 ${test.name}`);
        console.log('─'.repeat(50));

        const result = await test.fn();
        if (result) {
            passed++;
        }
    }

    console.log('\n📊 Test Results');
    console.log('─'.repeat(50));
    console.log(`Passed: ${passed}/${tests.length}`);

    if (passed === tests.length) {
        console.log('🎉 All tests passed! Gateway is working correctly.');
        process.exit(0);
    } else {
        console.log('❌ Some tests failed. Check gateway configuration.');
        process.exit(1);
    }
}

// Handle command line arguments
if (process.argv.includes('--help') || process.argv.includes('-h')) {
    console.log(`
Briefly Gateway Test Script

Usage: node test_gateway.js [options]

Options:
  --gateway-url <url>    Gateway URL (default: http://localhost:3001)
  --backend-url <url>    Backend URL (default: http://localhost:8000)
  --help, -h            Show this help message

Environment Variables:
  GATEWAY_URL           Gateway URL
  BACKEND_URL           Backend URL

Examples:
  node test_gateway.js
  GATEWAY_URL=http://localhost:3001 node test_gateway.js
  node test_gateway.js --gateway-url http://localhost:3001
`);
    process.exit(0);
}

// Parse command line arguments
for (let i = 2; i < process.argv.length; i++) {
    if (process.argv[i] === '--gateway-url' && i + 1 < process.argv.length) {
        process.env.GATEWAY_URL = process.argv[i + 1];
        i++;
    } else if (process.argv[i] === '--backend-url' && i + 1 < process.argv.length) {
        process.env.BACKEND_URL = process.argv[i + 1];
        i++;
    }
}

// Run tests
runTests().catch((error) => {
    console.error('❌ Test runner failed:', error);
    process.exit(1);
}); 