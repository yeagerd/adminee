// @ts-nocheck
import cookieParser from 'cookie-parser';
import cors from 'cors';
import dotenv from 'dotenv';
import express from 'express';
import rateLimit from 'express-rate-limit';
import fs from 'fs';
import helmet from 'helmet';
import { createProxyMiddleware } from 'http-proxy-middleware';
import jwt from 'jsonwebtoken';
import path from 'path';
import { fileURLToPath } from 'url';
import winston from 'winston';

// Create a logger instance
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp({
            format: 'YYYY-MM-DD HH:mm:ss,SSS'
        }),
        winston.format.printf((info: any) => `${info.timestamp} - ${info.level.toUpperCase()} - ${info.message}`)
    ),
    transports: [
        new winston.transports.Console()
    ]
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const envPath = path.join(__dirname, '.env');
console.log('[DEBUG] Loading .env file from:', envPath);
if (!fs.existsSync(envPath)) {
    logger.error('❌ .env file not found in gateway directory');
    logger.error(`   Expected location: ${envPath}`);
    logger.error('   Please create a .env file with:');
    logger.error('   NEXTAUTH_SECRET=your-secret-here');
    logger.error('   USER_SERVICE_URL=http://localhost:8001');
    logger.error('   CHAT_SERVICE_URL=http://localhost:8002');
    logger.error('   OFFICE_SERVICE_URL=http://localhost:8003');
    logger.error('   FRONTEND_URL=http://localhost:3000');
    process.exit(1);
}
dotenv.config({ path: envPath });

// ENVIRONMENT VARIABLE ASSERTION (must be first)
(function assertRequiredEnv() {
    const required = [
        'NEXTAUTH_SECRET',
        'USER_SERVICE_URL',
        'CHAT_SERVICE_URL',
        'OFFICE_SERVICE_URL',
        'FRONTEND_URL',
        'API_FRONTEND_USER_KEY',
        'API_FRONTEND_CHAT_KEY',
        'API_FRONTEND_OFFICE_KEY',
    ];
    const missing = required.filter((key) => !process.env[key]);
    if (missing.length > 0) {
        console.error('❌ Missing required environment variables in gateway/.env:');
        missing.forEach((key) => console.error(`   - ${key}`));
        console.error('\nPlease check your gateway/.env file and set the missing variables.');
        process.exit(1);
    }
})();

// Validate required environment variables
if (!process.env.NEXTAUTH_SECRET) {
    logger.error('❌ NEXTAUTH_SECRET is required but not set in .env file');
    logger.error('   Please add NEXTAUTH_SECRET=your-secret-here to your .env file');
    process.exit(1);
}

// Validate API keys for backend services
if (!process.env.API_FRONTEND_USER_KEY) {
    logger.error('❌ API_FRONTEND_USER_KEY is required but not set in .env file');
    logger.error('   Please add API_FRONTEND_USER_KEY=your-frontend-user-api-key to your .env file');
    process.exit(1);
}

if (!process.env.API_FRONTEND_CHAT_KEY) {
    logger.error('❌ API_FRONTEND_CHAT_KEY is required but not set in .env file');
    logger.error('   Please add API_FRONTEND_CHAT_KEY=your-frontend-chat-api-key to your .env file');
    process.exit(1);
}

if (!process.env.API_FRONTEND_OFFICE_KEY) {
    logger.error('❌ API_FRONTEND_OFFICE_KEY is required but not set in .env file');
    logger.error('   Please add API_FRONTEND_OFFICE_KEY=your-frontend-office-api-key to your .env file');
    process.exit(1);
}

logger.info('✅ Environment loaded successfully');

const app = express();

// Security middleware
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
            imgSrc: ["'self'", "data:", "https:"],
        },
    },
    crossOriginEmbedderPolicy: false, // Allow SSE
}));

// Enhanced rate limiting with different tiers
const strictLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 30, // 30 requests per IP per window for sensitive endpoints
    message: 'Too many requests from this IP',
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: false,
    keyGenerator: (req: any) => {
        // Use user ID if available, otherwise IP
        return req.user?.sub || req.ip;
    }
});

const standardLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 100, // 100 requests per IP per window
    message: 'Too many requests from this IP',
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: false,
    keyGenerator: (req: any) => {
        return req.user?.sub || req.ip;
    }
});

// Malicious traffic filtering middleware
const maliciousTrafficFilter = (req: any, res: any, next: any) => {
    const userAgent = req.headers['user-agent'] || '';
    const contentType = req.headers['content-type'] || '';
    const contentLength = parseInt(req.headers['content-length'] || '0');

    // Block suspicious user agents
    const suspiciousUserAgents = [
        /bot/i, /crawler/i, /spider/i, /scraper/i,
        /curl/i, /wget/i, /python/i, /java/i,
        /sqlmap/i, /nikto/i, /nmap/i
    ];

    if (suspiciousUserAgents.some(pattern => pattern.test(userAgent))) {
        logger.warn(`Blocked suspicious user agent: ${userAgent}`);
        return res.status(403).json({ error: 'Access denied' });
    }

    // Block requests with suspicious content types
    if (contentType.includes('application/x-www-form-urlencoded') && contentLength > 1000000) {
        logger.warn(`Blocked large form data: ${contentLength} bytes`);
        return res.status(413).json({ error: 'Payload too large' });
    }

    // Block requests with suspicious headers
    const suspiciousHeaders = ['x-forwarded-for', 'x-real-ip', 'x-client-ip'];
    const hasSuspiciousHeaders = suspiciousHeaders.some(header =>
        req.headers[header] && !req.headers[header].match(/^(127\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)/)
    );

    if (hasSuspiciousHeaders) {
        logger.warn(`Blocked request with suspicious headers from ${req.ip}`);
        return res.status(403).json({ error: 'Access denied' });
    }

    // Block requests with suspicious query parameters
    const suspiciousParams = ['eval', 'exec', 'system', 'shell', 'cmd'];
    const hasSuspiciousParams = suspiciousParams.some(param =>
        req.query[param] || (req.body && req.body[param])
    );

    if (hasSuspiciousParams) {
        logger.warn(`Blocked request with suspicious parameters from ${req.ip}`);
        return res.status(403).json({ error: 'Access denied' });
    }

    next();
};

// Block /internal endpoints at the gateway level
app.use((req, res, next) => {
    if (req.path.startsWith('/api/internal') || req.path.startsWith('/internal')) {
        logger.warn(`Blocked attempt to access internal endpoint: ${req.method} ${req.path}`);
        return res.status(403).json({ error: 'Access to internal endpoints is forbidden via gateway' });
    }
    next();
});

// CORS configuration
app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'X-User-Id', 'X-User-Email', 'X-User-Name']
}));

// Body and cookie parsing with size limits
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(cookieParser());

// Enhanced JWT validation middleware
const validateAuth = async (req: any, res: any, next: any) => {
    try {
        let token;

        // Try Authorization header first (JWT)
        const authHeader = req.headers.authorization || '';
        if (authHeader.startsWith('Bearer ')) {
            token = authHeader.split(' ')[1];
        }

        // Fallback to session cookie if using NextAuth sessions
        if (!token && req.cookies['next-auth.session-token']) {
            // For session-based auth, you'd need to validate the session cookie
            // This is more complex and requires NextAuth's session validation
            return res.status(401).json({ error: 'Session-based auth not implemented in proxy' });
        }

        if (!token) {
            return res.status(401).json({ error: 'Missing authentication token' });
        }

        // Verify JWT token
        const payload = jwt.verify(token, process.env.NEXTAUTH_SECRET as string);

        // Additional token validation
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) {
            return res.status(401).json({ error: 'Token expired' });
        }

        if (payload.iat && payload.iat > now + 60) {
            return res.status(401).json({ error: 'Token issued in the future' });
        }

        // Validate required claims
        if (!payload.sub) {
            return res.status(401).json({ error: 'Invalid token: missing subject' });
        }

        req.user = payload;

        // Log authenticated requests (optional)
        logger.info(`Authenticated request: ${req.method} ${req.path} - User: ${payload.sub || payload.email}`);

        next();
    } catch (err: any) {
        logger.error('Auth validation error:', err.message);
        return res.status(401).json({ error: 'Invalid or expired token' });
    }
};

// Health check endpoint (no auth required)
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime()
    });
});

