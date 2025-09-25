#!/usr/bin/env python3
"""
Test script to debug GUI authentication issues
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import sys
sys.path.append('/Users/gabortabi/DEV/devBlogger/devblogger/src')

from config.settings import Settings
from github.auth import GitHubAuth

def test_gui_auth():
    """Test GUI authentication components."""
    print("🔍 Testing GUI Authentication Components")
    print("=" * 50)

    # Load settings
    try:
        settings = Settings()
        print("✅ Settings loaded successfully")
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return

    # Initialize GitHub auth
    try:
        github_auth = GitHubAuth(settings)
        print("✅ GitHubAuth initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing GitHubAuth: {e}")
        return

    # Test URL generation
    try:
        auth_url = github_auth.get_authorization_url()
        print("\n🔗 Authorization URL generated:")
        print(f"   {auth_url}")

        # Test if URL is valid
        if auth_url.startswith("https://github.com/login/oauth/authorize"):
            print("✅ URL has correct format")
        else:
            print("❌ URL has incorrect format")

    except Exception as e:
        print(f"\n❌ Error generating authorization URL: {e}")
        return

    # Test manual authentication flow
    print("\n🔄 Testing manual authentication flow...")
    print("   1. Copy the URL above")
    print("   2. Open it in your browser")
    print("   3. Authorize the application")
    print("   4. The browser should redirect to: http://localhost:8080/callback?code=...&state=...")
    print("   5. The callback server should receive the authorization code")

    # Start callback server
    try:
        print("\n🌐 Starting callback server on port 8080...")
        print("   Server is running and waiting for callback...")

        # Import and start server
        import http.server
        import socketserver
        import threading
        from urllib.parse import parse_qs, urlparse

        class TestCallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                print(f"\n📨 Callback received: {self.path}")

                # Parse query parameters
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                print(f"📋 Query parameters: {query_params}")

                # Get authorization code
                auth_code = query_params.get('code', [''])[0]
                if auth_code:
                    print(f"🔑 Authorization code received: {auth_code[:10]}...")

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    response_html = '''
                    <!DOCTYPE html>
                    <html>
                    <head><title>Success</title></head>
                    <body>
                        <h1>✓ Authentication Successful!</h1>
                        <p>You can now close this window and return to the application.</p>
                    </body>
                    </html>
                    '''

                    self.wfile.write(response_html.encode())
                    print("🌐 Success response sent to browser")
                else:
                    print("❌ No authorization code received")
                    self.send_error(400, "No authorization code received")

            def log_message(self, format, *args):
                print(f"HTTP: {format % args}")

        # Start server
        server = socketserver.TCPServer(("", 8080), TestCallbackHandler)
        print("✅ Callback server started successfully")

        # Keep server running
        try:
            print("⏳ Waiting for authentication callback...")
            print("   (Press Ctrl+C to stop)")
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
        finally:
            server.shutdown()

    except Exception as e:
        print(f"\n❌ Error starting callback server: {e}")

if __name__ == "__main__":
    test_gui_auth()
