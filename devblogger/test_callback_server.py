#!/usr/bin/env python3
"""
Test the callback server to see if it's receiving the GitHub OAuth callback
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.github.auth import GitHubAuth
import time
import threading

def test_callback_server():
    """Test if the callback server is working properly."""
    print("🔧 Testing GitHub OAuth callback server...")
    
    # Initialize settings and auth
    settings = Settings()
    github_auth = GitHubAuth(settings)
    
    print(f"✅ GitHub OAuth configured: {github_auth.is_configured()}")
    print(f"✅ Client ID: {github_auth.client_id[:10]}..." if github_auth.client_id else "❌ No client ID")
    print(f"✅ Redirect URI: {github_auth.redirect_uri}")
    
    try:
        # Start the callback server
        print("🚀 Starting callback server...")
        github_auth._start_callback_server()
        print("✅ Callback server started successfully")
        
        # Generate authorization URL
        auth_url = github_auth.get_authorization_url()
        print(f"🔗 Authorization URL: {auth_url}")
        print("\n📋 Instructions:")
        print("1. Copy the URL above")
        print("2. Open it in your browser")
        print("3. Complete GitHub authorization")
        print("4. Watch for callback messages below")
        print("5. Press Ctrl+C to stop\n")
        
        # Monitor for callback
        print("⏳ Waiting for OAuth callback...")
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if github_auth.auth_code:
                print(f"✅ Authorization code received: {github_auth.auth_code[:10]}...")
                print("🔄 Attempting token exchange...")
                
                success = github_auth._exchange_code_for_token()
                if success:
                    print("✅ Token exchange successful!")
                    print(f"✅ Access token: {github_auth.access_token[:20]}..." if github_auth.access_token else "❌ No access token")
                    
                    success = github_auth._get_user_data()
                    if success:
                        print("✅ User data retrieved successfully!")
                        print(f"✅ User: {github_auth.user_data.get('login', 'unknown')}")
                        print("🎉 Authentication completed successfully!")
                        break
                    else:
                        print("❌ Failed to get user data")
                else:
                    print("❌ Token exchange failed")
                    
            if elapsed > 300:  # 5 minutes timeout
                print("⏰ Timeout after 5 minutes")
                break
                
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🛑 Stopping callback server...")
        github_auth._stop_callback_server()
        print("✅ Test completed")

if __name__ == "__main__":
    test_callback_server()