// Apply malicious traffic filtering to all routes
app.use(maliciousTrafficFilter);

// OpenTelemetry tracing for local development
if (process.env.NODE_ENV !== 'production') {
    try {
        // Dynamically require OpenTelemetry only in dev
        const { NodeSDK } = require('@opentelemetry/sdk-node');
        const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
        const { ConsoleSpanExporter } = require('@opentelemetry/exporter-trace-stdout');
        const sdk = new NodeSDK({
            traceExporter: new ConsoleSpanExporter(),
            instrumentations: [getNodeAutoInstrumentations()],
        });
        sdk.start();
        console.log('OpenTelemetry tracing enabled (console exporter)');
    } catch (err) {
        console.warn('OpenTelemetry tracing not enabled:', err.message);
    }
}

// Service routing configuration
const serviceRoutes = {
    '/api/users': process.env.USER_SERVICE_URL || 'http://127.0.0.1:8001',
    '/api/chat': process.env.CHAT_SERVICE_URL || 'http://127.0.0.1:8002',
    '/api/calendar': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/email': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/files': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/drafts': process.env.CHAT_SERVICE_URL || 'http://127.0.0.1:8002',
    '/api/meetings': process.env.MEETINGS_SERVICE_URL || 'http://127.0.0.1:8003',
};

// Create proxy middleware factory
const createServiceProxy = (targetUrl: string, pathRewrite?: Record<string, string>) => {
    return createProxyMiddleware({
        target: targetUrl,
        changeOrigin: true,
        ws: true, // Enable WebSocket proxying
        timeout: 60000, // 60 second timeout
        proxyTimeout: 60000,
        pathRewrite,

        // Handle proxy requests
        onProxyReq: (proxyReq: any, req: any, res: any) => {
            // Add service API key for backend authentication
            if (targetUrl.includes('8001')) {
                // User service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_USER_KEY || '');
            } else if (targetUrl.includes('8002')) {
                // Chat service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_CHAT_KEY || '');
            } else if (targetUrl.includes('8003')) {
                // Office service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_OFFICE_KEY || '');
            }

            // Forward user identity to backend
            if (req.user) {
                proxyReq.setHeader('X-User-Id', req.user.sub || req.user.id || '');
                proxyReq.setHeader('X-User-Email', req.user.email || '');
                proxyReq.setHeader('X-User-Name', req.user.name || '');

                // Remove the original Authorization header to prevent double-auth
                proxyReq.removeHeader('Authorization');
            }

            // Add request ID for tracing
            const requestId = req.headers['x-request-id'] || Math.random().toString(36).substr(2, 9);
            proxyReq.setHeader('X-Request-Id', requestId);

            // Re-write the request body for proxying
            if (req.body && Object.keys(req.body).length > 0) {
                const bodyData = JSON.stringify(req.body);
                proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
                proxyReq.write(bodyData);
                logger.info(`Rewriting body for proxy: ${bodyData}`);
            }

            // Log proxied requests
            logger.info(`Proxying: ${req.method} ${req.path} -> ${targetUrl}${proxyReq.path}`);
        },

        // Handle proxy responses
        onProxyRes: (proxyRes: any, req: any, res: any) => {
            // Handle Server-Sent Events - disable buffering
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                logger.info('Handling SSE stream');
                res.writeHead(proxyRes.statusCode || 200, {
                    ...proxyRes.headers,
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                });
                proxyRes.pipe(res, { end: true });
                return;
            }

            // Add security headers
            proxyRes.headers['X-Content-Type-Options'] = 'nosniff';
            proxyRes.headers['X-Frame-Options'] = 'DENY';
            proxyRes.headers['X-XSS-Protection'] = '1; mode=block';
        },

        // Handle WebSocket upgrades
        onProxyReqWs: (proxyReq: any, req: any, socket: any, options: any, head: any) => {
            logger.info('WebSocket upgrade request');
            // You could add WebSocket-specific auth here if needed
        },

        // Error handling
        onError: (err: any, req: any, res: any) => {
            logger.error(`Proxy error to ${targetUrl}:`, err.message);
            if (!res.headersSent) {
                res.status(500).json({
                    error: 'Service unavailable',
                    service: targetUrl,
                    message: process.env.NODE_ENV === 'development' ? err.message : 'Internal server error'
                });
            }
        }
    });
};

