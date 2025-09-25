#!/usr/bin/env python3
"""
DevBlogger - GitHub authentication handling
"""

import json
import secrets
import hashlib
import base64
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
import http.server
import socketserver
import threading
import webbrowser
import time
from pathlib import Path

try:
    import customtkinter as ctk
    from customtkinter import CTkToplevel, CTkLabel, CTkButton, CTkProgressBar
except ImportError:
    ctk = None

from ..config.settings import Settings


class GitHubAuth:
    """GitHub OAuth authentication handler."""

    def __init__(self, settings: Settings):
        """Initialize GitHub authentication."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # OAuth configuration
        self.client_id = self.settings.get("github.client_id", "")
        self.client_secret = self.settings.get("github.client_secret", "")
        self.redirect_uri = self.settings.get("github.redirect_uri", "http://localhost:8080/callback")
        self.scope = self.settings.get("github.scope", "read:user repo")

        # State for OAuth flow
        self.state = None
        self.auth_code = None
        self.access_token = None
        self.user_data = None

        # Server for handling callback
        self.callback_server = None
        self.server_thread = None

    def is_configured(self) -> bool:
        """Check if GitHub OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return bool(self.access_token and self.user_data)

    def get_authorization_url(self) -> str:
        """Generate GitHub OAuth authorization URL."""
        if not self.is_configured():
            raise ValueError("GitHub OAuth is not configured. Please set client_id and client_secret.")

        # Generate secure random state
        self.state = secrets.token_urlsafe(32)

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': self.state,
            'response_type': 'code'
        }

        base_url = "https://github.com/login/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"

    def authenticate(self, parent_window=None) -> bool:
        """Start OAuth authentication flow."""
        self.logger.info("Starting OAuth authentication flow")
        if not self.is_configured():
            self.logger.error("GitHub OAuth is not configured")
            raise ValueError("GitHub OAuth is not configured")

        try:
            self.logger.info("Starting callback server")
            # Start local server to handle callback
            self._start_callback_server()

            # Open browser for authentication
            auth_url = self.get_authorization_url()
            self.logger.info(f"Opening browser to: {auth_url}")

            if parent_window and ctk:
                # Show progress dialog
                self.logger.info("Showing authentication dialog")
                self._show_auth_dialog(parent_window)

            # Open browser - handle gracefully
            try:
                print(f"🔗 Opening browser for GitHub authentication...")
                print(f"🔗 If browser doesn't open automatically, visit: {auth_url}")
                webbrowser.open(auth_url)
                self.logger.info("Browser opened successfully")
            except Exception as e:
                self.logger.error(f"Browser couldn't be opened automatically: {e}")
                print(f"🔗 Browser couldn't be opened automatically: {e}")
                print(f"🔗 Please manually open this URL in your browser: {auth_url}")

            # Wait for authentication to complete
            self.logger.info("Waiting for authentication to complete")
            self._wait_for_authentication()

            # Exchange authorization code for access token
            self.logger.info("Exchanging authorization code for access token")
            if self._exchange_code_for_token():
                # Get user data
                self.logger.info("Authentication successful, getting user data")
                self._get_user_data()
                return True
            else:
                self.logger.error("Authentication failed - could not exchange code for token")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}", exc_info=True)
            return False
        finally:
            self.logger.info("Stopping callback server")
            self._stop_callback_server()

    def _start_callback_server(self):
        """Start local HTTP server to handle OAuth callback."""
        try:
            # Find available port
            port = self._find_available_port(8080)

            class CallbackHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.logger.info(f"Callback received: {self.path}")

                    # Parse query parameters
                    parsed_url = urlparse(self.path)
                    query_params = parse_qs(parsed_url.query)
                    self.logger.info(f"Query parameters: {query_params}")

                    # Verify state parameter
                    returned_state = query_params.get('state', [''])[0]
                    expected_state = CallbackHandler.auth_instance.state
                    self.logger.info(f"Received state: {returned_state}")
                    self.logger.info(f"Expected state: {expected_state}")

                    if returned_state != expected_state:
                        self.logger.error(f"State mismatch! Received: {returned_state}, Expected: {expected_state}")
                        self.send_error(400, "Invalid state parameter")
                        return

                    # Get authorization code
                    self.auth_code = query_params.get('code', [''])[0]
                    self.logger.info(f"Authorization code received: {self.auth_code[:10]}..." if self.auth_code else "No authorization code received")

                    if not self.auth_code:
                        self.logger.error("No authorization code in callback")
                        self.send_error(400, "No authorization code received")
                        return

                    # Store the authorization code in the auth instance
                    CallbackHandler.auth_instance.auth_code = self.auth_code
                    self.logger.info("Authorization code stored successfully")

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    response_html = '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>DevBlogger - Authentication Successful</title>
                        <style>
                            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                            .success { color: #28a745; font-size: 24px; }
                            .message { color: #6c757d; font-size: 16px; margin-top: 20px; }
                        </style>
                    </head>
                    <body>
                        <div class="success">✓ Authentication Successful!</div>
                        <div class="message">You can now close this window and return to DevBlogger.</div>
                    </body>
                    </html>
                    '''

                    self.wfile.write(response_html.encode())
                    self.logger.info("Success response sent to browser")

                def log_message(self, format, *args):
                    # Add logger to callback handler
                    self.logger = CallbackHandler.auth_instance.logger
                    self.logger.info(f"HTTP {format % args}")

            # Store reference to auth instance
            CallbackHandler.auth_instance = self

            # Start server in a separate thread
            self.callback_server = socketserver.TCPServer(("", port), CallbackHandler)
            self.server_thread = threading.Thread(target=self.callback_server.serve_forever, daemon=True)
            self.server_thread.start()
            self.logger.info(f"Callback server started on port {port}")

        except Exception as e:
            self.logger.error(f"Failed to start callback server: {e}")
            raise

    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port."""
        import socket

        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", port))
                    return port
            except OSError:
                continue

        raise RuntimeError(f"No available port found in range {start_port}-{start_port + 9}")

    def _wait_for_authentication(self, timeout: int = 300):
        """Wait for OAuth authentication to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.auth_code:
                self.logger.info("Authorization code received")
                break
            time.sleep(0.1)

        if not self.auth_code:
            raise TimeoutError("Authentication timeout - no authorization code received")

    def _exchange_code_for_token(self) -> bool:
        """Exchange authorization code for access token."""
        import requests

        if not self.auth_code:
            self.logger.error("No authorization code available for token exchange")
            return False

        try:
            self.logger.info(f"Starting token exchange with code: {self.auth_code[:10]}...")

            # Prepare token exchange request
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': self.auth_code,
                'redirect_uri': self.redirect_uri
            }

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            self.logger.info(f"Sending token exchange request to: https://github.com/login/oauth/access_token")
            self.logger.info(f"Request data: client_id={self.client_id[:10]}..., redirect_uri={self.redirect_uri}")

            # Exchange code for token
            response = requests.post(
                'https://github.com/login/oauth/access_token',
                data=data,
                headers=headers,
                timeout=30
            )

            self.logger.info(f"Token exchange response status: {response.status_code}")
            self.logger.info(f"Token exchange response headers: {dict(response.headers)}")

            if response.status_code == 200:
                token_data = response.json()
                self.logger.info(f"Token exchange response data: {token_data}")

                self.access_token = token_data.get('access_token')
                self.logger.info(f"Access token obtained: {self.access_token[:20]}..." if self.access_token else "No access token in response")

                if token_data.get('token_type') != 'bearer':
                    self.logger.warning(f"Unexpected token type: {token_data.get('token_type')}")

                if 'error' in token_data:
                    self.logger.error(f"Token exchange error: {token_data['error']}")
                    self.logger.error(f"Error description: {token_data.get('error_description', 'No description')}")
                    return False

                self.logger.info("Successfully obtained access token")
                return True
            else:
                self.logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                self.logger.error(f"Full response: {response.content}")
                return False

        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {e}", exc_info=True)
            return False

    def _get_user_data(self) -> bool:
        """Get authenticated user data from GitHub API."""
        import requests

        if not self.access_token:
            self.logger.error("No access token available for user data retrieval")
            return False

        try:
            self.logger.info(f"Getting user data with access token: {self.access_token[:20]}...")

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'DevBlogger/1.0'
            }

            self.logger.info("Sending user data request to: https://api.github.com/user")

            # Get user data
            response = requests.get(
                'https://api.github.com/user',
                headers=headers,
                timeout=30
            )

            self.logger.info(f"User data response status: {response.status_code}")
            self.logger.info(f"User data response headers: {dict(response.headers)}")

            if response.status_code == 200:
                self.user_data = response.json()
                self.logger.info(f"User data response: {self.user_data}")
                self.logger.info(f"Successfully authenticated as: {self.user_data.get('login', 'unknown')}")
                return True
            else:
                self.logger.error(f"Failed to get user data: {response.status_code} - {response.text}")
                self.logger.error(f"Full response: {response.content}")
                return False

        except Exception as e:
            self.logger.error(f"Error getting user data: {e}", exc_info=True)
            return False

    def _show_auth_dialog(self, parent_window):
        """Show authentication progress dialog."""
        if not ctk:
            return

        try:
            dialog = CTkToplevel(parent_window)
            dialog.title("GitHub Authentication")
            dialog.geometry("400x200")
            dialog.resizable(False, False)

            # Center dialog on parent without modal behavior to prevent blocking
            dialog.transient(parent_window)
            # Don't use grab_set() as it can cause the main thread to hang

            # Dialog content
            title_label = CTkLabel(
                dialog,
                text="GitHub Authentication",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.pack(pady=(20, 10))

            message_label = CTkLabel(
                dialog,
                text="Opening browser for GitHub authentication...\nPlease complete the login process.",
                font=ctk.CTkFont(size=12),
                wraplength=350
            )
            message_label.pack(pady=(0, 20))

            progress_bar = CTkProgressBar(dialog, mode="indeterminate")
            progress_bar.pack(pady=(0, 20), padx=40, fill="x")
            progress_bar.start()

            # Store dialog reference
            self.auth_dialog = dialog

        except Exception as e:
            self.logger.error(f"Error showing auth dialog: {e}")

    def _stop_callback_server(self):
        """Stop the callback server."""
        if self.callback_server:
            try:
                self.callback_server.shutdown()
                self.callback_server.server_close()
                self.callback_server = None
                self.server_thread = None
            except Exception as e:
                self.logger.error(f"Error stopping callback server: {e}")

    def logout(self):
        """Clear authentication data."""
        self.access_token = None
        self.user_data = None
        self.auth_code = None
        self.state = None
        self.logger.info("User logged out")

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        return self.user_data or {}

    def get_access_token(self) -> Optional[str]:
        """Get current access token."""
        return self.access_token

    def refresh_token(self) -> bool:
        """Refresh access token (not needed for GitHub OAuth app flow)."""
        # GitHub OAuth apps don't support token refresh
        # Users need to re-authenticate when token expires
        return False
