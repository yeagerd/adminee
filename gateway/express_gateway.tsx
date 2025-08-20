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

// Enhanced logging configuration for better debugging
const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
        winston.format.timestamp({
            format: 'YYYY-MM-DDTHH:mm:ss.SSS[Z]'
        }),
        winston.format.errors({ stack: true }),
        winston.format.printf((info: any) => {
            const {
                timestamp,
                level,
                message,
                service = 'gateway',
                requestId,
                userId,
                file,
                line,
                method,
                path,
                statusCode,
                duration,
                ...extra
            } = info;

            // Build the enhanced log line
            let logLine = `${timestamp} [${service}] [${level.toUpperCase()}]`;

            // Add request ID if present (last 4 chars for readability)
            if (requestId) {
                const shortId = requestId.length >= 4 ? requestId.slice(-4) : requestId;
                logLine += ` [${shortId}]`;
            }

            // Add logger name and file/line info
            logLine += ` ${info.logger || 'gateway'}`;
            if (file && line) {
                logLine += ` ${file}:${line}`;
            }

            // Add the main message
            logLine += ` - ${message}`;

            // Add user context if present
            if (userId) {
                logLine += ` | User: ${userId}`;
            }

            // Add HTTP context if present
            if (method && path) {
                logLine += ` | ${method} ${path}`;
                if (statusCode) {
                    logLine += ` → ${statusCode}`;
                }
                if (duration) {
                    logLine += ` (${duration}ms)`;
                }
            }

            // Add extra context as key=value pairs
            const extraContext = Object.entries(extra)
                .filter(([key, value]) => value !== undefined && value !== null)
                .map(([key, value]) => `${key}=${value}`)
                .join(' ');

            if (extraContext) {
                logLine += ` | ${extraContext}`;
            }

            return logLine;
        })
    ),
    transports: [
        new winston.transports.Console()
    ]
});

// Helper function to get file and line information
const getFileLineInfo = () => {
    const stack = new Error().stack;
    if (stack) {
        const lines = stack.split('\n');
        // Skip the first few lines (Error, getFileLineInfo, caller)
        for (let i = 3; i < lines.length; i++) {
            const line = lines[i];
            const match = line.match(/at\s+(.+?)\s+\((.+?):(\d+):(\d+)\)/);
            if (match) {
                const [, , filePath, lineNum] = match;
                const fileName = filePath.split('/').pop() || filePath.split('\\').pop() || filePath;
                return { file: fileName, line: parseInt(lineNum) };
            }
        }
    }
    return { file: 'unknown', line: 0 };
};

// Enhanced logging helper
const logWithContext = (level: string, message: string, context: any = {}) => {
    const fileLine = getFileLineInfo();
    logger.log(level, message, {
        service: 'gateway',
        ...fileLine,
        ...context
    });
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const envPath = path.join(__dirname, '.env');
console.log('[DEBUG] Loading .env file from:', envPath);
if (!fs.existsSync(envPath)) {
    logWithContext('error', '❌ .env file not found in gateway directory');
    logWithContext('error', `   Expected location: ${envPath}`);
    logWithContext('error', '   Please create a .env file with:');
    logWithContext('error', '   NEXTAUTH_SECRET=your-secret-here');
    logWithContext('error', '   USER_SERVICE_URL=http://localhost:8001');
logWithContext('error', '   CHAT_SERVICE_URL=http://localhost:8002');
logWithContext('error', '   OFFICE_SERVICE_URL=http://localhost:8003');
logWithContext('error', '   VESPA_QUERY_URL=http://localhost:8006');
    logWithContext('error', '   FRONTEND_URL=http://localhost:3000');
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
        'MEETINGS_SERVICE_URL',
        'SHIPMENTS_SERVICE_URL',
        'VESPA_QUERY_URL',
        'API_FRONTEND_USER_KEY',
        'API_FRONTEND_CHAT_KEY',
        'API_FRONTEND_OFFICE_KEY',
        'API_FRONTEND_SHIPMENTS_KEY',
        'API_FRONTEND_MEETINGS_KEY',
    ];
    const missing = required.filter((key) => !process.env[key]);
    if (missing.length > 0) {
        console.error('❌ Missing required environment variables in gateway/.env:');
        missing.forEach((key) => console.error(`   - ${key}`));
        console.error('\nPlease check your gateway/.env file and set the missing variables.');
        process.exit(1);
    }
})();