// Apply service-specific routes with appropriate rate limiting and path rewrites
app.use('/api/users', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/users'], { '^/api/users': '/users' }));
app.use('/api/users/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/users'], { '^/api/users': '/users' }));
app.use('/api/chat', validateAuth, strictLimiter, createServiceProxy(serviceRoutes['/api/chat'], { '^/api/chat': '/chat' }));
app.use('/api/chat/*', validateAuth, strictLimiter, createServiceProxy(serviceRoutes['/api/chat'], { '^/api/chat': '/chat' }));
app.use('/api/calendar', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/calendar'], { '^/api/calendar': '/calendar' }));
app.use('/api/calendar/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/calendar'], { '^/api/calendar': '/calendar' }));
app.use('/api/email', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/email'], { '^/api/email': '/email' }));
app.use('/api/email/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/email'], { '^/api/email': '/email' }));
app.use('/api/files', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/files'], { '^/api/files': '/files' }));
app.use('/api/files/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/files'], { '^/api/files': '/files' }));
app.use('/api/drafts', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/drafts'], { '^/api/drafts': '/chat/drafts' }));
app.use('/api/drafts/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/drafts'], { '^/api/drafts': '/chat/drafts' }));
app.use('/api/meetings', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/meetings'], { '^/api/meetings': '/api/meetings' }));
app.use('/api/meetings/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/meetings'], { '^/api/meetings': '/api/meetings' }));

// Fallback for other API routes (default to user service)
app.use('/api', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/users'], { '^/api': '' }));

// Catch-all for undefined routes
app.use('*', (req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use((err: any, req: any, res: any, next: any) => {
    logger.error('Global error:', err);
    res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
    });
});

const PORT = process.env.PORT || 3001;
const server = app.listen(PORT, () => {
    logger.info(`Auth proxy running on port ${PORT}`);
    logger.info(`Frontend URL: ${process.env.FRONTEND_URL || 'http://localhost:3000'}`);
    logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
    logger.info('');
    logger.info('Service Routing:');
    logger.info(`  /api/users    → ${serviceRoutes['/api/users']}`);
    logger.info(`  /api/chat     → ${serviceRoutes['/api/chat']}`);
    logger.info(`  /api/calendar → ${serviceRoutes['/api/calendar']}`);
    logger.info(`  /api/email    → ${serviceRoutes['/api/email']}`);
    logger.info(`  /api/files    → ${serviceRoutes['/api/files']}`);
    logger.info(`  /api/drafts     → ${serviceRoutes['/api/drafts']}`);
    logger.info(`  /api/meetings → ${serviceRoutes['/api/meetings']}`);
});

// Handle WebSocket upgrades
server.on('upgrade', (request: any, socket: any, head: any) => {
    logger.info('WebSocket upgrade event');

    // Route WebSocket connections based on path
    const url = new URL(request.url || '', `http://${request.headers.host}`);
    const path = url.pathname;

    let targetService = serviceRoutes['/api/users']; // Default to user service

    if (path.startsWith('/api/chat')) {
        targetService = serviceRoutes['/api/chat'];
    } else if (path.startsWith('/api/calendar') || path.startsWith('/api/email') || path.startsWith('/api/files')) {
        targetService = serviceRoutes['/api/calendar']; // All office service endpoints
    } else if (path.startsWith('/api/meetings')) {
        targetService = serviceRoutes['/api/meetings'];
    }

    // Create proxy for WebSocket
    const wsProxy = createServiceProxy(targetService);
    if (wsProxy && typeof wsProxy.upgrade === 'function') {
        wsProxy.upgrade(request, socket, head);
    } else {
        logger.error('WebSocket proxy upgrade function not available');
        socket.destroy();
    }
});

// Graceful shutdown
process.on('SIGTERM', () => {
    logger.info('Received SIGTERM, shutting down gracefully');
    server.close(() => {
        logger.info('Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    logger.info('Received SIGINT, shutting down gracefully');
    server.close(() => {
        logger.info('Server closed');
        process.exit(0);
    });
});

export default app;