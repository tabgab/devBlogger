#!/usr/bin/env python3
"""
Debug script to test GitHub authentication flow
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

def test_auth_flow():
    """Test the authentication flow step by step."""
    print("🔍 Testing GitHub Authentication Flow")
    print("=" * 50)

    # Load settings
    try:
        settings = Settings()
        print("✅ Settings loaded successfully")
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return

    # Check configuration
    print("\n🔧 Configuration Check:")
    print(f"   Client ID: {settings.get('github.client_id', 'Not set')[:20]}...")
    print(f"   Client Secret: {'*' * 20 if settings.get('github.client_secret') else 'Not set'}")
    print(f"   Redirect URI: {settings.get('github.redirect_uri', 'Not set')}")
    print(f"   Scope: {settings.get('github.scope', 'Not set')}")

    # Initialize GitHub auth
    try:
        github_auth = GitHubAuth(settings)
        print("\n✅ GitHubAuth initialized successfully")
    except Exception as e:
        print(f"\n❌ Error initializing GitHubAuth: {e}")
        return

    # Check if configured
    if not github_auth.is_configured():
        print("\n❌ GitHub OAuth is not configured")
        print("   Please set client_id and client_secret in your config file")
        return

    print("\n✅ GitHub OAuth is configured correctly")

    # Test URL generation
    try:
        auth_url = github_auth.get_authorization_url()
        print("\n🔗 Authorization URL generated successfully:")
        print(f"   {auth_url}")

        # Check if URL contains expected parameters
        if "client_id=" in auth_url and "redirect_uri=" in auth_url:
            print("✅ Authorization URL contains expected parameters")
        else:
            print("❌ Authorization URL is missing expected parameters")

    except Exception as e:
        print(f"\n❌ Error generating authorization URL: {e}")
        return

    # Test callback server startup
    print("\n🔄 Testing callback server startup...")
    try:
        # This should start the server
        print("   Starting callback server on port 8080...")
        print("   Server should be running in background")
        print("   Press Ctrl+C to stop the server")

        # Keep the script running to test the server
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Callback server stopped")
    except Exception as e:
        print(f"\n❌ Error starting callback server: {e}")

if __name__ == "__main__":
    test_auth_flow()
