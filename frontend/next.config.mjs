/** @type {import('next').NextConfig} */
const nextConfig = {
    eslint: {
        ignoreDuringBuilds: true,
    },
    typescript: {
        ignoreBuildErrors: true,
    },
    images: {
        unoptimized: true,
    },
    async headers() {
        // Get gateway URL from environment variable
        const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001';
        const isProduction = process.env.NODE_ENV === 'production';

        // Build CSP directives
        const cspDirectives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            `connect-src 'self' ${gatewayUrl} https://login.microsoftonline.com https://graph.microsoft.com https://accounts.google.com https://www.googleapis.com`,
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'"
        ];

        // Only add upgrade-insecure-requests in production
        if (isProduction) {
            cspDirectives.push("upgrade-insecure-requests");
            // In production, also add HTTPS version of gateway URL by appending to existing connect-src
            if (gatewayUrl.startsWith('http://')) {
                const httpsGatewayUrl = gatewayUrl.replace('http://', 'https://');
                const connectSrcIndex = cspDirectives.findIndex((directive) => directive.startsWith("connect-src "));
                if (connectSrcIndex !== -1 && !cspDirectives[connectSrcIndex].includes(httpsGatewayUrl)) {
                    cspDirectives[connectSrcIndex] = `${cspDirectives[connectSrcIndex]} ${httpsGatewayUrl}`;
                }
            }
        }

        return [
            {
                source: '/(.*)',
                headers: [
                    {
                        key: 'Content-Security-Policy',
                        value: cspDirectives.join('; ')
                    },
                    {
                        key: 'X-Content-Type-Options',
                        value: 'nosniff'
                    },
                    {
                        key: 'X-Frame-Options',
                        value: 'DENY'
                    },
                    {
                        key: 'X-XSS-Protection',
                        value: '1; mode=block'
                    },
                    {
                        key: 'Referrer-Policy',
                        value: 'strict-origin-when-cross-origin'
                    }
                ]
            }
        ];
    }
}

export default nextConfig
