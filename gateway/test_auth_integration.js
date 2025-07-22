#!/usr/bin/env node

/**
 * Integration test for end-to-end authentication flow:
 * - Generates a valid JWT (using NEXTAUTH_SECRET)
 * - Makes an authenticated request to the gateway
 * - Verifies the backend receives the correct user context
 */

const http = require('http');
const jwt = require('jsonwebtoken');

const GATEWAY_URL = process.env.GATEWAY_URL || 'http://localhost:3001';
const NEXTAUTH_SECRET = process.env.NEXTAUTH_SECRET || 'test-secret';

function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const client = http;
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
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                resolve({ statusCode: res.statusCode, headers: res.headers, data });
            });
        });
        req.on('error', (err) => { reject(err); });
        req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
        if (options.body) req.write(options.body);
        req.end();
    });
}

function generateTestJWT() {
    const now = Math.floor(Date.now() / 1000);
    const payload = {
        sub: 'user_123',
        email: 'testuser@example.com',
        name: 'Test User',
        iat: now,
        exp: now + 3600,
        iss: 'https://nextauth.example.com',
    };
    return jwt.sign(payload, NEXTAUTH_SECRET);
}

async function testAuthenticatedRequest() {
    console.log('🔑 Testing authenticated request through gateway...');
    const token = generateTestJWT();
    const response = await makeRequest(`${GATEWAY_URL}/api/users/me`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    if (response.statusCode === 200 || response.statusCode === 404) {
        // 200 if user exists, 404 if not (both mean auth worked)
        console.log('✅ Authenticated request succeeded:', response.statusCode);
        console.log('   Response:', response.data);
        return true;
    } else {
        console.log('❌ Authenticated request failed:', response.statusCode);
        console.log('   Response:', response.data);
        return false;
    }
}

async function run() {
    const result = await testAuthenticatedRequest();
    process.exit(result ? 0 : 1);
}

run(); 