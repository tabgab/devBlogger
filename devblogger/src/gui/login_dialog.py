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

# Try to import CTkMessagebox, fall back to tkinter if not available
try:
    from CTkMessagebox import CTkMessagebox
except ImportError:
    try:
        import tkinter.messagebox as tk_messagebox
        def CTkMessagebox(title, message, icon="info", **kwargs):
            """Fallback messagebox using tkinter."""
            root = ctk.CTk()
            root.withdraw()  # Hide the root window
            if icon == "check":
                tk_messagebox.showinfo(title, message)
            elif icon == "cancel" or icon == "warning":
                tk_messagebox.showerror(title, message)
            else:
                tk_messagebox.showinfo(title, message)
            root.destroy()
    except ImportError:
        def CTkMessagebox(title, message, icon="info", **kwargs):
            """Fallback messagebox using print."""
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

            # Generate and display authorization URL immediately
            try:
                auth_url = self.github_auth.get_authorization_url()
                # Display in manual URL text area (this should exist)
                self.manual_url_text.configure(state="normal")
                self.manual_url_text.delete("1.0", "end")
                self.manual_url_text.insert("1.0", auth_url)
                self.manual_url_text.configure(state="disabled")
                self._add_log_message("🔗 Authorization URL generated and displayed")
                self._add_log_message(f"🌐 URL: {auth_url}")
                self._add_log_message(f"📋 Copy the URL above and open it in your browser")
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

            # Start monitoring thread
            self.auth_thread = threading.Thread(target=self._monitor_authentication, daemon=True)
            self.auth_thread.start()
            self.logger.info("Authentication monitoring thread started")
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

    def _monitor_authentication(self):
        """Monitor authentication progress in background thread."""
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        self.logger.info(f"Starting authentication monitoring (max wait: {max_wait_time}s)")

        while self.auth_in_progress and (time.time() - start_time) < max_wait_time:
            try:
                elapsed = time.time() - start_time
                if elapsed % 10 == 0:  # Log every 10 seconds
                    self.logger.info(f"Monitoring authentication... ({elapsed:.1f}s elapsed)")
                    self.logger.info(f"Auth in progress: {self.auth_in_progress}")
                    self.logger.info(f"GitHub auth authenticated: {self.github_auth.is_authenticated()}")
                    self.logger.info(f"GitHub auth has access token: {bool(self.github_auth.access_token)}")
                    self.logger.info(f"GitHub auth has user data: {bool(self.github_auth.user_data)}")

                if self.github_auth.is_authenticated():
                    # Authentication successful
                    self.logger.info(f"Authentication successful after {elapsed:.1f}s!")
                    self.after(0, self._handle_auth_success)
                    return

                # Wait before checking again
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error during authentication monitoring: {e}", exc_info=True)
                self.after(0, lambda: self._show_error(f"Authentication error: {str(e)}"))
                return

        # Timeout
        if self.auth_in_progress:
            self.logger.warning(f"Authentication timeout after {max_wait_time}s")
            self.logger.warning(f"Final state - Auth in progress: {self.auth_in_progress}")
            self.logger.warning(f"Final state - GitHub auth authenticated: {self.github_auth.is_authenticated()}")
            self.logger.warning(f"Final state - Has access token: {bool(self.github_auth.access_token)}")
            self.logger.warning(f"Final state - Has user data: {bool(self.github_auth.user_data)}")
            self.after(0, self._handle_auth_timeout)

    def _handle_auth_success(self):
        """Handle successful authentication."""
        self.auth_in_progress = False
        self._update_ui_state()

        # Close dialog
        self._close_dialog()

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
            self.grab_release()
            self.destroy()
        except Exception as e:
            self.logger.error(f"Error closing dialog: {e}")

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
