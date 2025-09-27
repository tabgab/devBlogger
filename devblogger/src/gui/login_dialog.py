#!/usr/bin/env python3
"""
DevBlogger - GitHub Login Dialog
"""

import logging
import threading
import time
import webbrowser
from typing import Callable, Optional
import customtkinter as ctk

# Safe, non-grabbing messagebox wrapper to avoid input grabs/topmost issues
try:
    import tkinter.messagebox as tk_messagebox
except Exception:
    tk_messagebox = None

def CTkMessagebox(title, message, icon="info", **kwargs):
    """Safe messagebox wrapper using tkinter.messagebox without grabs/topmost."""
    try:
        if tk_messagebox:
            if icon == "cancel":
                tk_messagebox.showerror(title, message)
            elif icon == "warning":
                tk_messagebox.showwarning(title, message)
            else:
                # treat "check" and "info" similarly
                tk_messagebox.showinfo(title, message)
        else:
            print(f"=== {title} ===")
            print(message)
            print("=" * (len(title) + 4))
    except Exception:
        print(f"=== {title} ===")
        print(message)
        print("=" * (len(title) + 4))

from ..github.auth import GitHubAuth


class GitHubLoginDialog(ctk.CTkToplevel):
    """GitHub login dialog with OAuth flow."""

    def __init__(self, parent, github_auth: GitHubAuth, on_success: Callable):
        """Initialize login dialog."""
        super().__init__(parent)

        self.github_auth = github_auth
        self.on_success = on_success
        self.logger = logging.getLogger(__name__)
        # Ensure auth callbacks are scheduled on this dialog's Tk thread
        try:
            self.github_auth.ui_after = self.after
        except Exception:
            pass

        # Dialog state
        self.auth_in_progress = False
        self.auth_thread: Optional[threading.Thread] = None

        # Setup dialog
        self._setup_dialog()
        self._setup_ui()
        self._setup_bindings()

        # Start authentication process
        self._start_authentication()

    def _setup_dialog(self):
        """Setup dialog properties."""
        # Configure dialog
        self.title("GitHub Authentication")
        self.geometry("500x400")
        self.resizable(True, True)  # Allow resizing to see more log text

        # Center on parent without modal behavior to prevent macOS segfault
        self.transient(self.master)
        # Don't use grab_set() as it can cause segfaults on macOS

        # Position dialog
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        x = parent_x + (parent_width - 500) // 2
        y = parent_y + (parent_height - 400) // 2

        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Setup user interface."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="GitHub Authentication",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions_label = ctk.CTkLabel(
            main_frame,
            text="🔐 GitHub Authentication Required\n\n"
                 "This application needs permission to access your GitHub repositories.\n\n"
                 "📋 Step 1: Copy the authorization URL below\n"
                 "🌐 Step 2: Open it in your web browser\n"
                 "✅ Step 3: Authorize the application\n"
                 "🔄 Step 4: Return here - authentication will complete automatically\n\n"
                 "The browser will redirect to a success page when done.",
            font=ctk.CTkFont(size=12),
            wraplength=440,
            justify="left"
        )
        instructions_label.pack(pady=(0, 20))

        # WebView for GitHub authentication
        self.webview_frame = ctk.CTkFrame(main_frame, border_width=2, fg_color="lightgray")
        self.webview_frame.pack(fill="both", expand=True, pady=(0, 20))

        webview_label = ctk.CTkLabel(
            self.webview_frame,
            text="🌐 GitHub Authentication (opens automatically)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        webview_label.pack(anchor="w", padx=10, pady=(10, 5))

        # Status text for webview
        self.webview_status = ctk.CTkLabel(
            self.webview_frame,
            text="Loading GitHub authentication...",
            font=ctk.CTkFont(size=11),
            text_color="blue"
        )
        self.webview_status.pack(anchor="w", padx=10, pady=(0, 10))

        # Placeholder for webview - will be replaced with actual webview
        self.webview_placeholder = ctk.CTkLabel(
            self.webview_frame,
            text="🔄 Opening GitHub authentication in embedded browser...\n\n"
                 "If this doesn't load, please use the manual method below.",
            font=ctk.CTkFont(size=12),
            justify="center"
        )
        self.webview_placeholder.pack(expand=True, padx=20, pady=20)

        # Manual authentication section (fallback)
        self.manual_frame = ctk.CTkFrame(main_frame, border_width=2, fg_color="lightyellow")
        self.manual_frame.pack(fill="x", pady=(0, 20))

        manual_label = ctk.CTkLabel(
            self.manual_frame,
            text="🔗 Manual Authentication (if webview fails):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        manual_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.manual_url_text = ctk.CTkTextbox(
            self.manual_frame,
            height=60,
            font=ctk.CTkFont(size=10),
            wrap="word"
        )
        self.manual_url_text.pack(fill="x", padx=10, pady=(0, 10))
        self.manual_url_text.insert("1.0", "⏳ Generating authorization URL...")
        self.manual_url_text.configure(state="disabled")

        # Copy URL button for manual method
        copy_button = ctk.CTkButton(
            self.manual_frame,
            text="📋 Copy URL",
            command=self._copy_manual_url,
            width=100
        )
        copy_button.pack(anchor="e", padx=10, pady=(0, 10))

        # Progress section
        self.progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 20))

        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready to authenticate...",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            mode="indeterminate",
            width=400
        )
        self.progress_bar.pack(pady=(0, 20))

        # Authentication log text area
        self.log_frame = ctk.CTkFrame(main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=(0, 20))

        self.log_label = ctk.CTkLabel(
            self.log_frame,
            text="Authentication Log:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.log_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            height=150,
            font=ctk.CTkFont(size=10),
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.insert("1.0", "Authentication log will appear here...\n")
        self.log_text.configure(state="disabled")

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        self.authenticate_button = ctk.CTkButton(
            button_frame,
            text="Open Browser for Authentication",
            command=self._open_browser_auth,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        )
        self.authenticate_button.pack(side="left", padx=(0, 10))

        # Manual check button
        self.check_button = ctk.CTkButton(
            button_frame,
            text="Check Authentication Status",
            command=self._check_auth_status,
            fg_color="blue",
            hover_color="darkblue",
            height=40
        )
        self.check_button.pack(side="left", padx=(0, 10))

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_auth,
            fg_color="red",
            hover_color="darkred",
            height=40
        )
        self.cancel_button.pack(side="right")

        # Info text
        info_label = ctk.CTkLabel(
            main_frame,
            text="Note: This application only requests read-only access to your repositories.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="gray"
        )
        info_label.pack(pady=(20, 0))

    def _setup_bindings(self):
        """Setup event bindings."""
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _start_authentication(self):
        """Start the authentication process."""
        try:
            self.logger.info("Starting authentication process")
            self.logger.info(f"GitHub auth configured: {self.github_auth.is_configured()}")
            self.logger.info(f"GitHub auth client_id: {self.github_auth.client_id[:10]}..." if self.github_auth.client_id else "No client_id")

            if not self.github_auth.is_configured():
                self.logger.error("GitHub OAuth is not configured")
                self._show_error("GitHub OAuth is not configured. Please check your settings.")
                return

            self.auth_in_progress = True
            self._update_ui_state()
            self._add_log_message("🔄 Starting authentication process...")
            self.logger.info("Authentication state updated, starting monitoring thread")

            # Set up log callback for GitHub auth
            self.github_auth.log_callback = self._add_log_message

            # Start the callback server first
            try:
                self._add_log_message("🔄 Starting callback server...")
                self.github_auth._start_callback_server()
                self._add_log_message("✅ Callback server started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start callback server: {e}")
                self._add_log_message(f"❌ Failed to start callback server: {e}")
                self._show_error(f"Failed to start callback server: {str(e)}")
                return

            # Generate and display authorization URL immediately
            try:
                self._add_log_message("🔄 Generating authorization URL...")
                auth_url = self.github_auth.get_authorization_url()
                self.logger.info(f"Authorization URL generated: {auth_url}")

                # Display in manual URL text area (this should exist)
                self.manual_url_text.configure(state="normal")
                self.manual_url_text.delete("1.0", "end")
                self.manual_url_text.insert("1.0", auth_url)
                self.manual_url_text.configure(state="disabled")
                self._add_log_message("🔗 Authorization URL generated and displayed")
                self._add_log_message(f"🌐 URL: {auth_url}")
                self._add_log_message(f"📋 Copy the URL above and open it in your browser")

                # Also try to open browser automatically
                self._add_log_message("🌐 Opening browser automatically...")
                try:
                    import webbrowser
                    webbrowser.open(auth_url)
                    self._add_log_message("✅ Browser opened successfully")
                except Exception as browser_error:
                    self.logger.error(f"Error opening browser: {browser_error}")
                    self._add_log_message(f"⚠️ Could not open browser automatically: {browser_error}")
                    self._add_log_message(f"🔗 Please manually open this URL: {auth_url}")

            except Exception as e:
                self.logger.error(f"Error generating authorization URL: {e}")
                self._add_log_message(f"❌ Error generating URL: {e}")
                # Try to display error in manual text area
                try:
                    self.manual_url_text.configure(state="normal")
                    self.manual_url_text.delete("1.0", "end")
                    self.manual_url_text.insert("1.0", f"Error: {str(e)}")
                    self.manual_url_text.configure(state="disabled")
                except:
                    pass

            # Use main thread monitoring to avoid autorelease pool crashes on macOS
            self.logger.info("Starting main thread authentication monitoring")
            self._start_main_thread_monitoring()
        except Exception as e:
            self.logger.error(f"Error in _start_authentication: {e}", exc_info=True)
            self._show_error(f"Failed to start authentication: {str(e)}")

    def _update_ui_state(self):
        """Update UI based on authentication state."""
        if self.auth_in_progress:
            self.status_label.configure(text="Authentication in progress...")
            self.progress_bar.start()
            self.authenticate_button.configure(state="disabled", text="Authenticating...")
            self.cancel_button.configure(state="normal")
        else:
            self.status_label.configure(text="Authentication completed")
            self.progress_bar.stop()
            self.authenticate_button.configure(state="normal", text="Open Browser for Authentication")
            self.cancel_button.configure(state="normal")

    def _add_log_message(self, message: str):
        """Add a message to the authentication log."""
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{time.strftime('%H:%M:%S')} - {message}\n")
            self.log_text.see("end")  # Scroll to bottom
            self.log_text.configure(state="disabled")
        except Exception as e:
            self.logger.error(f"Error adding log message: {e}")

    def _clear_log(self):
        """Clear the authentication log."""
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.insert("1.0", "Authentication log will appear here...\n")
            self.log_text.configure(state="disabled")
        except Exception as e:
            self.logger.error(f"Error clearing log: {e}")

    def _open_browser_auth(self):
        """Open browser for GitHub authentication."""
        try:
            auth_url = self.github_auth.get_authorization_url()
            self.logger.info(f"Opening browser to: {auth_url}")

            # Update status
            self.status_label.configure(text="⏳ Opening browser...")

            # Open browser
            webbrowser.open(auth_url)

            # Update status
            self.status_label.configure(text="🌐 Waiting for callback from external browser for GitHub authorization...")

        except Exception as e:
            self.logger.error(f"Error opening browser: {e}")
            self._show_error(f"Failed to open browser: {str(e)}")

    def _copy_url(self):
        """Copy the authorization URL to clipboard."""
        try:
            auth_url = self.auth_url_text.get("1.0", "end").strip()
            if auth_url and auth_url != "⏳ Generating authorization URL...":
                self.clipboard_clear()
                self.clipboard_append(auth_url)
                self._add_log_message("📋 Authorization URL copied to clipboard")
                CTkMessagebox(
                    title="URL Copied",
                    message="Authorization URL has been copied to your clipboard.",
                    icon="info"
                )
            else:
                CTkMessagebox(
                    title="No URL Available",
                    message="Authorization URL is not yet available.",
                    icon="warning"
                )
        except Exception as e:
            self.logger.error(f"Error copying URL: {e}")
            CTkMessagebox(
                title="Copy Error",
                message=f"Failed to copy URL: {str(e)}",
                icon="cancel"
            )

    def _copy_manual_url(self):
        """Copy the manual authorization URL to clipboard."""
        try:
            auth_url = self.manual_url_text.get("1.0", "end").strip()
            if auth_url and auth_url != "⏳ Generating authorization URL...":
                self.clipboard_clear()
                self.clipboard_append(auth_url)
                self._add_log_message("📋 Manual authorization URL copied to clipboard")
                CTkMessagebox(
                    title="URL Copied",
                    message="Manual authorization URL has been copied to your clipboard.",
                    icon="info"
                )
            else:
                CTkMessagebox(
                    title="No URL Available",
                    message="Authorization URL is not yet available.",
                    icon="warning"
                )
        except Exception as e:
            self.logger.error(f"Error copying manual URL: {e}")
            CTkMessagebox(
                title="Copy Error",
                message=f"Failed to copy URL: {str(e)}",
                icon="cancel"
            )

    def _check_auth_status(self):
        """Manually check authentication status."""
        try:
            self._add_log_message("🔍 Manually checking authentication status...")

            # Check if we have an auth code (callback was received)
            if self.github_auth.auth_code:
                self._add_log_message(f"✅ Authorization code found: {self.github_auth.auth_code[:10]}...")
                self._add_log_message("🔄 Processing authorization code...")

                # Try to exchange code for token
                success = self.github_auth._exchange_code_for_token()
                if success:
                    self._add_log_message("✅ Token exchange successful!")
                    success = self.github_auth._get_user_data()
                    if success:
                        self._add_log_message("✅ User data retrieved successfully!")
                        self._add_log_message("🎉 Authentication completed successfully!")
                        self._handle_auth_success()
                        return
                    else:
                        self._add_log_message("❌ Failed to get user data")
                else:
                    self._add_log_message("❌ Token exchange failed")

            # Check if we have access token
            if self.github_auth.access_token:
                self._add_log_message(f"✅ Access token found: {self.github_auth.access_token[:20]}...")
                if not self.github_auth.user_data:
                    self._add_log_message("🔄 Getting user data...")
                    success = self.github_auth._get_user_data()
                    if success:
                        self._add_log_message("✅ User data retrieved successfully!")
                        self._add_log_message("🎉 Authentication completed successfully!")
                        self._handle_auth_success()
                        return
                    else:
                        self._add_log_message("❌ Failed to get user data")

            # Check if we have user data
            if self.github_auth.user_data:
                self._add_log_message("✅ User data found - authentication successful!")
                self._handle_auth_success()
                return

            # Check if fully authenticated
            if self.github_auth.is_authenticated():
                self._add_log_message("✅ Authentication is complete!")
                self._handle_auth_success()
                return

            # No authentication found
            self._add_log_message("❌ No authentication data found")
            self._add_log_message("🔗 Please complete the GitHub authorization in your browser first")
            CTkMessagebox(
                title="No Authentication Found",
                message="No authentication data found. Please complete the GitHub authorization in your browser first, then click this button again.",
                icon="warning"
            )

        except Exception as e:
            self.logger.error(f"Error checking auth status: {e}")
            self._add_log_message(f"❌ Error checking authentication status: {str(e)}")
            CTkMessagebox(
                title="Check Error",
                message=f"Error checking authentication status: {str(e)}",
                icon="cancel"
            )

    def _monitor_authentication(self):
        """Monitor authentication progress in background thread."""
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        self.logger.info(f"Starting authentication monitoring (max wait: {max_wait_time}s)")

        while self.auth_in_progress and (time.time() - start_time) < max_wait_time:
            try:
                elapsed = time.time() - start_time
                if elapsed % 2 == 0:  # Log every 2 seconds for more frequent updates
                    self.logger.info(f"Monitoring authentication... ({elapsed:.1f}s elapsed)")
                    self.logger.info(f"Auth in progress: {self.auth_in_progress}")
                    self.logger.info(f"GitHub auth authenticated: {self.github_auth.is_authenticated()}")
                    self.logger.info(f"GitHub auth has access token: {bool(self.github_auth.access_token)}")
                    self.logger.info(f"GitHub auth has user data: {bool(self.github_auth.user_data)}")
                    self.logger.info(f"GitHub auth has auth code: {bool(self.github_auth.auth_code)}")

                # Check multiple conditions for successful authentication
                if self.github_auth.is_authenticated():
                    # Authentication successful
                    self.logger.info(f"Authentication successful after {elapsed:.1f}s!")
                    self._add_log_message("✅ Authentication successful!")
                    self.after(0, self._handle_auth_success)
                    return

                # Also check if we have both access token and user data
                if self.github_auth.access_token and self.github_auth.user_data:
                    self.logger.info(f"Authentication completed with token and user data after {elapsed:.1f}s!")
                    self._add_log_message("✅ Authentication completed successfully!")
                    self.after(0, self._handle_auth_success)
                    return

                # Check if we have an auth code (indicates callback was received)
                if self.github_auth.auth_code and not self.github_auth.access_token:
                    self.logger.info(f"Authorization code received, waiting for token exchange... ({elapsed:.1f}s elapsed)")
                    self._add_log_message("🔄 Authorization code received, exchanging for token...")

                # Also check if we have user data (indicates successful authentication)
                if self.github_auth.user_data and not self.github_auth.is_authenticated():
                    self.logger.info(f"User data received, authentication likely successful after {elapsed:.1f}s!")
                    self._add_log_message("✅ User data received - authentication successful!")
                    self.after(0, self._handle_auth_success)
                    return

                # Check if we have access token (indicates token exchange completed)
                if self.github_auth.access_token and not self.github_auth.user_data:
                    self.logger.info(f"Access token received, waiting for user data... ({elapsed:.1f}s elapsed)")
                    self._add_log_message("🔄 Access token received, getting user data...")

                # Check if we have both access token and user data but is_authenticated() is failing
                if self.github_auth.access_token and self.github_auth.user_data:
                    self.logger.info(f"Both token and user data present after {elapsed:.1f}s - forcing success!")
                    self._add_log_message("✅ Authentication completed with token and user data!")
                    self.after(0, self._handle_auth_success)
                    return

                # Check if we have an access token (indicates successful token exchange)
                if self.github_auth.access_token:
                    self.logger.info(f"Access token received after {elapsed:.1f}s - authentication successful!")
                    self._add_log_message("✅ Access token received - authentication successful!")
                    self.after(0, self._handle_auth_success)
                    return

                # Check if we have user data (indicates successful user data retrieval)
                if self.github_auth.user_data:
                    self.logger.info(f"User data received after {elapsed:.1f}s - authentication successful!")
                    self._add_log_message("✅ User data received - authentication successful!")
                    self.after(0, self._handle_auth_success)
                    return

                # Wait before checking again
                time.sleep(0.5)  # Check more frequently

            except Exception as e:
                self.logger.error(f"Error during authentication monitoring: {e}", exc_info=True)
                self._add_log_message(f"❌ Authentication monitoring error: {str(e)}")
                self.after(0, lambda: self._show_error(f"Authentication error: {str(e)}"))
                return

        # Timeout
        if self.auth_in_progress:
            self.logger.warning(f"Authentication timeout after {max_wait_time}s")
            self.logger.warning(f"Final state - Auth in progress: {self.auth_in_progress}")
            self.logger.warning(f"Final state - GitHub auth authenticated: {self.github_auth.is_authenticated()}")
            self.logger.warning(f"Final state - Has access token: {bool(self.github_auth.access_token)}")
            self.logger.warning(f"Final state - Has user data: {bool(self.github_auth.user_data)}")
            self.logger.warning(f"Final state - Has auth code: {bool(self.github_auth.auth_code)}")
            self._add_log_message(f"⏰ Authentication timed out after {max_wait_time} seconds")
            self.after(0, self._handle_auth_timeout)

    def _handle_auth_success(self):
        """Handle successful authentication."""
        self.auth_in_progress = False
        self._update_ui_state()

        # Close dialog
        self._close_dialog()

        # Ensure main window regains focus after closing dialog (macOS click-through fix)
        try:
            if self.master and self.master.winfo_exists():
                def _restore_focus():
                    try:
                        self.master.lift()
                        # Bounce topmost to break potential click-through on macOS
                        try:
                            self.master.attributes("-topmost", True)
                            self.master.after(100, lambda: self.master.attributes("-topmost", False))
                        except Exception:
                            # Ignore if attribute not supported on platform
                            pass
                        self.master.focus_force()
                    except Exception:
                        pass
                self.master.after(150, _restore_focus)
        except Exception:
            pass

        # Call success callback
        try:
            self.on_success()
        except Exception as e:
            self.logger.error(f"Error in success callback: {e}")

    def _handle_auth_timeout(self):
        """Handle authentication timeout."""
        self.auth_in_progress = False
        self._update_ui_state()

        self.status_label.configure(text="Authentication timed out. Please try again.")
        self.authenticate_button.configure(text="Retry Authentication")

        CTkMessagebox(
            title="Authentication Timeout",
            message="Authentication timed out after 5 minutes.\nPlease try again.",
            icon="warning"
        )

    def _cancel_auth(self):
        """Cancel authentication process."""
        if self.auth_in_progress:
            self.auth_in_progress = False
            self.monitoring_active = False  # Stop monitoring
            if self.auth_thread and self.auth_thread.is_alive():
                self.auth_thread.join(timeout=1)

        self._close_dialog()

    def _show_error(self, message: str):
        """Show error message."""
        self.status_label.configure(text=f"Error: {message}")
        self.progress_bar.stop()
        self.authenticate_button.configure(state="normal", text="Retry")

        CTkMessagebox(
            title="Authentication Error",
            message=message,
            icon="cancel"
        )

    def _close_dialog(self):
        """Close the dialog."""
        try:
            # Stop the callback server in background to avoid blocking
            if hasattr(self.github_auth, 'callback_server') and self.github_auth.callback_server:
                self.logger.info("Stopping callback server...")
                # Don't wait for server to stop - do it in background
                def stop_server_background():
                    try:
                        self.github_auth._stop_callback_server()
                    except Exception as e:
                        self.logger.error(f"Error stopping callback server: {e}")
                
                import threading
                threading.Thread(target=stop_server_background, daemon=True).start()
                self._add_log_message("🛑 Callback server stopping...")
            
            # Don't use grab_release() as it can block on some systems
            # Just destroy the dialog immediately
            self.destroy()
        except Exception as e:
            self.logger.error(f"Error closing dialog: {e}")

    def _start_main_thread_monitoring(self):
        """Start authentication monitoring - no automatic polling."""
        self.monitoring_start_time = time.time()
        self.max_wait_time = 300  # 5 minutes
        self.monitoring_active = True
        
        # Set up callback in GitHub auth to notify us when authentication completes
        self.github_auth.success_callback = self._on_auth_complete
        
        # Just show instructions - no automatic polling
        self._add_log_message("🔄 Waiting for GitHub authorization...")
        self._add_log_message("📋 Complete the authorization in your browser, then click 'Check Authentication Status'")

    def _on_auth_complete(self):
        """Called by GitHub auth when authentication completes."""
        if hasattr(self, 'monitoring_active') and self.monitoring_active:
            self.monitoring_active = False
            try:
                self._add_log_message("✅ Authentication completed!")
                # Schedule dialog close on main thread to avoid widget destruction issues
                self.after(100, self._handle_auth_success)
            except Exception as e:
                self.logger.error(f"Error in auth complete callback: {e}")
                # Force close dialog even if there's an error
                self.after(100, self._handle_auth_success)

    def _on_closing(self):
        """Handle dialog closing event."""
        self._cancel_auth()


