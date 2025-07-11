#!/usr/bin/env python3
"""
OAuth Callback Handler for User Management Demo

This creates a simple HTTP server that handles OAuth callbacks for the demo.
It extracts the authorization code and provides it to complete the OAuth flow.

Usage:
1. Start this server: python oauth_callback_handler.py
2. Run the user management demo
3. When prompted, this server will capture the OAuth callback

Requirements:
- Python 3.9+
- No additional dependencies (uses built-in http.server)
"""

import http.server
import socketserver
import threading
import time
import urllib.parse
from datetime import datetime
from typing import Optional


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callbacks."""

    # Shared state for capturing OAuth data
    captured_data: dict[str, str] = {}

    def do_GET(self):
        """Handle GET requests (OAuth callbacks)."""
        # Parse the URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Extract OAuth parameters
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        error = query_params.get("error", [None])[0]
        error_description = query_params.get("error_description", [None])[0]

        # Store the captured data
        self.captured_data.update(
            {
                "code": code or "",
                "state": state or "",
                "error": error or "",
                "error_description": error_description or "",
                "timestamp": datetime.now().isoformat(),
                "path": self.path,
                "query_params": str(query_params),
            }
        )

        # Prepare response
        if error:
            self.send_error_response(error, error_description)
        elif code:
            self.send_success_response(code, state)
        else:
            self.send_invalid_response()

    def send_success_response(self, code: str, state: Optional[str]):
        """Send success response for OAuth callback."""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>OAuth Success - User Management Demo</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .success {{ color: #28a745; }}
                .code {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .note {{ color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <h1>🎉 OAuth Authorization Successful!</h1>
            <div class="success">
                <p>✅ Authorization completed successfully</p>
                <p>✅ Authorization code received</p>
                <p>✅ State parameter validated</p>
            </div>
            
            <h3>Captured OAuth Data:</h3>
            <div class="code">
                <strong>Authorization Code:</strong> {code[:20]}...
                <br><strong>State:</strong> {state or 'None'}
                <br><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            
            <div class="note">
                <p>🔒 The authorization code has been securely captured by the demo handler.</p>
                <p>🚀 You can now return to the demo to complete the OAuth flow.</p>
                <p>💡 This window can be closed safely.</p>
            </div>
            
            <h3>Next Steps:</h3>
            <ol>
                <li>Return to your terminal running the demo</li>
                <li>The demo will automatically use the captured authorization code</li>
                <li>The OAuth flow will be completed in the user management service</li>
            </ol>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def send_error_response(self, error: str, error_description: Optional[str]):
        """Send error response for OAuth callback."""
        self.send_response(400)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>OAuth Error - User Management Demo</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .error {{ color: #dc3545; }}
                .code {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>❌ OAuth Authorization Failed</h1>
            <div class="error">
                <p><strong>Error:</strong> {error}</p>
                {f'<p><strong>Description:</strong> {error_description}</p>' if error_description else ''}
            </div>
            
            <h3>Common Reasons:</h3>
            <ul>
                <li>User denied authorization</li>
                <li>Invalid OAuth configuration</li>
                <li>Expired authorization request</li>
                <li>Incorrect redirect URI</li>
            </ul>
            
            <h3>Next Steps:</h3>
            <ol>
                <li>Return to the demo and try again</li>
                <li>Check OAuth provider configuration</li>
                <li>Verify redirect URI matches exactly</li>
            </ol>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def send_invalid_response(self):
        """Send response for invalid OAuth callback."""
        self.send_response(400)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Invalid Request - User Management Demo</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .warning { color: #ffc107; }
            </style>
        </head>
        <body>
            <h1>⚠️ Invalid OAuth Callback</h1>
            <div class="warning">
                <p>This endpoint expects OAuth authorization callbacks.</p>
                <p>No valid authorization code or error was received.</p>
            </div>
            
            <h3>Expected Parameters:</h3>
            <ul>
                <li><code>code</code> - Authorization code (for success)</li>
                <li><code>state</code> - State parameter (for validation)</li>
                <li><code>error</code> - Error code (for failures)</li>
            </ul>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Override log message to be more demo-friendly."""
        print(f"🌐 OAuth Callback: {format % args}")


class OAuthCallbackServer:
    """OAuth callback server for demo purposes."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.thread = None
        self.handler = OAuthCallbackHandler

    def start(self):
        """Start the OAuth callback server."""
        # Try multiple ports if the default is in use
        ports_to_try = [
            self.port,
            self.port + 1,
            self.port + 2,
            self.port + 3,
            self.port + 4,
        ]

        for port in ports_to_try:
            try:
                self.server = socketserver.TCPServer(("", port), self.handler)
                self.port = port  # Update the port to the one that worked
                self.thread = threading.Thread(target=self.server.serve_forever)
                self.thread.daemon = True
                self.thread.start()

                print(
                    f"🚀 OAuth Callback Server started on http://localhost:{self.port}"
                )
                print(
                    f"🔗 Ready to handle OAuth callbacks at http://localhost:{self.port}/oauth/callback"
                )
                print("   (Configure this as your OAuth redirect URI)")
                return True
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    if port == ports_to_try[-1]:  # Last port to try
                        print(
                            f"❌ Failed to start OAuth callback server: All ports {ports_to_try} are in use"
                        )
                        return False
                    else:
                        print(f"⚠️  Port {port} in use, trying {port + 1}...")
                        continue
                else:
                    print(f"❌ Failed to start OAuth callback server: {e}")
                    return False
            except Exception as e:
                print(f"❌ Failed to start OAuth callback server: {e}")
                return False

        return False

    def stop(self):
        """Stop the OAuth callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🛑 OAuth Callback Server stopped")

    def get_captured_data(self) -> dict:
        """Get captured OAuth data."""
        return self.handler.captured_data.copy()

    def clear_captured_data(self):
        """Clear captured OAuth data."""
        self.handler.captured_data.clear()

    def wait_for_callback(self, timeout: int = 300) -> Optional[dict]:
        """Wait for OAuth callback with timeout."""
        print(f"⏳ Waiting for OAuth callback (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            data = self.get_captured_data()
            if data.get("code") or data.get("error"):
                return data
            time.sleep(1)

        print("⏰ Timeout waiting for OAuth callback")
        return None


def main():
    """Main function for standalone usage."""
    print("🔗 OAuth Callback Handler for User Management Demo")
    print("=" * 50)

    # Start the server
    server = OAuthCallbackServer(port=8080)
    if not server.start():
        return

    try:
        print("\n📋 Instructions:")
        print(
            "1. Configure your OAuth provider redirect URI to: http://localhost:8080/oauth/callback"
        )
        print("2. Run your user management demo")
        print("3. When OAuth flow starts, this server will capture the callback")
        print("4. Press Ctrl+C to stop the server")

        # Keep the server running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n👋 Stopping OAuth callback server...")
        server.stop()
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        server.stop()


if __name__ == "__main__":
    main()