logWithContext('info', '✅ Environment loaded successfully');

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
        logWithContext('warn', 'Blocked suspicious user agent', {
            userAgent,
            method: req.method,
            path: req.path,
            ip: req.ip
        });
        return res.status(403).json({ error: 'Access denied' });
    }

    // Block requests with suspicious content types
    if (contentType.includes('application/x-www-form-urlencoded') && contentLength > 1000000) {
        logWithContext('warn', 'Blocked large form data', {
            contentLength,
            contentType,
            method: req.method,
            path: req.path,
            ip: req.ip
        });
        return res.status(413).json({ error: 'Payload too large' });
    }

    // Block requests with suspicious headers
    const suspiciousHeaders = ['x-forwarded-for', 'x-real-ip', 'x-client-ip'];
    const hasSuspiciousHeaders = suspiciousHeaders.some(header =>
        req.headers[header] && !req.headers[header].match(/^(127\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)/)
    );

    if (hasSuspiciousHeaders) {
        logWithContext('warn', 'Blocked request with suspicious headers', {
            ip: req.ip,
            method: req.method,
            path: req.path
        });
        return res.status(403).json({ error: 'Access denied' });
    }

    // Block requests with suspicious query parameters
    const suspiciousParams = ['eval', 'exec', 'system', 'shell', 'cmd'];
    const hasSuspiciousParams = suspiciousParams.some(param =>
        req.query[param] || (req.body && req.body[param])
    );

    if (hasSuspiciousParams) {
        logWithContext('warn', 'Blocked request with suspicious parameters', {
            ip: req.ip,
            method: req.method,
            path: req.path
        });
        return res.status(403).json({ error: 'Access denied' });
    }

    next();
};

