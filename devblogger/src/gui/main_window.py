#!/usr/bin/env python3
"""
DevBlogger - Main GUI Window
"""

import logging
import threading
import time
from typing import Optional, Dict, Any
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
                tk_messagebox.showinfo(title, message)
        else:
            print(f"=== {title} ===")
            print(message)
            print("=" * (len(title) + 4))
    except Exception:
        print(f"=== {title} ===")
        print(message)
        print("=" * (len(title) + 4))

from ..config.settings import Settings
from ..config.database import DatabaseManager
from ..github.auth import GitHubAuth
from ..github.client import GitHubClient
from ..ai.manager import DevBloggerAIProviderManager
from .login_dialog import GitHubLoginDialog
from .repo_selector import RepositorySelector
from .commit_browser import CommitBrowser
from .ai_config import AIConfigurationPanel
from .blog_editor import BlogEditor


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self, settings: Settings, database: DatabaseManager):
        """Initialize main window."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing MainWindow")

        super().__init__()
        self.logger.info("CTk parent initialized")

        self.settings = settings
        self.database = database
        self.logger.info("Settings and database assigned")

        # Initialize components
        self.logger.info("Initializing GitHubAuth")
        self.github_auth = GitHubAuth(settings)
        self.logger.info("GitHubAuth initialized")

        self.github_client: Optional[GitHubClient] = None
        self.logger.info("GitHub client set to None")

        self.logger.info("Initializing AI manager")
        self.ai_manager = DevBloggerAIProviderManager(settings)
        self.logger.info("AI manager initialized")

        # GUI state
        self.current_repo: Optional[str] = None
        self.selected_commits: list = []
        self.login_dialog: Optional[GitHubLoginDialog] = None
        self.repo_selector: Optional[RepositorySelector] = None
        self.commit_browser: Optional[CommitBrowser] = None
        self.ai_config: Optional[AIConfigurationPanel] = None
        self.blog_editor: Optional[BlogEditor] = None
        self.auth_in_progress: bool = False  # Prevent multiple auth dialogs
        self.logger.info("GUI state variables initialized")

        # Setup window
        self.logger.info("Setting up window")
        self._setup_window()
        self.logger.info("Window setup completed")

        self.logger.info("Setting up UI")
        self._setup_ui()
        self.logger.info("UI setup completed")

        self.logger.info("Setting up bindings")
        self._setup_bindings()
        self.logger.info("Bindings setup completed")

        # Check authentication status
        self.logger.info("Checking authentication status")
        self._check_auth_status()
        self.logger.info("Authentication status check completed")

        # Set initial AI status without testing connections
        self.logger.info("Setting initial AI status")
        self._set_initial_ai_status()
        self.logger.info("Initial AI status set")

    def _setup_window(self):
        """Setup main window properties."""
        # Get window size from settings
        width, height = self.settings.get_window_size()

        # Configure window
        self.title("DevBlogger - Development Blog Generator")
        self.geometry(f"{width}x{height}")
        self.minsize(1000, 700)

        # Disable modal behavior to prevent macOS segfault
        self.wm_attributes("-type", "normal")  # Ensure it's a normal window, not modal

        # Set icon if available
        try:
            self.iconbitmap("assets/devblogger.ico")  # Windows
        except:
            try:
                self.iconphoto(True, ctk.CTkImage("assets/devblogger.png"))  # macOS/Linux
            except:
                pass  # No icon available

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _setup_ui(self):
        """Setup user interface."""
        # Create main container with NO padding and NO frame borders
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Create header
        self._create_header()

        # Create tabbed interface immediately below header
        self._create_tabbed_interface()

    def _create_header(self):
        """Create application header."""
        # Header frame - eliminate all padding
        header_frame = ctk.CTkFrame(self.main_container)
        header_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="DevBlogger",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=(10, 20), pady=10)

        # Status indicators
        self._create_status_indicators(header_frame)

        # Control buttons
        self._create_control_buttons(header_frame)

    def _create_status_indicators(self, parent):
        """Create status indicator widgets."""
        # GitHub status frame
        github_frame = ctk.CTkFrame(parent, fg_color="transparent")
        github_frame.grid(row=0, column=1, padx=(0, 20))

        self.github_status_label = ctk.CTkLabel(
            github_frame,
            text="GitHub: Not Connected",
            font=ctk.CTkFont(size=12)
        )
        self.github_status_label.grid(row=0, column=0)

        self.github_status_indicator = ctk.CTkLabel(
            github_frame,
            text="✗",
            font=ctk.CTkFont(size=16),
            text_color="red"
        )
        self.github_status_indicator.grid(row=0, column=1, padx=(5, 0))

        # AI status frame
        ai_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ai_frame.grid(row=0, column=2, padx=(0, 20))

        self.ai_status_label = ctk.CTkLabel(
            ai_frame,
            text="AI: Not Configured",
            font=ctk.CTkFont(size=12)
        )
        self.ai_status_label.grid(row=0, column=0)

        self.ai_status_indicator = ctk.CTkLabel(
            ai_frame,
            text="✗",
            font=ctk.CTkFont(size=16),
            text_color="red"
        )
        self.ai_status_indicator.grid(row=0, column=1, padx=(5, 0))

    def _create_control_buttons(self, parent):
        """Create control buttons."""
        # Settings button
        settings_button = ctk.CTkButton(
            parent,
            text="Settings",
            command=self._show_settings,
            width=80
        )
        settings_button.grid(row=0, column=3, padx=(0, 10), pady=10)

        # About button
        about_button = ctk.CTkButton(
            parent,
            text="About",
            command=self._show_about,
            width=80
        )
        about_button.grid(row=0, column=4, padx=(0, 10), pady=10)

    def _create_tabbed_interface(self):
        """Create custom tabbed interface with no wasted space."""
        # Create tab buttons frame - positioned immediately below header
        self.tab_buttons_frame = ctk.CTkFrame(self.main_container)
        self.tab_buttons_frame.grid(row=1, column=0, padx=0, pady=0, sticky="ew")

        # Global status banner (hidden by default). Non-modal, non-grabbing. Purely informational.
        self.global_status_frame = ctk.CTkFrame(self.tab_buttons_frame, fg_color=("goldenrod", "goldenrod4"))
        self.global_status_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.global_status_frame.grid_remove()

        self.global_status_label = ctk.CTkLabel(
            self.global_status_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="black"
        )
        self.global_status_label.pack(padx=10, pady=6)

        # Indeterminate progress bar to indicate background work (non-blocking)
        self.global_status_progress = ctk.CTkProgressBar(
            self.global_status_frame,
            mode="indeterminate",
            width=240
        )
        self.global_status_progress.pack(padx=10, pady=(0, 6))
        
        # Create tab content frame - takes up all remaining space
        self.tab_content_frame = ctk.CTkFrame(self.main_container)
        self.tab_content_frame.grid(row=2, column=0, padx=0, pady=0, sticky="nsew")
        self.tab_content_frame.grid_columnconfigure(0, weight=1)
        self.tab_content_frame.grid_rowconfigure(0, weight=1)
        
        # Update main container to give weight to row 2 (content) instead of row 1
        self.main_container.grid_rowconfigure(1, weight=0)  # Tab buttons - no weight
        self.main_container.grid_rowconfigure(2, weight=1)  # Tab content - all weight
        
        # Create tab buttons
        self.current_tab = "GitHub"
        self._create_tab_buttons()
        
        # Create tab content areas
        self._create_tab_contents()
        
        # Show initial tab
        self._show_tab("GitHub")

    def _create_tab_buttons(self):
        """Create custom tab buttons."""
        self.tab_buttons = {}
        
        # GitHub tab button
        github_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="GitHub",
            command=lambda: self._show_tab("GitHub"),
            width=120
        )
        github_btn.grid(row=1, column=0, padx=(5, 2), pady=5)
        self.tab_buttons["GitHub"] = github_btn
        
        # AI Configuration tab button
        ai_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="AI Configuration",
            command=lambda: self._show_tab("AI Configuration"),
            width=120
        )
        ai_btn.grid(row=1, column=1, padx=2, pady=5)
        self.tab_buttons["AI Configuration"] = ai_btn
        
        # Blog Generation tab button
        blog_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="Blog Generation",
            command=lambda: self._show_tab("Blog Generation"),
            width=120
        )
        blog_btn.grid(row=1, column=2, padx=(2, 5), pady=5)
        self.tab_buttons["Blog Generation"] = blog_btn

    def _create_tab_contents(self):
        """Create tab content areas."""
        self.tab_contents = {}
        
        # GitHub tab content
        self._create_github_content()
        
        # AI Configuration tab content
        self._create_ai_content()
        
        # Blog Generation tab content
        self._create_blog_content()

    def _create_github_content(self):
        """Create GitHub tab content."""
        github_content = ctk.CTkFrame(self.tab_content_frame)
        github_content.grid_columnconfigure(0, weight=1)
        github_content.grid_rowconfigure(1, weight=1)
        self.tab_contents["GitHub"] = github_content

        # GitHub controls
        github_controls = ctk.CTkFrame(github_content)
        github_controls.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Scan repositories button
        self.login_button = ctk.CTkButton(
            github_controls,
            text="Scan Available Repos",
            command=self._scan_repositories,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.login_button.grid(row=0, column=0, padx=(0, 10))

        # Repository selection
        self.repo_var = ctk.StringVar()
        self.repo_dropdown = ctk.CTkOptionMenu(
            github_controls,
            variable=self.repo_var,
            values=["Select Repository..."],
            command=self._on_repo_selected,
            width=300
        )
        self.repo_dropdown.grid(row=0, column=1, padx=(0, 10))

        # Refresh repositories button
        def refresh_with_logging():
            self.logger.info("🔴 REFRESH BUTTON CLICKED - Button click registered!")
            self._refresh_repositories()
        
        refresh_repos_button = ctk.CTkButton(
            github_controls,
            text="Refresh",
            command=refresh_with_logging,
            width=80
        )
        refresh_repos_button.grid(row=0, column=2)

        # Main content area for GitHub tab
        self.github_main_area = ctk.CTkFrame(github_content)
        self.github_main_area.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.github_main_area.grid_columnconfigure(0, weight=1)
        self.github_main_area.grid_rowconfigure(0, weight=1)

        # Placeholder for commit browser
        placeholder_label = ctk.CTkLabel(
            self.github_main_area,
            text="Login to GitHub and select a repository to browse commits",
            font=ctk.CTkFont(size=14, slant="italic"),
            text_color="gray"
        )
        placeholder_label.grid(row=0, column=0, padx=20, pady=20)

    def _create_ai_content(self):
        """Create AI configuration tab content."""
        ai_content = ctk.CTkFrame(self.tab_content_frame)
        ai_content.grid_columnconfigure(0, weight=1)
        ai_content.grid_rowconfigure(0, weight=1)
        self.tab_contents["AI Configuration"] = ai_content

        # Create AI configuration panel
        self.ai_config = AIConfigurationPanel(ai_content, self.ai_manager, self.settings)
        self.ai_config.grid(row=0, column=0, sticky="nsew")
        
        # Set callback to update blog editor when AI config changes
        self.ai_config._on_provider_config_changed = self._on_ai_config_changed

    def _create_blog_content(self):
        """Create blog generation tab content."""
        self.blog_content = ctk.CTkFrame(self.tab_content_frame)
        self.blog_content.grid_columnconfigure(0, weight=1)
        self.blog_content.grid_rowconfigure(0, weight=1)
        self.tab_contents["Blog Generation"] = self.blog_content

        # Initially show placeholder
        self._show_blog_placeholder()

    def _show_tab(self, tab_name):
        """Show the specified tab."""
        # Hide all tab contents
        for name, content in self.tab_contents.items():
            content.grid_remove()
        
        # Update button states
        for name, button in self.tab_buttons.items():
            if name == tab_name:
                button.configure(fg_color=("gray75", "gray25"))  # Active state
            else:
                button.configure(fg_color=("gray90", "gray13"))  # Inactive state
        
        # Show selected tab content
        if tab_name in self.tab_contents:
            self.tab_contents[tab_name].grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        
        self.current_tab = tab_name

    def _setup_bindings(self):
        """Setup event bindings."""
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # On focus changes, nudge window state and sanitize toplevels to avoid click-through on macOS
        try:
            self.bind("<FocusIn>", lambda e: self._on_focus_change())
            self.bind("<FocusOut>", lambda e: self._on_focus_change())
        except Exception:
            pass

    def _check_auth_status(self):
        """Check GitHub authentication status."""
        if self.github_auth.is_authenticated():
            self._update_github_status(True)
            self._initialize_github_client()
        else:
            self._update_github_status(False)

    def _update_github_status(self, connected: bool):
        """Update GitHub connection status indicators."""
        if connected:
            user_info = self.github_auth.get_user_info()
            username = user_info.get('login') if user_info else None
            
            if username:
                # User data is available
                self.github_status_label.configure(text=f"GitHub: {username}")
                self.github_status_indicator.configure(text="✓", text_color="green")
            else:
                # User data not yet available, but authentication is in progress
                self.github_status_label.configure(text="GitHub: Authenticating...")
                self.github_status_indicator.configure(text="⏳", text_color="blue")
            
            self.login_button.configure(text="Scan Available Repos", fg_color="green", hover_color="darkgreen")
        else:
            self.github_status_label.configure(text="GitHub: Not Connected")
            self.github_status_indicator.configure(text="✗", text_color="red")
            self.login_button.configure(text="Scan Available Repos", fg_color="green", hover_color="darkgreen")

    def _set_initial_ai_status(self):
        """Set initial AI status without testing connections."""
        try:
            # Just check if providers are configured, don't test connections
            configured_count = 0
            provider_names = []
            
            # Check each provider configuration without testing
            for name, provider in self.ai_manager.get_all_providers().items():
                if provider.is_configured():
                    configured_count += 1
                    provider_names.append(name)
            
            if configured_count > 0:
                # Show first configured provider
                self.ai_status_label.configure(text=f"AI: {provider_names[0]} (configured)")
                self.ai_status_indicator.configure(text="?", text_color="blue")
            else:
                self.ai_status_label.configure(text="AI: Not Configured")
                self.ai_status_indicator.configure(text="✗", text_color="red")
                
        except Exception as e:
            self.logger.error(f"Error setting initial AI status: {e}")
            self.ai_status_label.configure(text="AI: Error")
            self.ai_status_indicator.configure(text="✗", text_color="red")

    def _update_ai_status(self):
        """Update AI status indicators by testing connections."""
        working_providers = self.ai_manager.get_working_providers()
        configured_providers = self.ai_manager.get_configured_providers()

        if working_providers:
            provider_name = working_providers[0]
            self.ai_status_label.configure(text=f"AI: {provider_name}")
            self.ai_status_indicator.configure(text="✓", text_color="green")
        elif configured_providers:
            provider_name = configured_providers[0]
            self.ai_status_label.configure(text=f"AI: {provider_name} (not working)")
            self.ai_status_indicator.configure(text="⚠", text_color="orange")
        else:
            self.ai_status_label.configure(text="AI: Not Configured")
            self.ai_status_indicator.configure(text="✗", text_color="red")

    def _scan_repositories(self):
        """Scan for available repositories and authenticate if needed."""
        self.logger.info("User clicked 'Scan Available Repos' button")

        # Prevent multiple authentication dialogs
        if self.auth_in_progress:
            self.logger.warning("Authentication already in progress, ignoring duplicate request")
            CTkMessagebox(
                title="Authentication In Progress",
                message="Authentication is already in progress. Please wait for the current process to complete.",
                icon="info"
            )
            return

        if not self.github_auth.is_configured():
            self.logger.warning("GitHub OAuth is not configured")
            CTkMessagebox(
                title="Configuration Required",
                message="GitHub OAuth is not configured. Please check your settings first.",
                icon="warning"
            )
            return

        self.logger.info(f"GitHub auth configured: client_id={self.github_auth.client_id[:10]}..., redirect_uri={self.github_auth.redirect_uri}")

        if not self.github_auth.is_authenticated():
            self.logger.info("User not authenticated, starting authentication process")
            self.auth_in_progress = True
            # Need to authenticate first
            self.login_dialog = GitHubLoginDialog(self, self.github_auth, self._on_login_success)
        else:
            self.logger.info("User already authenticated, refreshing repositories")
            # Already authenticated, just refresh repositories
            self._refresh_repositories()

    def _on_login_success(self):
        """Handle successful GitHub login."""
        self.logger.info("Login success callback triggered")
        
        # Reset the auth flag immediately
        self.auth_in_progress = False

        # Track post-auth tasks and wire callbacks
        self._post_auth_pending = {"server": True, "client": True, "stabilize": True}
        try:
            # Ensure UI callbacks from auth use the main window's event loop
            self.github_auth.ui_after = self.after
            # Get notified when the server has fully stopped
            self.github_auth.on_server_stopped = self._on_post_auth_server_stopped
        except Exception:
            pass

        # Start stabilization task to keep UI banner until clicks are reliably accepted
        try:
            self._start_post_auth_stabilization()
        except Exception as e:
            self.logger.warning(f"Could not start post-auth stabilization: {e}")

        # Stop the authentication server immediately (non-blocking)
        if self.github_auth.callback_server:
            self.github_auth._stop_callback_server()
        
        # Set up a callback for when user data becomes available
        self.github_auth.success_callback = self._on_user_data_available
        
        # Update UI immediately - this will show "Authenticating..." if user data isn't ready
        self.logger.info("Authentication completed, updating UI immediately")
        self._update_github_status(True)

        # Show non-blocking status banner to inform user about background steps
        try:
            if hasattr(self, "global_status_frame"):
                self.global_status_label.configure(
                    text=(
                        "Finalizing GitHub authentication... Please wait.\n"
                        "Tasks: stopping local callback server, initializing GitHub client, restoring window focus.\n"
                        "You can continue when this message disappears."
                    )
                )
                self.global_status_frame.grid()
                # Ensure banner is visible above tab buttons
                self.global_status_frame.tkraise()
                # Start non-blocking progress indicator
                if hasattr(self, "global_status_progress"):
                    self.global_status_progress.start()
        except Exception:
            pass

        self._initialize_github_client()
        
        # Restore focus and break potential macOS click-through after auth
        def _restore_focus():
            try:
                self.lift()
                try:
                    # Bounce topmost to force window manager to re-register click region
                    self.attributes("-topmost", True)
                    self.after(100, lambda: self.attributes("-topmost", False))
                except Exception:
                    # Ignore if attribute unsupported
                    pass
                self.focus_force()
                self.update_idletasks()
            except Exception:
                pass
        self.after(200, _restore_focus)
        # Sweep stray toplevels/grabs and normalize mac window style post-auth
        for delay in (100, 300, 700, 1200):
            try:
                self.after(delay, self._sanitize_toplevels)
                self.after(delay + 40, self._mac_nudge_style)
            except Exception:
                pass
    
    def _sanitize_toplevels(self):
        """Aggressively clean up toplevels/attributes to prevent invisible overlays hijacking clicks."""
        try:
            import tkinter as tk
            root = getattr(tk, "_default_root", None) or self

            # Release any global grab if present
            try:
                current = root.grab_current()
                if current:
                    current.grab_release()
            except Exception:
                pass

            # Walk all immediate children (toplevels) and try to normalize
            for w in list(root.winfo_children()):
                try:
                    # Determine if 'w' is a toplevel-like window
                    is_toplevel = False
                    try:
                        if w.winfo_class() == "Toplevel":
                            is_toplevel = True
                    except Exception:
                        pass
                    try:
                        from customtkinter import CTkToplevel  # type: ignore
                        if isinstance(w, CTkToplevel):
                            is_toplevel = True
                    except Exception:
                        pass
                    if not is_toplevel:
                        continue

                    # Normalize window attributes: remove topmost, transparent, ensure alpha=1
                    for attr, value in (("-topmost", False), ("-transparent", False)):
                        try:
                            w.attributes(attr, value)
                        except Exception:
                            pass
                    try:
                        w.attributes("-alpha", 1.0)
                    except Exception:
                        pass
                    try:
                        w.attributes("-type", "normal")
                    except Exception:
                        pass

                    # Release any grab that might remain on this toplevel
                    try:
                        w.grab_release()
                    except Exception:
                        pass

                    # Destroy invisible/hidden shells that can still intercept clicks
                    try:
                        if (not w.winfo_viewable()) or (not w.winfo_ismapped()):
                            w.destroy()
                            continue
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def _start_post_auth_stabilization(self, max_seconds: int = 25, interval_ms: int = 250, good_required: int = 6, jitter_threshold_s: float = 0.12):
        """
        Probe UI event loop responsiveness and finish stabilization as soon as it's responsive.
        - max_seconds: hard cap to avoid hanging banner
        - interval_ms: probe interval
        - good_required: consecutive good probes required to consider UI responsive
        - jitter_threshold_s: acceptable scheduling jitter over interval
        """
        try:
            # Initialize probe state
            self._probe_good_required = max(1, good_required)
            self._probe_good_count = 0
            self._probe_interval = max(50, interval_ms)
            self._probe_threshold = max(0.02, jitter_threshold_s)  # at least 20ms
            self._probe_elapsed_s = 0.0
            self._probe_max_s = max(1, min(max_seconds, 120))
            self._probe_status = "measuring UI responsiveness"

            # Schedule periodic probe
            def _probe_tick():
                try:
                    # Stop if stabilization already completed
                    if not getattr(self, "_post_auth_pending", {}).get("stabilize", False):
                        return

                    start = time.perf_counter()

                    def _on_probe():
                        nonlocal start
                        try:
                            # Measure jitter against desired interval
                            actual = time.perf_counter() - start
                            expected = self._probe_interval / 1000.0
                            jitter = max(0.0, actual - expected)

                            if jitter <= self._probe_threshold:
                                self._probe_good_count += 1
                            else:
                                # Slight decay on bad sample
                                self._probe_good_count = max(0, self._probe_good_count - 1)

                            # Update elapsed and status
                            self._probe_elapsed_s += expected
                            if self._probe_good_count >= self._probe_good_required:
                                self._probe_status = "responsive"
                                # Mark stabilization done
                                if hasattr(self, "_post_auth_pending"):
                                    self._post_auth_pending["stabilize"] = False
                                self._post_auth_check_ready()
                                return
                            else:
                                self._probe_status = f"measuring... jitter {int(jitter*1000)}ms (good {self._probe_good_count}/{self._probe_good_required})"

                            # If exceeded max time, finish anyway
                            if self._probe_elapsed_s >= self._probe_max_s:
                                if hasattr(self, "_post_auth_pending"):
                                    self._post_auth_pending["stabilize"] = False
                                self._post_auth_check_ready()
                                return

                            # Nudge window state and sanitize overlays while probing
                            try:
                                self._mac_nudge_style()
                            except Exception:
                                pass
                            try:
                                self._sanitize_toplevels()
                            except Exception:
                                pass

                            # Schedule next probe
                            self.after(self._probe_interval, _probe_tick)
                            self._post_auth_check_ready()
                        except Exception as e:
                            self.logger.warning(f"Probe callback error: {e}")

                    # Schedule probe callback after interval
                    self.after(self._probe_interval, _on_probe)
                except Exception as e:
                    self.logger.warning(f"Probe scheduling error: {e}")

            # Start probing immediately
            # Ensure stabilize flag is set
            if hasattr(self, "_post_auth_pending"):
                self._post_auth_pending["stabilize"] = True
            self._post_auth_check_ready()
            _probe_tick()

        except Exception as e:
            self.logger.warning(f"Failed to start post-auth stabilization: {e}")

    def _mac_nudge_style(self):
        """On macOS, normalize window style to ensure clicks are accepted after external focus changes."""
        try:
            import sys
            if sys.platform != "darwin":
                return
            # Try unsupported style call to normalize document window behavior
            try:
                self.tk.call("tk::unsupported::MacWindowStyle", "style", self._w, "document", "normal")
            except Exception:
                pass
            # Lift and briefly toggle alpha to 1 to force redraw
            try:
                self.lift()
                self.attributes("-alpha", 0.999)
                self.after(30, lambda: self.attributes("-alpha", 1.0))
            except Exception:
                pass
        except Exception:
            pass

    def _on_focus_change(self):
        """Nudge window manager state and sanitize overlays on focus changes."""
        try:
            # Briefly toggle topmost to re-register click region with window manager
            try:
                self.attributes("-topmost", True)
                self.after(60, lambda: self.attributes("-topmost", False))
            except Exception:
                pass
            # macOS-specific window style nudge
            self.after(80, self._mac_nudge_style)
            # Sanitize toplevels after the bounce
            self.after(120, self._sanitize_toplevels)
        except Exception:
            pass

    def _on_user_data_available(self):
        """Called when user data becomes available after token exchange."""
        self.logger.info("User data available callback triggered")
        # Update the GitHub status now that we have user data
        self._update_github_status(True)

    def _on_post_auth_server_stopped(self):
        """Called when the OAuth callback server has fully stopped (async)."""
        try:
            if not hasattr(self, "_post_auth_pending"):
                self._post_auth_pending = {"server": False, "client": True}
            else:
                self._post_auth_pending["server"] = False
            self._post_auth_check_ready()
        except Exception as e:
            self.logger.warning(f"Error handling post-auth server stopped: {e}")

    def _on_post_auth_client_ready(self):
        """Called when the GitHub client has been initialized on the UI thread."""
        try:
            if not hasattr(self, "_post_auth_pending"):
                self._post_auth_pending = {"server": True, "client": False}
            else:
                self._post_auth_pending["client"] = False
            self._post_auth_check_ready()
        except Exception as e:
            self.logger.warning(f"Error handling post-auth client ready: {e}")

    def _post_auth_check_ready(self):
        """Update banner based on remaining post-auth tasks and hide when all complete."""
        try:
            pending = getattr(self, "_post_auth_pending", {"server": False, "client": False, "stabilize": False})
            remaining = [k for k, v in pending.items() if v]
            if hasattr(self, "global_status_frame"):
                if remaining:
                    tasks_text = ", ".join(remaining)
                    # Optionally append probe status if available
                    if hasattr(self, "_probe_status") and self._probe_status:
                        tasks_text = f"{tasks_text} — {self._probe_status}"
                    self.global_status_label.configure(
                        text=f"Finalizing GitHub authentication... Please wait.\nTasks in progress: {tasks_text}"
                    )
                else:
                    # All tasks completed
                    self.global_status_label.configure(
                        text="Authentication complete — UI is ready. You can continue using DevBlogger."
                    )
                    if hasattr(self, "global_status_progress"):
                        self.global_status_progress.stop()
                    # Hide after brief confirmation
                    self.after(1500, lambda: self.global_status_frame.grid_remove())
        except Exception as e:
            self.logger.warning(f"Error updating post-auth banner: {e}")

    def _initialize_github_client(self):
        """Initialize GitHub API client."""
        def init_client_background():
            try:
                self.logger.info("Initializing GitHub client in background...")
                client = GitHubClient(self.github_auth, self.settings)
                
                # Set client on main thread
                def set_client():
                    self.github_client = client
                    self.logger.info("GitHub client initialized successfully")
                    # Mark client ready; banner will hide when all tasks complete
                    try:
                        self._on_post_auth_client_ready()
                    except Exception:
                        pass
                
                self.after(0, set_client)
                
            except Exception as e:
                self.logger.error(f"Error initializing GitHub client: {e}")
                
                def show_error():
                    CTkMessagebox(
                        title="Error",
                        message=f"Failed to initialize GitHub client: {str(e)}",
                        icon="cancel"
                    )
                
                self.after(0, show_error)
        
        # Initialize client in background thread to avoid any blocking
        threading.Thread(target=init_client_background, daemon=True).start()

    def _refresh_repositories(self):
        """Refresh list of available repositories - only when user clicks Refresh."""
        self.logger.info("=== REFRESH REPOSITORIES CALLED ===")
        
        if not self.github_auth.is_authenticated():
            self.logger.warning("Refresh attempted but not authenticated")
            return
        
        if not self.github_client:
            self.logger.info("Refresh attempted but GitHub client not ready yet")
            return

        # Check if already loading
        if hasattr(self, '_repo_loading') and self._repo_loading:
            self.logger.info("Refresh attempted but already loading")
            return

        self.logger.info("=== STARTING REPOSITORY REFRESH ===")
        
        try:
            # Set loading state
            self._repo_loading = True
            self.logger.info("Set loading state to True")
            
            # Disable controls and show loading
            self.logger.info("Disabling dropdown and showing loading...")
            self.repo_dropdown.configure(state="disabled")
            self.repo_dropdown.set("Loading repositories...")
            self.logger.info("Dropdown configured")
            
            # Disable refresh button and show cancel option
            self.logger.info("Looking for refresh button...")
            refresh_button = None
            for widget in self.repo_dropdown.master.winfo_children():
                if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Refresh":
                    refresh_button = widget
                    break
            
            if refresh_button:
                self.logger.info("Found refresh button, changing to Cancel")
                refresh_button.configure(text="Cancel", command=self._cancel_repo_loading)
            else:
                self.logger.warning("Refresh button not found!")

            self.logger.info("=== STARTING BACKGROUND THREAD ===")
            
            # Load repositories in background thread
            def load_repositories_thread():
                try:
                    self.logger.info("Background thread started - Loading repositories from GitHub...")
                    repositories = self.github_client.get_user_repositories()
                    self.logger.info(f"Got {len(repositories)} repositories from GitHub")
                    repo_names = ["Select Repository..."] + [repo.full_name for repo in repositories]
                    
                    # Schedule UI update on main thread
                    self.logger.info("Scheduling UI update on main thread")
                    self.after(0, lambda: self._update_repository_list(repo_names))

                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"Error loading repositories: {error_msg}")
                    # Schedule error handling on main thread
                    self.after(0, lambda: self._handle_repository_error(error_msg))

            # Start background thread
            self._repo_thread = threading.Thread(target=load_repositories_thread, daemon=True)
            self._repo_thread.start()
            self.logger.info("Background thread started successfully")
            self.logger.info("=== REFRESH REPOSITORIES METHOD COMPLETED ===")

        except Exception as e:
            self.logger.error(f"Error refreshing repositories: {e}")
            self._repo_loading = False
            # Remove the blocking CTkMessagebox here too
            self.logger.error(f"Repository refresh failed: {str(e)}")

    def _cancel_repo_loading(self):
        """Cancel repository loading operation."""
        self.logger.info("User cancelled repository loading")
        
        # Reset loading state
        self._repo_loading = False
        
        # Reset UI
        self.repo_dropdown.configure(state="normal")
        self.repo_dropdown.set("Select Repository...")
        
        # Reset refresh button
        refresh_button = None
        for widget in self.repo_dropdown.master.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Cancel":
                refresh_button = widget
                break
        
        if refresh_button:
            refresh_button.configure(text="Refresh", command=self._refresh_repositories)

    def _update_repository_list(self, repo_names: list):
        """Update repository dropdown with new list."""
        # Reset loading state
        self._repo_loading = False
        
        # Update UI
        self.repo_dropdown.configure(values=repo_names, state="normal")
        self.repo_dropdown.set("Select Repository...")
        
        # Reset refresh button
        refresh_button = None
        for widget in self.repo_dropdown.master.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Cancel":
                refresh_button = widget
                break
        
        if refresh_button:
            refresh_button.configure(text="Refresh", command=self._refresh_repositories)

    def _handle_repository_error(self, error_message: str):
        """Handle repository loading error."""
        # Reset loading state
        self._repo_loading = False
        
        # Reset UI
        self.repo_dropdown.configure(state="normal")
        self.repo_dropdown.set("Select Repository...")
        
        # Reset refresh button
        refresh_button = None
        for widget in self.repo_dropdown.master.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Cancel":
                refresh_button = widget
                break
        
        if refresh_button:
            refresh_button.configure(text="Refresh", command=self._refresh_repositories)
        
        # Show error
        CTkMessagebox(
            title="Error",
            message=f"Failed to load repositories: {error_message}",
            icon="cancel"
        )

    def _on_repo_selected(self, repo_name: str):
        """Handle repository selection."""
        if repo_name == "Select Repository..." or not repo_name:
            return

        self.current_repo = repo_name
        self.logger.info(f"Repository selected: {repo_name}")
        
        # Show immediate feedback to user
        self._show_repository_loading_state()
        
        # Initialize commit browser immediately - no delay needed
        try:
            self._initialize_commit_browser_async()
        except Exception as e:
            self.logger.error(f"Error initializing commit browser: {e}")
            self._show_commit_browser_error(str(e))

    def _show_repository_loading_state(self):
        """Show loading state immediately when repository is selected."""
        # Clear existing content
        self._clear_commit_browser()
        
        # Show loading message
        loading_label = ctk.CTkLabel(
            self.github_main_area,
            text=f"Loading commits for {self.current_repo}...\nPlease wait, this may take a moment.",
            font=ctk.CTkFont(size=14, slant="italic"),
            text_color="blue"
        )
        loading_label.grid(row=0, column=0, padx=20, pady=20)
        
        # Force UI update
        self.update_idletasks()

    def _initialize_commit_browser_async(self):
        """Initialize commit browser for selected repository asynchronously."""
        if not self.current_repo or not self.github_client:
            return

        try:
            self.logger.info(f"Initializing commit browser for {self.current_repo}")
            
            # Clear existing commit browser and placeholder
            self._clear_commit_browser()

            # Create new commit browser (this will start loading commits automatically)
            self.commit_browser = CommitBrowser(
                self.github_main_area,
                self.github_client,
                self.current_repo,
                self.database,
                self._on_commits_selected
            )
            
            # Pack the commit browser to make it visible
            self.commit_browser.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            
            self.logger.info("Commit browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing commit browser: {e}")
            # Show error message to user
            self._show_commit_browser_error(str(e))

    def _show_commit_browser_error(self, error_message: str):
        """Show error message when commit browser fails to initialize."""
        # Clear existing content
        self._clear_commit_browser()
        
        # Show error message
        error_label = ctk.CTkLabel(
            self.github_main_area,
            text=f"Error loading repository: {error_message}\n\nPlease try selecting the repository again.",
            font=ctk.CTkFont(size=14, slant="italic"),
            text_color="red"
        )
        error_label.grid(row=0, column=0, padx=20, pady=20)

    def _clear_commit_browser(self):
        """Clear commit browser and any placeholder content."""
        # Clear existing commit browser
        if self.commit_browser:
            self.commit_browser.destroy()
            self.commit_browser = None
        
        # Clear any existing widgets in the main area (like placeholder labels)
        for widget in self.github_main_area.winfo_children():
            widget.destroy()

    def _on_commits_selected(self, commits: list):
        """Handle commit selection for blog generation."""
        self.selected_commits = commits
        self.logger.info(f"Selected {len(commits)} commits for blog generation")
        
        # Update blog tab status
        self._update_blog_tab_status()
        
        # Initialize blog editor if commits are selected and AI is configured
        if commits and self.current_repo:
            # Check if any providers are configured (don't test connections)
            configured_providers = []
            for name, provider in self.ai_manager.get_all_providers().items():
                if provider.is_configured():
                    configured_providers.append(name)
            
            if configured_providers:
                self._initialize_blog_editor()
            else:
                # Show updated placeholder with current status
                self._show_blog_placeholder()

    def _show_blog_placeholder(self):
        """Show placeholder in blog generation tab."""
        # Clear existing content
        for widget in self.blog_content.winfo_children():
            widget.destroy()
            
        # Create informative placeholder with status
        placeholder_frame = ctk.CTkFrame(self.blog_content)
        placeholder_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Title
        title_label = ctk.CTkLabel(
            placeholder_frame,
            text="Blog Entry Generation",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Requirements checklist
        requirements_label = ctk.CTkLabel(
            placeholder_frame,
            text="Requirements to generate blog entries:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        requirements_label.grid(row=1, column=0, padx=20, pady=(10, 5))
        
        # Check commits status
        commits_status = "✓" if self.selected_commits else "✗"
        commits_color = "green" if self.selected_commits else "red"
        commits_text = f"{commits_status} Commits selected: {len(self.selected_commits) if self.selected_commits else 0}"
        
        commits_label = ctk.CTkLabel(
            placeholder_frame,
            text=commits_text,
            font=ctk.CTkFont(size=12),
            text_color=commits_color
        )
        commits_label.grid(row=2, column=0, padx=20, pady=2, sticky="w")
        
        # Check AI provider status (don't test connections)
        configured_providers = []
        for name, provider in self.ai_manager.get_all_providers().items():
            if provider.is_configured():
                configured_providers.append(name)
        
        if configured_providers:
            ai_status = "?"
            ai_color = "blue"
            ai_text = f"? AI Provider configured: {configured_providers[0]} (click AI Configuration to test)"
        else:
            ai_status = "✗"
            ai_color = "red"
            ai_text = "✗ No AI Provider configured"
        
        ai_label = ctk.CTkLabel(
            placeholder_frame,
            text=ai_text,
            font=ctk.CTkFont(size=12),
            text_color=ai_color
        )
        ai_label.grid(row=3, column=0, padx=20, pady=2, sticky="w")
        
        # Instructions
        if not self.selected_commits:
            instruction_text = "1. Go to the GitHub tab\n2. Login and select a repository\n3. Select commits to generate blog entries from"
        elif not configured_providers:
            instruction_text = "1. Go to the AI Configuration tab\n2. Configure at least one AI provider\n3. Return here to generate blog entries"
        else:
            instruction_text = "All requirements met! The blog editor should appear automatically."
        
        instructions_label = ctk.CTkLabel(
            placeholder_frame,
            text=f"\nNext steps:\n{instruction_text}",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left"
        )
        instructions_label.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="w")

    def _initialize_blog_editor(self):
        """Initialize blog editor with selected commits."""
        if not self.selected_commits or not self.current_repo:
            return
            
        # Clear existing content
        for widget in self.blog_content.winfo_children():
            widget.destroy()
            
        # Create blog editor
        self.blog_editor = BlogEditor(
            self.blog_content,
            self.ai_manager,
            self.settings,
            self.selected_commits,
            self.current_repo
        )
        self.blog_editor.grid(row=0, column=0, sticky="nsew")

    def _show_settings(self):
        """Show application settings."""
        self._show_settings_dialog()

    def _show_settings_dialog(self):
        """Show settings configuration dialog."""
        # Create settings dialog
        settings_dialog = ctk.CTkToplevel(self)
        settings_dialog.title("Settings")
        settings_dialog.geometry("500x400")
        settings_dialog.resizable(False, False)

        # Center on parent without modal behavior to prevent macOS segfault
        settings_dialog.transient(self)
        # Don't use grab_set() as it can cause segfaults on macOS

        # Position dialog
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()

        x = parent_x + (parent_width - 500) // 2
        y = parent_y + (parent_height - 400) // 2

        settings_dialog.geometry(f"+{x}+{y}")

        # Main frame
        main_frame = ctk.CTkFrame(settings_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Application Settings",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # GitHub OAuth Section
        github_frame = ctk.CTkFrame(main_frame)
        github_frame.pack(fill="x", pady=(0, 20))

        github_label = ctk.CTkLabel(
            github_frame,
            text="GitHub OAuth Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        github_label.pack(pady=(10, 10))

        # Client ID
        client_id_frame = ctk.CTkFrame(github_frame, fg_color="transparent")
        client_id_frame.pack(fill="x", pady=(0, 10))

        client_id_label = ctk.CTkLabel(
            client_id_frame,
            text="Client ID:",
            font=ctk.CTkFont(size=12),
            width=100,
            anchor="w"
        )
        client_id_label.pack(side="left", padx=(10, 10))

        client_id_var = ctk.StringVar(value=self.settings.get("github.client_id", ""))
        client_id_entry = ctk.CTkEntry(
            client_id_frame,
            textvariable=client_id_var,
            width=300
        )
        client_id_entry.pack(side="left", padx=(0, 10))

        # Client Secret
        client_secret_frame = ctk.CTkFrame(github_frame, fg_color="transparent")
        client_secret_frame.pack(fill="x", pady=(0, 10))

        client_secret_label = ctk.CTkLabel(
            client_secret_frame,
            text="Client Secret:",
            font=ctk.CTkFont(size=12),
            width=100,
            anchor="w"
        )
        client_secret_label.pack(side="left", padx=(10, 10))

        client_secret_var = ctk.StringVar(value=self.settings.get("github.client_secret", ""))
        client_secret_entry = ctk.CTkEntry(
            client_secret_frame,
            textvariable=client_secret_var,
            show="*",
            width=300
        )
        client_secret_entry.pack(side="left", padx=(0, 10))

        # Redirect URI (optional)
        redirect_uri_frame = ctk.CTkFrame(github_frame, fg_color="transparent")
        redirect_uri_frame.pack(fill="x", pady=(0, 20))

        redirect_uri_label = ctk.CTkLabel(
            redirect_uri_frame,
            text="Redirect URI:",
            font=ctk.CTkFont(size=12),
            width=100,
            anchor="w"
        )
        redirect_uri_label.pack(side="left", padx=(10, 10))

        redirect_uri_var = ctk.StringVar(value=self.settings.get("github.redirect_uri", "http://localhost:8080/callback"))
        redirect_uri_entry = ctk.CTkEntry(
            redirect_uri_frame,
            textvariable=redirect_uri_var,
            width=300
        )
        redirect_uri_entry.pack(side="left", padx=(0, 10))

        # Instructions
        instructions_label = ctk.CTkLabel(
            main_frame,
            text="To get GitHub OAuth credentials:\n1. Go to GitHub Settings > Developer settings > OAuth Apps\n2. Create a new OAuth App or use an existing one\n3. Set Authorization callback URL to: http://localhost:8080/callback",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="left"
        )
        instructions_label.pack(pady=(0, 20))

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        def save_settings():
            """Save settings and close dialog."""
            # Update settings
            self.settings.set("github.client_id", client_id_var.get().strip())
            self.settings.set("github.client_secret", client_secret_var.get().strip())
            self.settings.set("github.redirect_uri", redirect_uri_var.get().strip())

            # Save to file
            try:
                self.settings.save()
                CTkMessagebox(
                    title="Settings Saved",
                    message="Settings have been saved successfully!",
                    icon="check"
                )
            except Exception as e:
                CTkMessagebox(
                    title="Error",
                    message=f"Failed to save settings: {str(e)}",
                    icon="cancel"
                )

            settings_dialog.destroy()

        def cancel_settings():
            """Cancel and close dialog."""
            settings_dialog.destroy()

        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_settings,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_button.pack(side="left", padx=(0, 10))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=cancel_settings,
            fg_color="red",
            hover_color="darkred"
        )
        cancel_button.pack(side="right")

        # Handle dialog closing
        def on_closing():
            settings_dialog.destroy()

        settings_dialog.protocol("WM_DELETE_WINDOW", on_closing)

    def _show_about(self):
        """Show about dialog."""
        CTkMessagebox(
            title="About DevBlogger",
            message="DevBlogger v0.1.0\n\nSemi-automatic development blog system\nfor generating blog entries from GitHub commits.\n\nBuilt with CustomTkinter and Python.",
            icon="info"
        )

    def _on_closing(self):
        """Handle window closing event."""
        # Save window size
        width = self.winfo_width()
        height = self.winfo_height()
        self.settings.set_window_size(width, height)

        # Close GitHub client
        if self.github_client:
            self.github_client.close()

        # Destroy window
        self.destroy()

    def _update_blog_tab_status(self):
        """Update blog tab status and content based on current state."""
        # Check if both requirements are met (don't test connections)
        configured_providers = []
        for name, provider in self.ai_manager.get_all_providers().items():
            if provider.is_configured():
                configured_providers.append(name)
        
        if self.selected_commits and self.current_repo and configured_providers:
            # All requirements met - initialize blog editor
            self._initialize_blog_editor()
        else:
            # Show updated placeholder with current status
            self._show_blog_placeholder()

    def _on_ai_config_changed(self):
        """Handle AI configuration changes."""
        # Don't update AI status automatically - it blocks the GUI
        # User can test connections manually in AI Configuration tab
        
        # Update blog tab status
        self._update_blog_tab_status()
        
        # Refresh blog editor if it exists
        if self.blog_editor:
            self.blog_editor._load_initial_content()