class GitHubLoginDialogSimple(ctk.CTkToplevel):
    """Simplified GitHub login dialog for basic authentication."""

    def __init__(self, parent, github_auth: GitHubAuth, on_success: Callable):
        """Initialize simple login dialog."""
        super().__init__(parent)

        self.github_auth = github_auth
        self.on_success = on_success
        self.logger = logging.getLogger(__name__)
        # Ensure auth callbacks are scheduled on this dialog's Tk thread
        try:
            self.github_auth.ui_after = self.after
        except Exception:
            pass

        # Setup dialog
        self._setup_dialog()
        self._setup_ui()
        self._setup_bindings()

    def _setup_dialog(self):
        """Setup dialog properties."""
        self.title("GitHub Login")
        self.geometry("400x300")
        self.resizable(False, False)

        # Center on parent without modal behavior to prevent macOS segfault
        self.transient(self.master)
        # Don't use grab_set() as it can cause segfaults on macOS

        # Position dialog
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        x = parent_x + (parent_width - 400) // 2
        y = parent_y + (parent_height - 300) // 2

        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Setup user interface."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="GitHub Authentication",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions_label = ctk.CTkLabel(
            main_frame,
            text="This application requires GitHub authentication\nto access your repositories.",
            font=ctk.CTkFont(size=12),
            justify="center"
        )
        instructions_label.pack(pady=(0, 30))

        # Status
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Click the button below to authenticate",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 20))

        # Authenticate button
        self.auth_button = ctk.CTkButton(
            main_frame,
            text="Authenticate with GitHub",
            command=self._authenticate,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        )
        self.auth_button.pack(pady=(0, 20))

        # Cancel button
        cancel_button = ctk.CTkButton(
            main_frame,
            text="Cancel",
            command=self._cancel,
            fg_color="red",
            hover_color="darkred",
            height=40
        )
        cancel_button.pack()

    def _setup_bindings(self):
        """Setup event bindings."""
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _authenticate(self):
        """Start authentication process."""
        try:
            self.status_label.configure(text="Opening browser...")
            self.auth_button.configure(state="disabled", text="Authenticating...")

            # Start authentication
            success = self.github_auth.authenticate(self)

            if success:
                self.status_label.configure(text="Authentication successful!")
                self._close_dialog()
                self.on_success()
            else:
                self.status_label.configure(text="Authentication failed. Please try again.")
                self.auth_button.configure(state="normal", text="Retry Authentication")

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            self.status_label.configure(text=f"Error: {str(e)}")
            self.auth_button.configure(state="normal", text="Retry Authentication")

    def _cancel(self):
        """Cancel authentication."""
        self._close_dialog()

    def _close_dialog(self):
        """Close the dialog."""
        try:
            self.grab_release()
            self.destroy()
        except Exception as e:
            self.logger.error(f"Error closing dialog: {e}")

    def _on_closing(self):
        """Handle dialog closing event."""
        self._cancel()