// Block /internal endpoints at the gateway level
app.use((req, res, next) => {
    if (req.path.startsWith('/api/internal') || req.path.startsWith('/internal')) {
        logWithContext('warn', 'Blocked attempt to access internal endpoint', {
            method: req.method,
            path: req.path,
            ip: req.ip
        });
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

        // Log authenticated requests with enhanced context
        logWithContext('info', 'Authenticated request', {
            method: req.method,
            path: req.path,
            userId: payload.sub || payload.email,
            requestId: req.headers['x-request-id']
        });

        next();
    } catch (err: any) {
        logWithContext('error', 'Auth validation error', {
            error: err.message,
            method: req.method,
            path: req.path,
            requestId: req.headers['x-request-id']
        });
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

// Request timing and ID middleware
app.use((req: any, res: any, next: any) => {
    // Generate or use existing request ID
    req.requestId = req.headers['x-request-id'] || Math.random().toString(36).substr(2, 9);

    // Add request ID to response headers
    res.setHeader('X-Request-Id', req.requestId);

    // Start timing
    req.startTime = Date.now();

    // Log incoming request
    logWithContext('debug', '→ Incoming request', {
        method: req.method,
        path: req.path,
        requestId: req.requestId,
        ip: req.ip,
        userAgent: req.headers['user-agent']
    });

    // Override res.end to log response timing
    const originalEnd = res.end;
    res.end = function (chunk: any, encoding: any) {
        const duration = Date.now() - req.startTime;

        // Log response
        const logLevel = res.statusCode >= 400 ? 'error' : 'info';
        const statusEmoji = res.statusCode >= 400 ? '❌' : '✅';

        logWithContext(logLevel, `${statusEmoji} Response completed`, {
            method: req.method,
            path: req.path,
            statusCode: res.statusCode,
            duration,
            requestId: req.requestId
        });

        originalEnd.call(this, chunk, encoding);
    };

    next();
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
    '/api/v1/users': process.env.USER_SERVICE_URL || 'http://127.0.0.1:8001',
    '/api/v1/chat': process.env.CHAT_SERVICE_URL || 'http://127.0.0.1:8002',
    '/api/v1/calendar': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/v1/email': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/v1/files': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/v1/contacts': process.env.OFFICE_SERVICE_URL || 'http://127.0.0.1:8003',
    '/api/v1/drafts': process.env.CHAT_SERVICE_URL || 'http://127.0.0.1:8002',
    '/api/v1/shipments': process.env.SHIPMENTS_SERVICE_URL || 'http://127.0.0.1:8004',
    '/api/v1/meetings': process.env.MEETINGS_SERVICE_URL || 'http://127.0.0.1:8005',
    '/api/v1/bookings': process.env.MEETINGS_SERVICE_URL || 'http://127.0.0.1:8005',
    '/api/v1/public/polls': process.env.MEETINGS_SERVICE_URL || 'http://127.0.0.1:8005',
    '/api/v1/search': process.env.VESPA_QUERY_URL || 'http://127.0.0.1:8006',
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
        // Configure header forwarding
        onProxyReq: (proxyReq: any, req: any, res: any) => {
            // REQUIREMENT: Explicitly forward all headers from original request to proxy request
            // 
            // The http-proxy-middleware library does not automatically forward all headers
            // from the original request to the target service. This was causing API key
            // authentication to fail because custom headers like X-API-Key, Authorization,
            // and X-Service-Key were being dropped during the proxy forwarding process.
            //
            // By explicitly iterating through all original request headers and setting them
            // on the proxy request, we ensure that:
            // 1. All original headers are preserved and forwarded to the target service
            // 2. Custom authentication headers set via proxyReq.setHeader() are not dropped
            // 3. The proxy middleware doesn't lose any headers during forwarding
            //
            // This fix was discovered after extensive debugging showed that the gateway
            // was correctly setting API key headers on the proxy request, but the shipments
            // service was not receiving them. The issue was that the proxy middleware
            // was not forwarding these headers to the target service.
            Object.keys(req.headers).forEach(key => {
                if (req.headers[key]) {
                    proxyReq.setHeader(key, req.headers[key]);
                }
            });

            // Add service API key for backend authentication
            if (targetUrl.includes('8001')) {
                // User service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_USER_KEY || '');
                logger.debug(`Setting API key for user service: ${process.env.API_FRONTEND_USER_KEY ? 'present' : 'missing'}`);
            } else if (targetUrl.includes('8002')) {
                // Chat service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_CHAT_KEY || '');
                logger.debug(`Setting API key for chat service: ${process.env.API_FRONTEND_CHAT_KEY ? 'present' : 'missing'}`);
            } else if (targetUrl.includes('8003')) {
                // Office service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_OFFICE_KEY || '');
                logger.debug(`Setting API key for office service: ${process.env.API_FRONTEND_OFFICE_KEY ? 'present' : 'missing'}`);
            } else if (targetUrl.includes('8004')) {
                // Shipments service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_SHIPMENTS_KEY || '');
                logger.debug(`Setting API key for shipments service: ${process.env.API_FRONTEND_SHIPMENTS_KEY ? 'present' : 'missing'}`);
            } else if (targetUrl.includes('8005')) {
                // Meetings service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_MEETINGS_KEY || '');
                logger.debug(`Setting API key for meetings service: ${process.env.API_FRONTEND_MEETINGS_KEY ? 'present' : 'missing'}`);
            } else if (targetUrl.includes('8006')) {
                // Vespa query service
                proxyReq.setHeader('X-API-Key', process.env.API_FRONTEND_VESPA_QUERY_KEY || '');
                logger.debug(`Setting API key for vespa query service: ${process.env.API_FRONTEND_VESPA_QUERY_KEY ? 'present' : 'missing'}`);
            } else {
                logger.warn(`No API key assigned for target URL: ${targetUrl}`);
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
            const requestId = req.requestId || req.headers['x-request-id'] || Math.random().toString(36).substr(2, 9);
            proxyReq.setHeader('X-Request-Id', requestId);

            // Re-write the request body for proxying
            if (req.body && Object.keys(req.body).length > 0) {
                const bodyData = JSON.stringify(req.body);
                proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
                proxyReq.write(bodyData);
                logger.info(`Rewriting body for proxy: ${bodyData}`);
            }

            // Log proxied requests with enhanced context
            logWithContext('debug', 'Proxying request', {
                method: req.method,
                path: req.path,
                targetUrl: `${targetUrl}${proxyReq.path}`,
                requestId: req.requestId || requestId,
                userId: req.user?.sub || req.user?.email
            });
        },

        // Handle proxy responses
        onProxyRes: (proxyRes: any, req: any, res: any) => {
            // Handle Server-Sent Events - disable buffering
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                logWithContext('info', 'Handling SSE stream', {
                    statusCode: proxyRes.statusCode,
                    contentType: proxyRes.headers['content-type']
                });
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
            logWithContext('info', 'WebSocket upgrade request', {
                path: req.path,
                targetUrl
            });
            // You could add WebSocket-specific auth here if needed
        },

        // Error handling
        onError: (err: any, req: any, res: any) => {
            logWithContext('error', 'Proxy error', {
                targetUrl,
                error: err.message,
                method: req.method,
                path: req.path,
                requestId: req.headers['x-request-id']
            });
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
app.use('/api/v1/users', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/users'], { '^/api/v1/users': '/v1/users' }));
app.use('/api/v1/users/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/users'], { '^/api/v1/users': '/v1/users' }));
app.use('/api/v1/chat', validateAuth, strictLimiter, createServiceProxy(serviceRoutes['/api/v1/chat'], { '^/api/v1/chat': '/v1/chat' }));
app.use('/api/v1/chat/*', validateAuth, strictLimiter, createServiceProxy(serviceRoutes['/api/v1/chat'], { '^/api/v1/chat': '/v1/chat' }));
app.use('/api/v1/calendar', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/calendar'], { '^/api/v1/calendar': '/v1/calendar' }));
app.use('/api/v1/calendar/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/calendar'], { '^/api/v1/calendar': '/v1/calendar' }));
app.use('/api/v1/email', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/email'], { '^/api/v1/email': '/v1/email' }));
app.use('/api/v1/email/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/email'], { '^/api/v1/email': '/v1/email' }));
app.use('/api/v1/files', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/files'], { '^/api/v1/files': '/v1/files' }));
app.use('/api/v1/files/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/files'], { '^/api/v1/files': '/v1/files' }));
app.use('/api/v1/drafts', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/drafts'], { '^/api/v1/drafts': '/v1/chat/drafts' }));
app.use('/api/v1/drafts/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/drafts'], { '^/api/v1/drafts': '/v1/chat/drafts' }));
app.use('/api/v1/meetings', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/meetings'], { '^/api/v1/meetings': '/api/v1/meetings' }));
app.use('/api/v1/meetings/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/meetings'], { '^/api/v1/meetings': '/api/v1/meetings' }));
app.use('/api/v1/bookings', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/bookings'], { '^/api/v1/bookings': '/api/v1/bookings' }));
app.use('/api/v1/bookings/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/bookings'], { '^/api/v1/bookings': '/api/v1/bookings' }));
app.use('/api/v1/public/polls', standardLimiter, createServiceProxy(serviceRoutes['/api/v1/public/polls'], { '^/api/v1/public/polls': '/api/v1/public/polls' }));
app.use('/api/v1/public/polls/*', standardLimiter, createServiceProxy(serviceRoutes['/api/v1/public/polls'], { '^/api/v1/public/polls': '/api/v1/public/polls' }));
app.use('/api/v1/shipments', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/shipments'], { '^/api/v1/shipments': '/v1/shipments' }));
app.use('/api/v1/shipments/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/shipments'], { '^/api/v1/shipments': '/v1/shipments' }));
app.use('/api/v1/contacts', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/contacts'], { '^/api/v1/contacts': '/v1/contacts/' }));
app.use('/api/v1/contacts/*', validateAuth, standardLimiter, createServiceProxy(serviceRoutes['/api/v1/contacts'], { '^/api/v1/contacts': '/v1/contacts' }));

// Catch-all for undefined routes
app.use('*', (req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use((err: any, req: any, res: any, next: any) => {
    logWithContext('error', 'Global error', {
        error: err.message,
        stack: err.stack,
        method: req.method,
        path: req.path,
        requestId: req.headers['x-request-id']
    });
    res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
    });
});

const PORT = process.env.PORT || 3001;
const server = app.listen(PORT, () => {
    logWithContext('info', `Auth proxy running on port ${PORT}`);
    logWithContext('info', `Frontend URL: ${process.env.FRONTEND_URL || 'http://localhost:3000'}`);
    logWithContext('info', `Environment: ${process.env.NODE_ENV || 'development'}`);
    logWithContext('info', 'Service Routing:');
    logWithContext('info', `  /api/v1/users    → ${serviceRoutes['/api/v1/users']}`);
    logWithContext('info', `  /api/v1/chat     → ${serviceRoutes['/api/v1/chat']}`);
    logWithContext('info', `  /api/v1/calendar → ${serviceRoutes['/api/v1/calendar']}`);
    logWithContext('info', `  /api/v1/email    → ${serviceRoutes['/api/v1/email']}`);
    logWithContext('info', `  /api/v1/files    → ${serviceRoutes['/api/v1/files']}`);
    logWithContext('info', `  /api/v1/contacts → ${serviceRoutes['/api/v1/contacts']}`);
    logWithContext('info', `  /api/v1/drafts     → ${serviceRoutes['/api/v1/drafts']}`);
    logWithContext('info', `  /api/v1/meetings → ${serviceRoutes['/api/v1/meetings']}`);
    logWithContext('info', `  /api/v1/bookings → ${serviceRoutes['/api/v1/bookings']}`);
    logWithContext('info', `  /api/v1/public/polls → ${serviceRoutes['/api/v1/public/polls']}`);
    logWithContext('info', `  /api/v1/shipments → ${serviceRoutes['/api/v1/shipments']}`);
});

// Handle WebSocket upgrades
server.on('upgrade', (request: any, socket: any, head: any) => {
    logWithContext('info', 'WebSocket upgrade event');

    // Route WebSocket connections based on path
    const url = new URL(request.url || '', `http://${request.headers.host}`);
    const path = url.pathname;

    let targetService = serviceRoutes['/api/v1/users']; // Default to user service

    if (path.startsWith('/api/v1/chat')) {
        targetService = serviceRoutes['/api/v1/chat'];
    } else if (path.startsWith('/api/v1/calendar') || path.startsWith('/api/v1/email') || path.startsWith('/api/v1/files') || path.startsWith('/api/v1/contacts')) {
        targetService = serviceRoutes['/api/v1/calendar'];
    } else if (path.startsWith('/api/v1/meetings')) {
        targetService = serviceRoutes['/api/v1/meetings'];
    } else if (path.startsWith('/api/v1/bookings')) {
        targetService = serviceRoutes['/api/v1/bookings'];
    } else if (path.startsWith('/api/v1/public/polls')) {
        targetService = serviceRoutes['/api/v1/public/polls'];
    } else if (path.startsWith('/api/v1/shipments')) {
        targetService = serviceRoutes['/api/v1/shipments'];
    }

    // Create proxy for WebSocket
    const wsProxy = createServiceProxy(targetService);
    if (wsProxy && typeof wsProxy.upgrade === 'function') {
        wsProxy.upgrade(request, socket, head);
    } else {
        logWithContext('error', 'WebSocket proxy upgrade function not available');
        socket.destroy();
    }
});

// Graceful shutdown
process.on('SIGTERM', () => {
    logWithContext('info', 'Received SIGTERM, shutting down gracefully');
    server.close(() => {
        logWithContext('info', 'Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    logWithContext('info', 'Received SIGINT, shutting down gracefully');
    server.close(() => {
        logWithContext('info', 'Server closed');
        process.exit(0);
    });
});

export default app;