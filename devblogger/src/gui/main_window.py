#!/usr/bin/env python3
"""
DevBlogger - Main GUI Window
"""

import logging
import threading
from typing import Optional, Dict, Any
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
        # Create main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Create header
        self._create_header()

        # Create tabbed interface
        self._create_tabbed_interface()

    def _create_header(self):
        """Create application header."""
        # Header frame
        header_frame = ctk.CTkFrame(self.main_container)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="DevBlogger",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=(0, 20))

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
        settings_button.grid(row=0, column=3, padx=(0, 10))

        # About button
        about_button = ctk.CTkButton(
            parent,
            text="About",
            command=self._show_about,
            width=80
        )
        about_button.grid(row=0, column=4)

    def _create_tabbed_interface(self):
        """Create tabbed interface for main functionality."""
        # Tab view
        self.tab_view = ctk.CTkTabview(self.main_container)
        self.tab_view.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.tab_view.grid_columnconfigure(0, weight=1)
        self.tab_view.grid_rowconfigure(0, weight=1)

        # Create tabs
        self._create_github_tab()
        self._create_ai_tab()
        self._create_blog_tab()

    def _create_github_tab(self):
        """Create GitHub integration tab."""
        github_tab = self.tab_view.add("GitHub")

        # GitHub tab content
        github_content = ctk.CTkFrame(github_tab)
        github_content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        github_content.grid_columnconfigure(0, weight=1)
        github_content.grid_rowconfigure(1, weight=1)

        # GitHub controls
        github_controls = ctk.CTkFrame(github_content)
        github_controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

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
        refresh_repos_button = ctk.CTkButton(
            github_controls,
            text="Refresh",
            command=self._refresh_repositories,
            width=80
        )
        refresh_repos_button.grid(row=0, column=2)

        # Main content area for GitHub tab
        self.github_main_area = ctk.CTkFrame(github_content)
        self.github_main_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
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

    def _create_ai_tab(self):
        """Create AI configuration tab."""
        ai_tab = self.tab_view.add("AI Configuration")

        # AI tab content
        ai_content = ctk.CTkFrame(ai_tab)
        ai_content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ai_content.grid_columnconfigure(0, weight=1)
        ai_content.grid_rowconfigure(0, weight=1)

        # Placeholder for AI configuration panel
        placeholder_label = ctk.CTkLabel(
            ai_content,
            text="AI Configuration Panel\nConfigure your AI providers here",
            font=ctk.CTkFont(size=14, slant="italic"),
            text_color="gray"
        )
        placeholder_label.grid(row=0, column=0, padx=20, pady=20)

    def _create_blog_tab(self):
        """Create blog generation tab."""
        blog_tab = self.tab_view.add("Blog Generation")

        # Blog tab content
        blog_content = ctk.CTkFrame(blog_tab)
        blog_content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        blog_content.grid_columnconfigure(0, weight=1)
        blog_content.grid_rowconfigure(0, weight=1)

        # Placeholder for blog generation interface
        placeholder_label = ctk.CTkLabel(
            blog_content,
            text="Blog Generation Interface\nGenerate and edit blog entries here",
            font=ctk.CTkFont(size=14, slant="italic"),
            text_color="gray"
        )
        placeholder_label.grid(row=0, column=0, padx=20, pady=20)

    def _setup_bindings(self):
        """Setup event bindings."""
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

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
            username = user_info.get('login', 'Unknown')
            self.github_status_label.configure(text=f"GitHub: {username}")
            self.github_status_indicator.configure(text="✓", text_color="green")
            self.login_button.configure(text="Scan Available Repos", fg_color="green", hover_color="darkgreen")
        else:
            self.github_status_label.configure(text="GitHub: Not Connected")
            self.github_status_indicator.configure(text="✗", text_color="red")
            self.login_button.configure(text="Scan Available Repos", fg_color="green", hover_color="darkgreen")

    def _update_ai_status(self):
        """Update AI status indicators."""
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

    def _show_login_dialog(self):
        """Show GitHub login dialog."""
        if self.github_auth.is_authenticated():
            # User wants to logout
            self._logout_github()
        else:
            # User wants to login
            self.login_dialog = GitHubLoginDialog(self, self.github_auth, self._on_login_success)

    def _logout_github(self):
        """Logout from GitHub."""
        self.github_auth.logout()

        if self.github_client:
            self.github_client.close()
            self.github_client = None

        self._update_github_status(False)
        self._clear_repository_selection()

        CTkMessagebox(
            title="Logged Out",
            message="Successfully logged out from GitHub.",
            icon="info"
        )

    def _on_login_success(self):
        """Handle successful GitHub login."""
        self._update_github_status(True)
        self._initialize_github_client()
        self._refresh_repositories()

        CTkMessagebox(
            title="Login Successful",
            message="Successfully authenticated with GitHub!",
            icon="check"
        )

    def _initialize_github_client(self):
        """Initialize GitHub API client."""
        try:
            self.github_client = GitHubClient(self.github_auth, self.settings)
        except Exception as e:
            self.logger.error(f"Error initializing GitHub client: {e}")
            CTkMessagebox(
                title="Error",
                message=f"Failed to initialize GitHub client: {str(e)}",
                icon="cancel"
            )

    def _refresh_repositories(self):
        """Refresh list of available repositories."""
        if not self.github_auth.is_authenticated() or not self.github_client:
            return

        try:
            # Show loading indicator
            self.repo_dropdown.configure(state="disabled")
            self.repo_dropdown.set("Loading repositories...")

            # Get repositories in a separate thread
            def load_repositories():
                try:
                    repositories = self.github_client.get_user_repositories()
                    repo_names = ["Select Repository..."] + [repo.full_name for repo in repositories]

                    # Update UI in main thread
                    self.after(0, lambda: self._update_repository_list(repo_names))

                except Exception as e:
                    self.logger.error(f"Error loading repositories: {e}")
                    self.after(0, lambda: self._handle_repository_error(str(e)))

            threading.Thread(target=load_repositories, daemon=True).start()

        except Exception as e:
            self.logger.error(f"Error refreshing repositories: {e}")
            CTkMessagebox(
                title="Error",
                message=f"Failed to load repositories: {str(e)}",
                icon="cancel"
            )

    def _update_repository_list(self, repo_names: list):
        """Update repository dropdown with new list."""
        self.repo_dropdown.configure(values=repo_names, state="normal")
        self.repo_dropdown.set("Select Repository...")

    def _handle_repository_error(self, error_message: str):
        """Handle repository loading error."""
        self.repo_dropdown.configure(state="normal")
        self.repo_dropdown.set("Select Repository...")
        CTkMessagebox(
            title="Error",
            message=f"Failed to load repositories: {error_message}",
            icon="cancel"
        )

    def _on_repo_selected(self, repo_name: str):
        """Handle repository selection."""
        if repo_name == "Select Repository...":
            return

        self.current_repo = repo_name
        self._initialize_commit_browser()

    def _clear_repository_selection(self):
        """Clear current repository selection."""
        self.current_repo = None
        self.repo_var.set("Select Repository...")
        self._clear_commit_browser()

    def _initialize_commit_browser(self):
        """Initialize commit browser for selected repository."""
        if not self.current_repo or not self.github_client:
            return

        # Clear existing commit browser
        self._clear_commit_browser()

        # Create new commit browser
        self.commit_browser = CommitBrowser(
            self.github_main_area,
            self.github_client,
            self.current_repo,
            self.database,
            self._on_commits_selected
        )

    def _clear_commit_browser(self):
        """Clear commit browser."""
        if self.commit_browser:
            self.commit_browser.destroy()
            self.commit_browser = None

    def _on_commits_selected(self, commits: list):
        """Handle commit selection for blog generation."""
        self.selected_commits = commits
        self.logger.info(f"Selected {len(commits)} commits for blog generation")

    def _scan_repositories(self):
        """Scan for available repositories and authenticate if needed."""
        self.logger.info("User clicked 'Scan Available Repos' button")

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
            # Need to authenticate first
            self.login_dialog = GitHubLoginDialog(self, self.github_auth, self._on_login_success)
        else:
            self.logger.info("User already authenticated, refreshing repositories")
            # Already authenticated, just refresh repositories
            self._refresh_repositories()

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
