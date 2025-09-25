#!/usr/bin/env python3
"""
Test script to test the complete GitHub OAuth authentication flow
"""

import sys
import os
import time
import threading
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
sys.path.append(os.path.dirname(__file__))

from src.config.settings import Settings
from src.github.auth import GitHubAuth

def test_auth_flow():
    """Test the complete GitHub OAuth authentication flow."""
    print("🔍 Testing Complete GitHub OAuth Authentication Flow")
    print("=" * 60)

    # Load settings
    settings = Settings()

    # Temporarily change redirect URI for testing
    original_redirect_uri = settings.get("github.redirect_uri", "http://localhost:8080/callback")
    settings.set("github.redirect_uri", "http://localhost:8081/callback")

    github_auth = GitHubAuth(settings)

    print("✅ Configuration loaded successfully")
    print(f"   Client ID: {github_auth.client_id[:10]}...")
    print(f"   Redirect URI: {github_auth.redirect_uri}")

    # Start a simple callback server to capture the authorization code
    print("\n🔄 Starting callback server on port 8080...")

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
                TestCallbackHandler.auth_code = auth_code

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                response_html = '''
                <!DOCTYPE html>
                <html>
                <head><title>DevBlogger Test - Success</title></head>
                <body>
                    <h1>✅ Authentication Successful!</h1>
                    <p>Authorization code received. You can close this window.</p>
                    <p><strong>Code:</strong> {}...</p>
                </body>
                </html>
                '''.format(auth_code[:10])

                self.wfile.write(response_html.encode())
                print("🌐 Success response sent to browser")
            else:
                print("❌ No authorization code received")
                self.send_error(400, "No authorization code received")

        def log_message(self, format, *args):
            print(f"HTTP: {format % args}")

    # Start server on a different port to avoid conflicts
    TestCallbackHandler.auth_code = None
    server = socketserver.TCPServer(("", 8081), TestCallbackHandler)

    def run_server():
        print("🌐 Callback server running on http://localhost:8080")
        server.serve_forever()

    # Start server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    print("\n🔗 Testing authorization URL generation...")
    try:
        auth_url = github_auth.get_authorization_url()
        print(f"✅ Authorization URL: {auth_url}")

        print("\n🌐 Please open this URL in your browser:")
        print(f"   {auth_url}")
        print("\n⏳ Waiting for authorization callback...")

        # Wait for authorization code
        timeout = 60  # 1 minute timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            if TestCallbackHandler.auth_code:
                print(f"\n🎉 Authorization code received: {TestCallbackHandler.auth_code[:20]}...")
                break
            time.sleep(1)

        if TestCallbackHandler.auth_code:
            print("\n🔄 Testing token exchange...")
            # Test token exchange
            github_auth.auth_code = TestCallbackHandler.auth_code
            if github_auth._exchange_code_for_token():
                print(f"✅ Token exchange successful!")
                print(f"   Access token: {github_auth.access_token[:20]}...")

                print("\n🔄 Testing user data retrieval...")
                if github_auth._get_user_data():
                    print(f"✅ User data retrieved successfully!")
                    print(f"   User: {github_auth.user_data.get('login', 'Unknown')}")
                    print(f"   Name: {github_auth.user_data.get('name', 'Unknown')}")
                    print(f"   Email: {github_auth.user_data.get('email', 'Unknown')}")
                else:
                    print("❌ Failed to get user data")
            else:
                print("❌ Token exchange failed")
        else:
            print(f"\n⏰ Timeout after {timeout} seconds - no authorization code received")
            print("❌ Authentication test failed")

    except Exception as e:
        print(f"❌ Error during authentication test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n🛑 Stopping callback server...")
        server.shutdown()
        server_thread.join(timeout=2)
        print("✅ Test completed")

if __name__ == "__main__":
    test_auth_flow()
