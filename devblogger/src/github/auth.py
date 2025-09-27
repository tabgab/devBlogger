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

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings


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
        self.log_callback = None
        self.success_callback = None
        self.token_exchange_in_progress = False
        # UI scheduler hook to ensure callbacks run on Tk main thread
        self.ui_after = None

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

    def authenticate(self, parent_window=None, log_callback=None) -> bool:
        """Start OAuth authentication flow."""
        self.logger.info("Starting OAuth authentication flow")
        self.log_callback = log_callback  # Store callback for logging

        if not self.is_configured():
            self.logger.error("GitHub OAuth is not configured")
            self._log("❌ GitHub OAuth is not configured. Please check your settings.")
            raise ValueError("GitHub OAuth is not configured")

        try:
            self._log("🔄 Starting callback server...")
            self.logger.info("Starting callback server")
            # Start local server to handle callback
            self._start_callback_server()

            # Generate authorization URL
            auth_url = self.get_authorization_url()
            self.logger.info(f"Authorization URL: {auth_url}")
            self._log(f"🔗 Authorization URL generated: {auth_url}")

            # Always log the URL for manual access
            self._log("🔗 Authorization URL generated successfully!")
            self._log(f"🌐 URL: {auth_url}")
            self._log("📋 Copy the URL above and open it in your browser")

            # Try to display URL in dialog if available (don't fail if attributes don't exist)
            if parent_window and ctk:
                try:
                    # Try to display in manual URL text area (fallback method)
                    if hasattr(parent_window, 'manual_url_text'):
                        parent_window.manual_url_text.configure(state="normal")
                        parent_window.manual_url_text.delete("1.0", "end")
                        parent_window.manual_url_text.insert("1.0", auth_url)
                        parent_window.manual_url_text.configure(state="disabled")
                        self._log("📋 Authorization URL displayed in dialog")
                    else:
                        self._log("⚠️ Dialog doesn't have URL display area - check logs for URL")

                    self._log("🔗 URL is ready to copy or open in browser")
                except Exception as e:
                    self.logger.error(f"Error displaying URL in dialog: {e}")
                    self._log(f"⚠️ Error displaying URL in dialog: {e}")
                    # Don't fail the entire authentication if URL display fails

            if parent_window and ctk:
                # Show progress dialog
                self.logger.info("Showing authentication dialog")
                self._log("📋 Showing authentication dialog...")
                self._show_auth_dialog(parent_window)

            # Open browser - handle gracefully
            try:
                print(f"🔗 Opening browser for GitHub authentication...")
                print(f"🔗 If browser doesn't open automatically, visit: {auth_url}")
                webbrowser.open(auth_url)
                self.logger.info("Browser opened successfully")
                self._log("🌐 Browser opened successfully")
            except Exception as e:
                self.logger.error(f"Browser couldn't be opened automatically: {e}")
                self._log(f"⚠️ Browser couldn't be opened automatically: {e}")
                print(f"🔗 Browser couldn't be opened automatically: {e}")
                print(f"🔗 Please manually open this URL in your browser: {auth_url}")

            # Wait for authentication to complete
            self.logger.info("Waiting for authentication to complete")
            self._log("⏳ Waiting for authentication to complete...")
            self._wait_for_authentication()

            # Exchange authorization code for access token
            self.logger.info("Exchanging authorization code for access token")
            self._log("🔄 Exchanging authorization code for access token...")
            if self._exchange_code_for_token():
                # Get user data
                self.logger.info("Authentication successful, getting user data")
                self._log("✅ Authentication successful, getting user data...")
                self._get_user_data()
                self._log("🎉 Authentication completed successfully!")
                return True
            else:
                self.logger.error("Authentication failed - could not exchange code for token")
                self._log("❌ Authentication failed - could not exchange code for token")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}", exc_info=True)
            self._log(f"❌ Authentication error: {e}")
            return False
        finally:
            self.logger.info("Stopping callback server")
            self._log("🛑 Stopping callback server...")
            self._stop_callback_server()

    def _log(self, message: str):
        """Log a message using the callback if available."""
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception as e:
                self.logger.error(f"Error in log callback: {e}")
        else:
            self.logger.info(f"LOG: {message}")

    def _start_callback_server(self):
        """Start local HTTP server to handle OAuth callback."""
        try:
            # Use the port from redirect_uri instead of finding an available one
            from urllib.parse import urlparse
            parsed_uri = urlparse(self.redirect_uri)
            port = parsed_uri.port or 8080
            self.logger.info(f"Using redirect URI port: {port}")

            class CallbackHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    # Use the auth instance logger instead of self.logger
                    CallbackHandler.auth_instance.logger.info(f"Callback received: {self.path}")
                    CallbackHandler.auth_instance._log(f"📨 Callback received: {self.path}")

                    # Parse query parameters
                    parsed_url = urlparse(self.path)
                    query_params = parse_qs(parsed_url.query)
                    CallbackHandler.auth_instance.logger.info(f"Query parameters: {query_params}")

                    # Verify state parameter
                    returned_state = query_params.get('state', [''])[0]
                    expected_state = CallbackHandler.auth_instance.state
                    CallbackHandler.auth_instance.logger.info(f"Received state: {returned_state}")
                    CallbackHandler.auth_instance.logger.info(f"Expected state: {expected_state}")

                    if returned_state != expected_state:
                        CallbackHandler.auth_instance.logger.error(f"State mismatch! Received: {returned_state}, Expected: {expected_state}")
                        CallbackHandler.auth_instance._log(f"❌ State mismatch! Received: {returned_state}, Expected: {expected_state}")
                        self.send_error(400, "Invalid state parameter")
                        return

                    # Get authorization code
                    self.auth_code = query_params.get('code', [''])[0]
                    CallbackHandler.auth_instance.logger.info(f"Authorization code received: {self.auth_code[:10]}..." if self.auth_code else "No authorization code received")
                    CallbackHandler.auth_instance._log(f"🔑 Authorization code received: {self.auth_code[:10]}..." if self.auth_code else "❌ No authorization code received")

                    if not self.auth_code:
                        CallbackHandler.auth_instance.logger.error("No authorization code in callback")
                        CallbackHandler.auth_instance._log("❌ No authorization code in callback")
                        self.send_error(400, "No authorization code received")
                        return

                    # Store the authorization code in the auth instance
                    CallbackHandler.auth_instance.auth_code = self.auth_code
                    CallbackHandler.auth_instance.logger.info("Authorization code stored successfully")
                    CallbackHandler.auth_instance._log("✅ Authorization code stored successfully")

                    # Check if token exchange is already in progress or completed
                    if CallbackHandler.auth_instance.token_exchange_in_progress:
                        CallbackHandler.auth_instance.logger.info("Token exchange already in progress, skipping")
                        CallbackHandler.auth_instance._log("⚠️ Token exchange already in progress, skipping")
                    elif CallbackHandler.auth_instance.access_token:
                        CallbackHandler.auth_instance.logger.info("Already have access token, skipping token exchange")
                        CallbackHandler.auth_instance._log("✅ Already authenticated, skipping token exchange")
                    else:
                        # Mark token exchange as in progress
                        CallbackHandler.auth_instance.token_exchange_in_progress = True
                        
                        # Immediately trigger token exchange
                        CallbackHandler.auth_instance.logger.info("Triggering immediate token exchange...")
                        CallbackHandler.auth_instance._log("🔄 Starting token exchange immediately...")

                        # Trigger token exchange in a separate thread to avoid blocking
                        import threading
                        def exchange_token():
                            try:
                                success = CallbackHandler.auth_instance._exchange_code_for_token()
                                if success:
                                    CallbackHandler.auth_instance._log("✅ Token exchange successful!")
                                    success = CallbackHandler.auth_instance._get_user_data()
                                    if success:
                                        CallbackHandler.auth_instance._log("✅ User data retrieved successfully!")
                                        CallbackHandler.auth_instance._log("🎉 Authentication completed successfully!")
                                        
                                        # Call success callback if available - schedule on main thread
                                        if CallbackHandler.auth_instance.success_callback:
                                            try:
                                                # Prefer an explicit UI scheduler if provided by the GUI (e.g., widget.after)
                                                ui_after = getattr(CallbackHandler.auth_instance, "ui_after", None)
                                                if callable(ui_after):
                                                    ui_after(0, CallbackHandler.auth_instance.success_callback)
                                                else:
                                                    # Fallback to tkinter default root if available
                                                    import tkinter as tk
                                                    if hasattr(tk, "_default_root") and tk._default_root:
                                                        tk._default_root.after(0, CallbackHandler.auth_instance.success_callback)
                                                    else:
                                                        # Last resort: call directly (unsafe), but log a warning
                                                        CallbackHandler.auth_instance.logger.warning("No Tk main loop available; calling success callback directly (may be unsafe)")
                                                        CallbackHandler.auth_instance.success_callback()
                                            except Exception as e:
                                                CallbackHandler.auth_instance.logger.error(f"Error scheduling success callback: {e}")
                                    else:
                                        CallbackHandler.auth_instance._log("❌ Failed to get user data")
                                else:
                                    CallbackHandler.auth_instance._log("❌ Token exchange failed")
                            except Exception as e:
                                CallbackHandler.auth_instance.logger.error(f"Error in token exchange: {e}")
                                CallbackHandler.auth_instance._log(f"❌ Error in token exchange: {e}")
                            finally:
                                # Reset the flag when done
                                CallbackHandler.auth_instance.token_exchange_in_progress = False

                        threading.Thread(target=exchange_token, daemon=True).start()

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()

                    # Embed success image as data URI if available
                    image_data_uri = ""
                    try:
                        from pathlib import Path as _Path
                        img_path = _Path(__file__).resolve().parent.parent.parent / "assets" / "authenticatedsuccess.png"
                        if img_path.exists():
                            with open(img_path, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode("ascii")
                                image_data_uri = f"data:image/png;base64,{b64}"
                    except Exception as _e:
                        CallbackHandler.auth_instance.logger.warning(f"Could not embed success image: {_e}")
                    if not image_data_uri:
                        # Fallback: 1x1 transparent PNG
                        image_data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="

                    response_html = f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>DevBlogger - Authentication Successful</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            .success {{ color: #28a745; font-size: 24px; }}
                            .message {{ color: #6c757d; font-size: 16px; margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="success">✅ Authentication Successful!</div>
                        <img src="{image_data_uri}" alt="Authenticated" style="margin-top:20px; max-width:240px; height:auto;" />
                        <div class="message">You can now close this window and return to DevBlogger.</div>
                    </body>
                    </html>
                    '''

                    self.wfile.write(response_html.encode('utf-8'))
                    CallbackHandler.auth_instance.logger.info("Success response sent to browser")
                    CallbackHandler.auth_instance._log("🌐 Success response sent to browser")

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
        self.logger.info(f"Starting to wait for authentication (timeout: {timeout}s)")

        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            if elapsed % 5 == 0:  # Log every 5 seconds
                self.logger.info(f"Waiting for auth code... ({elapsed:.1f}s elapsed, auth_code present: {bool(self.auth_code)})")

            if self.auth_code:
                self.logger.info(f"Authorization code received after {elapsed:.1f}s: {self.auth_code[:10]}...")
                break
            time.sleep(0.1)

        if not self.auth_code:
            self.logger.error(f"Authentication timeout after {timeout}s - no authorization code received")
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
        """Stop the callback server (idempotent and thread-safe)."""
        try:
            # Lazily create a lock for server stop operations
            if not hasattr(self, "_server_lock"):
                self._server_lock = threading.Lock()  # type: ignore[attr-defined]
        except Exception:
            # If we cannot create a lock, proceed without it (best-effort)
            self._server_lock = None  # type: ignore[attr-defined]

        server = None
        thread = None

        try:
            # Atomically take ownership of server references and clear shared attrs
            if getattr(self, "_server_lock", None) is not None:
                with self._server_lock:  # type: ignore[attr-defined]
                    server = self.callback_server
                    thread = self.server_thread
                    self.callback_server = None
                    self.server_thread = None
            else:
                # No lock available, best-effort swap
                server = self.callback_server
                thread = self.server_thread
                self.callback_server = None
                self.server_thread = None

            if server:
                # Stop server on a background thread to avoid blocking the GUI
                def _async_shutdown(srv, th):
                    try:
                        try:
                            srv.shutdown()
                        except Exception as e:
                            self.logger.warning(f"Callback server shutdown error (ignored): {e}")
                        try:
                            srv.server_close()
                        except Exception as e:
                            self.logger.warning(f"Callback server close error (ignored): {e}")
                        if th and th.is_alive():
                            # Join in background thread, not on the UI/main thread
                            th.join(timeout=2.0)
                            if th.is_alive():
                                self.logger.warning("Server thread did not stop within timeout")
                            else:
                                self.logger.info("Server thread stopped successfully")
                        self.logger.info("Callback server stopped successfully")
                    except Exception as e:
                        self.logger.warning(f"Async server stop encountered error (ignored): {e}")
                    finally:
                        # Notify UI thread that the server has fully stopped
                        try:
                            on_stopped = getattr(self, "on_server_stopped", None)
                            ui_after = getattr(self, "ui_after", None)
                            if callable(on_stopped):
                                if callable(ui_after):
                                    ui_after(0, on_stopped)
                                else:
                                    # Fallback to default root if available
                                    import tkinter as tk
                                    if hasattr(tk, "_default_root") and tk._default_root:
                                        tk._default_root.after(0, on_stopped)
                                    else:
                                        # Last resort, call directly
                                        on_stopped()
                            # Clear the callback to avoid duplicate invocations
                            try:
                                self.on_server_stopped = None  # type: ignore[attr-defined]
                            except Exception:
                                pass
                        except Exception as notify_e:
                            self.logger.warning(f"Could not notify UI of server stop: {notify_e}")
                try:
                    threading.Thread(target=_async_shutdown, args=(server, thread), daemon=True).start()
                except Exception as e:
                    self.logger.warning(f"Failed to spawn async server shutdown thread: {e}")
                # Notify UI that server stop was initiated (completion will trigger callback below)
            else:
                # Already stopped by another caller - notify UI to clear pending state
                self.logger.info("Callback server already stopped (noop)")
                try:
                    on_stopped = getattr(self, "on_server_stopped", None)
                    ui_after = getattr(self, "ui_after", None)
                    if callable(on_stopped):
                        if callable(ui_after):
                            ui_after(0, on_stopped)
                        else:
                            # Fallback to default root if available
                            import tkinter as tk
                            if hasattr(tk, "_default_root") and tk._default_root:
                                tk._default_root.after(0, on_stopped)
                            else:
                                # Last resort, call directly
                                on_stopped()
                    # Clear the callback to avoid duplicate invocations
                    try:
                        self.on_server_stopped = None  # type: ignore[attr-defined]
                    except Exception:
                        pass
                except Exception:
                    pass

        except Exception as e:
            # Ensure attributes remain cleared even if errors happen
            self.callback_server = None
            self.server_thread = None
            self.logger.error(f"Error stopping callback server (ignored): {e}")

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
