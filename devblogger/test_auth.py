#!/usr/bin/env python3
"""
Test script to manually test GitHub OAuth authentication
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.config.settings import Settings
from src.github.auth import GitHubAuth

def test_github_auth():
    """Test GitHub authentication manually."""
    print("🔍 Testing GitHub OAuth Authentication")
    print("=" * 50)

    # Load settings
    settings = Settings()
    print(f"📋 Settings loaded from: {settings.config_file}")

    # Create GitHub auth instance
    github_auth = GitHubAuth(settings)

    # Check configuration
    print("🔧 Configuration Check:")
    print(f"   Client ID: {github_auth.client_id}")
    print(f"   Client Secret: {'*' * len(github_auth.client_secret) if github_auth.client_secret else 'Not set'}")
    print(f"   Redirect URI: {github_auth.redirect_uri}")
    print(f"   Scope: {github_auth.scope}")
    print(f"   Configured: {github_auth.is_configured()}")

    if not github_auth.is_configured():
        print("❌ GitHub OAuth is not configured!")
        return False

    print("✅ GitHub OAuth is configured correctly")

    # Test authorization URL generation
    try:
        auth_url = github_auth.get_authorization_url()
        print("🔗 Authorization URL generated successfully:")
        print(f"   {auth_url}")
        print()
        print("🌐 Please open this URL in your browser to test authentication:")
        print(f"   {auth_url}")
        print()
        print("📝 After authorization, the callback should come to:")
        print(f"   {github_auth.redirect_uri}")

        return True

    except Exception as e:
        print(f"❌ Error generating authorization URL: {e}")
        return False

if __name__ == "__main__":
    test_github_auth()
