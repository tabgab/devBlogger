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
        self.resizable(False, False)

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
            text="To authenticate with GitHub, you need to authorize this application.\n\n"
                 "Click the button below to open your browser and complete the login process.\n\n"
                 "After successful authentication, you can close the browser window\n"
                 "and return to this application.",
            font=ctk.CTkFont(size=12),
            wraplength=440,
            justify="left"
        )
        instructions_label.pack(pady=(0, 30))

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
            if not self.github_auth.is_configured():
                self.logger.error("GitHub OAuth is not configured")
                self._show_error("GitHub OAuth is not configured. Please check your settings.")
                return

            self.auth_in_progress = True
            self._update_ui_state()
            self.logger.info("Authentication state updated, starting monitoring thread")

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

    def _open_browser_auth(self):
        """Open browser for GitHub authentication."""
        try:
            auth_url = self.github_auth.get_authorization_url()
            self.logger.info(f"Opening browser to: {auth_url}")

            # Update status
            self.status_label.configure(text="Opening browser...")

            # Open browser
            webbrowser.open(auth_url)

            # Update status
            self.status_label.configure(text="Please complete authentication in your browser...")

        except Exception as e:
            self.logger.error(f"Error opening browser: {e}")
            self._show_error(f"Failed to open browser: {str(e)}")

    def _monitor_authentication(self):
        """Monitor authentication progress in background thread."""
        max_wait_time = 300  # 5 minutes
        start_time = time.time()

        while self.auth_in_progress and (time.time() - start_time) < max_wait_time:
            try:
                if self.github_auth.is_authenticated():
                    # Authentication successful
                    self.logger.info("Authentication successful")
                    self.after(0, self._handle_auth_success)
                    return

                # Wait before checking again
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error during authentication monitoring: {e}")
                self.after(0, lambda: self._show_error(f"Authentication error: {str(e)}"))
                return

        # Timeout
        if self.auth_in_progress:
            self.logger.warning("Authentication timeout")
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
