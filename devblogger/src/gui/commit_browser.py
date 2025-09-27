#!/usr/bin/env python3
"""
DevBlogger - Commit Browser Component
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import customtkinter as ctk
from CTkListbox import CTkListbox
import tkinter as tk
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

from ..github.client import GitHubClient
from ..github.models import GitHubCommit
from ..config.database import DatabaseManager


class CommitBrowser(ctk.CTkFrame):
    """Commit browser with filtering and selection capabilities."""

    def __init__(
        self,
        parent,
        github_client: GitHubClient,
        repository: str,
        database: DatabaseManager,
        on_commits_selected: Callable[[List[GitHubCommit]], None],
        on_busy_state_change: Optional[Callable[[bool, str], None]] = None
    ):
        """Initialize commit browser."""
        super().__init__(parent)

        self.github_client = github_client
        self.repository = repository
        self.database = database
        self.on_commits_selected = on_commits_selected
        self.on_busy_change = on_busy_state_change
        self.logger = logging.getLogger(__name__)

        # State
        self.all_commits: List[GitHubCommit] = []
        self.filtered_commits: List[GitHubCommit] = []
        self.selected_commits: List[GitHubCommit] = []
        self.commit_message_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        # Loading state
        self.loading_commits = False
        self.load_thread = None

        # UI components
        self.commit_listbox: Optional[CTkListbox] = None
        self.preview_text: Optional[tk.Text] = None
        self.load_button: Optional[ctk.CTkButton] = None
        # Reusable font for row widgets to avoid per-row font construction cost
        self._row_font = ctk.CTkFont(size=11)

        # Busy state (DB operations)
        self.db_busy: bool = False
        self.refresh_button: Optional[ctk.CTkButton] = None
        self.select_all_message_cb: Optional[ctk.CTkCheckBox] = None
        # Cache processed status to avoid repeated DB reads across filter changes
        self._processed_cache: Dict[str, Dict[str, bool]] = {}
        # Fast lookup maps to avoid DB calls on selection
        self._index_to_commit: Dict[int, GitHubCommit] = {}
        self._text_to_commit: Dict[str, GitHubCommit] = {}

        # Setup UI
        self._setup_ui()
        # Show initial state instead of auto-loading
        self._show_initial_state()

    def _show_initial_state(self):
        """Show initial state with load button instead of auto-loading."""
        # Clear any existing content
        self.commit_listbox.delete(0, "end")
        
        # Show initial message with load button
        self.commit_listbox.insert(0, f"Repository: {self.repository}")
        self.commit_listbox.insert(1, "Click 'Load Commits' or 'Refresh' to load commits from GitHub")
        
        # Update count
        self.count_label.configure(text="No commits loaded")
        
        # Show initial preview
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", f"Repository: {self.repository}\n\n")
        self.preview_text.insert("2.0", "Click 'Load Commits' or 'Refresh' to start loading commits from GitHub.\n\n")
        self.preview_text.insert("3.0", "You can then use the filters to narrow down the results and select commits for blog generation.")
        self.preview_text.configure(state="disabled")

    def _setup_ui(self):
        """Setup user interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Controls frame
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(1, weight=1)

        # Filter controls
        self._create_filter_controls(controls_frame)

        # Main content area
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Create paned window for list and preview
        self._create_paned_interface(content_frame)

    def _create_filter_controls(self, parent):
        """Create filter control widgets."""
        # Left side controls
        left_controls = ctk.CTkFrame(parent, fg_color="transparent")
        left_controls.grid(row=0, column=0, padx=(0, 20))

        # Date range filter
        date_label = ctk.CTkLabel(left_controls, text="Date Range:")
        date_label.grid(row=0, column=0, padx=(0, 10))

        self.date_var = ctk.StringVar(value="Last 30 days")
        date_options = ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
        date_dropdown = ctk.CTkOptionMenu(
            left_controls,
            variable=self.date_var,
            values=date_options,
            command=self._apply_filters,
            width=120
        )
        date_dropdown.grid(row=0, column=1)

        # Max commits filter
        max_label = ctk.CTkLabel(left_controls, text="Max Commits:")
        max_label.grid(row=1, column=0, padx=(0, 10), pady=(10, 0))

        self.max_var = ctk.StringVar(value="50")
        max_options = ["25", "50", "100", "200", "All"]
        max_dropdown = ctk.CTkOptionMenu(
            left_controls,
            variable=self.max_var,
            values=max_options,
            command=self._apply_filters,
            width=80
        )
        max_dropdown.grid(row=1, column=1, pady=(10, 0))

        # Right side controls
        right_controls = ctk.CTkFrame(parent, fg_color="transparent")
        right_controls.grid(row=0, column=1, sticky="e")

        # Search filter
        search_label = ctk.CTkLabel(right_controls, text="Search:")
        search_label.grid(row=0, column=0, padx=(0, 10))

        self.search_var = ctk.StringVar()
        # Use trace_add for Python 3.13+ compatibility
        try:
            self.search_var.trace_add("write", self._on_search_change)
        except AttributeError:
            # Fallback for older Python versions
            self.search_var.trace("w", self._on_search_change)
        search_entry = ctk.CTkEntry(
            right_controls,
            textvariable=self.search_var,
            placeholder_text="Search commits...",
            width=200
        )
        search_entry.grid(row=0, column=1, padx=(0, 10))

        # Refresh button
        self.refresh_button = ctk.CTkButton(
            right_controls,
            text="Refresh",
            command=self._load_commits,
            width=80
        )
        self.refresh_button.grid(row=0, column=2)

    def _create_paned_interface(self, parent):
        """Create paned interface with list and preview."""
        # Create paned window
        paned_window = ctk.CTkFrame(parent)
        paned_window.grid(row=0, column=0, sticky="nsew")
        paned_window.grid_columnconfigure(0, weight=1)
        paned_window.grid_rowconfigure(0, weight=1)

        # Left side - commit list
        list_frame = ctk.CTkFrame(paned_window)
        list_frame.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Commit list header
        list_header = ctk.CTkFrame(list_frame)
        list_header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Select all checkboxes
        self.select_all_message_var = ctk.BooleanVar()
        self.select_all_message_cb = ctk.CTkCheckBox(
            list_header,
            text="Include Commits",
            variable=self.select_all_message_var,
            command=self._toggle_select_all_messages
        )
        self.select_all_message_cb.grid(row=0, column=0)


        # Commit count label
        self.count_label = ctk.CTkLabel(
            list_header,
            text="0 commits",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.count_label.grid(row=0, column=1, padx=(20, 0))

        # Busy indicator (hidden by default)
        self.busy_label = ctk.CTkLabel(
            list_header,
            text="Working...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="black"
        )
        self.busy_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.busy_label.grid_remove()

        self.busy_progress = ctk.CTkProgressBar(list_header, mode="indeterminate", width=160)
        self.busy_progress.grid(row=1, column=2, sticky="e", pady=(6, 0))
        self.busy_progress.grid_remove()

        # Scrollable commit list
        list_container = ctk.CTkFrame(list_frame)
        list_container.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)

        # Create custom listbox for commits
        self.commit_listbox = CTkListbox(
            list_container,
            height=400,
            command=self._on_commit_selected
        )
        self.commit_listbox.grid(row=0, column=0, sticky="nsew")

        # Right side - preview
        preview_frame = ctk.CTkFrame(paned_window)
        preview_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        # Preview header
        preview_header = ctk.CTkFrame(preview_frame)
        preview_header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        preview_title = ctk.CTkLabel(
            preview_header,
            text="Commit Preview",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        preview_title.grid(row=0, column=0)

        # Preview text area
        preview_container = ctk.CTkFrame(preview_frame)
        preview_container.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_rowconfigure(0, weight=1)

        self.preview_text = tk.Text(
            preview_container,
            wrap="word"
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        # Scrollbar for preview
        try:
            yscroll_prev = ctk.CTkScrollbar(preview_container, command=self.preview_text.yview)
            yscroll_prev.grid(row=0, column=1, sticky="ns")
            self.preview_text.configure(yscrollcommand=yscroll_prev.set)
        except Exception:
            pass
        # Start disabled; enable when writing
        self.preview_text.configure(state="disabled")

    def _load_commits(self):
        """Load commits from GitHub with smart loading and user confirmation."""
        # Notify global UI that heavy work is starting
        self._notify_busy(True, "Loading commits from GitHub...")
        def load_commits_thread():
            try:
                self.logger.info(f"Loading commits for {self.repository}")

                # Show loading state on main thread
                self.after(0, self._show_loading_state)

                # First, get a small sample to check repository size
                owner, repo = self.repository.split('/')
                
                # Get initial batch of commits to estimate total
                initial_commits = self.github_client.get_repository_commits(
                    owner=owner,
                    repo=repo,
                    per_page=100  # Get first 100 commits
                )
                
                self.logger.info(f"Initial batch loaded: {len(initial_commits)} commits")
                
                # If we got exactly 100 commits, there might be more
                if len(initial_commits) == 100:
                    # Check if there are more commits by trying to get page 2
                    try:
                        second_batch = self.github_client.get_repository_commits(
                            owner=owner,
                            repo=repo,
                            per_page=50,
                            page=2
                        )
                        
                        if len(second_batch) > 0:
                            # There are more than 100 commits, ask user
                            estimated_total = len(initial_commits) + len(second_batch)
                            self.logger.info(f"Repository has more than 100 commits (estimated: {estimated_total}+)")
                            
                            # Ask user on main thread
                            def ask_user():
                                self._ask_load_more_commits(initial_commits, estimated_total)
                            
                            self.after(0, ask_user)
                            return
                        else:
                            # Exactly 100 commits or less
                            all_commits = initial_commits
                    except Exception as e:
                        self.logger.warning(f"Could not check for additional commits: {e}")
                        # Just use the initial batch
                        all_commits = initial_commits
                else:
                    # Less than 100 commits, use what we have
                    all_commits = initial_commits

                # Store commits and apply filters on main thread
                def update_commits():
                    self.all_commits = all_commits
                    self.logger.info(f"Loaded {len(all_commits)} commits")
                    # Inform global UI we are now indexing/rendering
                    self._notify_busy(True, "Indexing and rendering commits...")
                    self._apply_filters()

                self.after(0, update_commits)

            except Exception as e:
                self.logger.error(f"Error loading commits: {e}")
                self.after(0, lambda: self._show_error(f"Failed to load commits: {str(e)}"))

        threading.Thread(target=load_commits_thread, daemon=True).start()

    def _ask_load_more_commits(self, initial_commits: List[GitHubCommit], estimated_total: int):
        """Ask user whether to load all commits or just the first 100."""
        try:
            # Create confirmation dialog
            dialog = ctk.CTkToplevel(self)
            dialog.title("Load More Commits?")
            dialog.geometry("500x300")
            dialog.resizable(False, False)
            
            # Center on parent
            dialog.transient(self.winfo_toplevel())
            
            # Position dialog
            parent = self.winfo_toplevel()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            x = parent_x + (parent_width - 500) // 2
            y = parent_y + (parent_height - 300) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            title_label = ctk.CTkLabel(
                main_frame,
                text="Repository Has Many Commits",
                font=ctk.CTkFont(size=18, weight="bold")
            )
            title_label.pack(pady=(0, 20))
            
            # Message
            message_text = (
                f"This repository has more than 100 commits (estimated {estimated_total}+).\n\n"
                "Loading all commits will provide complete filtering capabilities but may take longer "
                "and use more memory.\n\n"
                "What would you like to do?"
            )
            
            message_label = ctk.CTkLabel(
                main_frame,
                text=message_text,
                font=ctk.CTkFont(size=12),
                wraplength=450,
                justify="left"
            )
            message_label.pack(pady=(0, 30))
            
            # Button frame
            button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            button_frame.pack(fill="x", pady=(20, 0))
            
            # Result variable
            result = {"choice": None}
            
            def load_all():
                result["choice"] = "all"
                dialog.destroy()
            
            def load_100():
                result["choice"] = "100"
                dialog.destroy()
            
            # Load all button
            load_all_btn = ctk.CTkButton(
                button_frame,
                text=f"Load All Commits (~{estimated_total}+)",
                command=load_all,
                fg_color="green",
                hover_color="darkgreen",
                width=200
            )
            load_all_btn.pack(side="left", padx=(0, 10))
            
            # Load 100 button
            load_100_btn = ctk.CTkButton(
                button_frame,
                text="Load Latest 100 Only",
                command=load_100,
                fg_color="blue",
                hover_color="darkblue",
                width=200
            )
            load_100_btn.pack(side="right")
            
            # Performance info
            info_label = ctk.CTkLabel(
                main_frame,
                text="💡 Tip: You can always use filters to narrow down the results after loading",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color="gray"
            )
            info_label.pack(pady=(20, 0))
            
            # Don't wait for dialog - let button callbacks handle the choice
            # The dialog will be destroyed by the button callbacks
            
            # Set up callbacks that will be called when buttons are clicked
            def handle_load_all():
                self._load_all_commits_background()
            
            def handle_load_100():
                self.all_commits = initial_commits
                self.logger.info(f"Using initial {len(initial_commits)} commits")
                self._apply_filters()
            
            # Update button commands to use the handlers
            load_all_btn.configure(command=lambda: [handle_load_all(), dialog.destroy()])
            load_100_btn.configure(command=lambda: [handle_load_100(), dialog.destroy()])
                
        except Exception as e:
            self.logger.error(f"Error showing commit loading dialog: {e}")
            # Fallback to using initial commits
            self.all_commits = initial_commits
            self.logger.info(f"Fallback: Using initial {len(initial_commits)} commits")
            self._apply_filters()

    def _load_all_commits_background(self):
        """Load all commits in background with progress indication."""
        def load_all_thread():
            try:
                self.logger.info("Loading all commits...")
                
                # Update loading state
                self.after(0, lambda: self._show_loading_state_with_progress("Loading all commits..."))
                
                owner, repo = self.repository.split('/')
                all_commits = []
                page = 1
                per_page = 100
                
                while True:
                    # Get commits for this page
                    commits_batch = self.github_client.get_repository_commits(
                        owner=owner,
                        repo=repo,
                        per_page=per_page,
                        page=page
                    )
                    
                    if not commits_batch:
                        break
                    
                    all_commits.extend(commits_batch)
                    self.logger.info(f"Loaded page {page}: {len(commits_batch)} commits (total: {len(all_commits)})")
                    
                    # Update progress on main thread
                    self.after(0, lambda total=len(all_commits): 
                              self._show_loading_state_with_progress(f"Loading commits... ({total} loaded)"))
                    
                    # If we got less than per_page, we're done
                    if len(commits_batch) < per_page:
                        break
                    
                    page += 1
                    
                    # Safety limit to prevent infinite loading
                    if page > 50:  # Max 5000 commits
                        self.logger.warning(f"Reached safety limit of {page-1} pages, stopping")
                        break
                
                # Store commits and apply filters on main thread
                def update_commits():
                    self.all_commits = all_commits
                    self.logger.info(f"Loaded all {len(all_commits)} commits")
                    self._apply_filters()
                
                self.after(0, update_commits)
                
            except Exception as e:
                self.logger.error(f"Error loading all commits: {e}")
                self.after(0, lambda: self._show_error(f"Failed to load all commits: {str(e)}"))
        
        threading.Thread(target=load_all_thread, daemon=True).start()

    def _show_loading_state_with_progress(self, message: str):
        """Show loading state with custom progress message."""
        self.commit_listbox.delete(0, "end")
        self.commit_listbox.insert(0, message)
        self.count_label.configure(text="Loading...")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", f"{message}\nPlease wait...")
        self.preview_text.configure(state="disabled")

    def _show_loading_state(self):
        """Show loading state in UI."""
        self.commit_listbox.delete(0, "end")
        self.commit_listbox.insert(0, "Loading commits...")
        self.count_label.configure(text="Loading...")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", "Loading commit details...")
        self.preview_text.configure(state="disabled")

    def _show_error(self, message: str):
        """Show error message."""
        self.commit_listbox.delete(0, "end")
        self.commit_listbox.insert(0, f"Error: {message}")
        self.count_label.configure(text="Error loading commits")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", f"Error: {message}")
        self.preview_text.configure(state="disabled")

    def _apply_filters(self, *args):
        """Apply filters to commit list."""
        if not self.all_commits:
            return

        try:
            # Get filter values
            date_range = self.date_var.get()
            max_commits = self.max_var.get()
            search_term = self.search_var.get().lower()

            # Filter by date
            filtered = self._filter_by_date(self.all_commits, date_range)

            # Filter by search term
            if search_term:
                filtered = self._filter_by_search(filtered, search_term)

            # Limit number of commits
            if max_commits != "All":
                max_count = int(max_commits)
                filtered = filtered[:max_count]

            # Update filtered list
            self.filtered_commits = filtered
            self._update_commit_list()

        except Exception as e:
            self.logger.error(f"Error applying filters: {e}")

    def _filter_by_date(self, commits: List[GitHubCommit], date_range: str) -> List[GitHubCommit]:
        """Filter commits by date range."""
        if date_range == "All time":
            return commits

        # Calculate cutoff date - use UTC timezone to match GitHub API dates
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if date_range == "Last 7 days":
            cutoff = now - timedelta(days=7)
        elif date_range == "Last 30 days":
            cutoff = now - timedelta(days=30)
        elif date_range == "Last 90 days":
            cutoff = now - timedelta(days=90)
        else:
            return commits

        # Filter commits
        filtered = []
        for commit in commits:
            if commit.date:
                # Ensure both dates are timezone-aware for comparison
                commit_date = commit.date
                if commit_date.tzinfo is None:
                    # If commit date is naive, assume UTC
                    commit_date = commit_date.replace(tzinfo=timezone.utc)
                
                if commit_date > cutoff:
                    filtered.append(commit)

        return filtered

    def _filter_by_search(self, commits: List[GitHubCommit], search_term: str) -> List[GitHubCommit]:
        """Filter commits by search term."""
        filtered = []
        for commit in commits:
            # Search in commit message and author name
            message_match = search_term in commit.message.lower()
            author_match = commit.author.name and search_term in commit.author.name.lower()

            if message_match or author_match:
                filtered.append(commit)

        return filtered

    def _update_commit_list(self):
        """Update the commit list display with maximum UI responsiveness."""
        # Clear existing items immediately
        self.commit_listbox.delete(0, "end")
        self.commit_message_checkboxes.clear()
        # Reset selection lookup maps
        self._index_to_commit.clear()
        self._text_to_commit.clear()

        if not self.filtered_commits:
            self.commit_listbox.insert(0, "No commits found")
            self.count_label.configure(text="0 commits")
            return

        # Show immediate feedback
        self.count_label.configure(text=f"Loading {len(self.filtered_commits)} commits...")
        # Notify parent: checking processed status in background
        self._notify_busy(True, "Checking processed status...")
        
        # Do ALL heavy work in background thread to keep UI completely responsive
        def load_commits_background():
            try:
                # Batch database queries in background
                processed_commits = self._batch_check_processed_commits(self.filtered_commits)
                
                # Schedule UI update on main thread with all data ready
                self.after(0, lambda: self._populate_commit_list_fast(processed_commits))
                
            except Exception as e:
                self.logger.error(f"Error preparing commit list: {e}")
                self.after(0, lambda: self._show_error(f"Error loading commits: {str(e)}"))
        
        # Start background thread immediately
        threading.Thread(target=load_commits_background, daemon=True).start()
    def _populate_commit_list_fast(self, processed_commits: Dict[str, Dict[str, bool]]):
        """Populate commit list progressively to keep UI responsive."""
        # Start render profiling
        try:
            self._render_start_time = time.perf_counter()
        except Exception:
            pass
        # Notify global UI that we are rendering rows
        self._notify_busy(True, "Rendering commit list...")
        self.count_label.configure(text=f"Rendering {len(self.filtered_commits)} commits...")
        # Start progressive rendering
        self._add_rows_progressively(0, processed_commits)

        # Update global checkbox states based on actual commit status
        self._update_global_checkbox_states(processed_commits)

        # Initial preview deferred to finalize to reduce work during progressive render

    def _update_global_checkbox_states(self, processed_commits: Dict[str, Dict[str, bool]]):
        """Update global message checkbox state based on processing status."""
        if not self.filtered_commits:
            return
        message_count = 0
        for commit in self.filtered_commits:
            processed_status = processed_commits.get(commit.sha, {'message': False})
            if processed_status.get('message', False):
                message_count += 1
        self.select_all_message_var.set(message_count == len(self.filtered_commits))

    def _batch_check_processed_commits(self, commits: List[GitHubCommit]) -> Dict[str, Dict[str, bool]]:
        """Batch check processed status (message only) to reduce database calls, with caching."""
        processed_status: Dict[str, Dict[str, bool]] = {}
        try:
            for commit in commits:
                sha = commit.sha
                cache_entry = self._processed_cache.get(sha, {})
                msg_known = "message" in cache_entry
                msg = cache_entry.get("message", False)
                if not msg_known:
                    try:
                        msg = self.database.is_commit_processed(self.repository, sha, "message")
                    except Exception:
                        msg = False
                cache_entry = self._processed_cache.setdefault(sha, {})
                cache_entry["message"] = msg
                processed_status[sha] = {"message": msg}
        except Exception as e:
            self.logger.error(f"Error batch checking processed commits: {e}")
            for commit in commits:
                sha = commit.sha
                processed_status[sha] = {"message": self._processed_cache.get(sha, {}).get("message", False)}
        return processed_status

    def _add_commits_progressively(self, start_index: int, processed_commits: Dict[str, Dict[str, bool]]):
        """Legacy progressive adder (unused)."""
        # Kept for backward compatibility; new code uses _add_rows_progressively.
        self._add_rows_progressively(start_index, processed_commits)

    def _add_rows_progressively(self, start_index: int, processed_commits: Dict[str, Dict[str, bool]]):
        """Add rows progressively (checkboxes + label) to keep UI snappy."""
        # Use small batch size and a tiny timeout to interleave with user input events
        batch_size = 6
        end_index = min(start_index + batch_size, len(self.filtered_commits))

        for i in range(start_index, end_index):
            commit = self.filtered_commits[i]
            status = processed_commits.get(commit.sha, {'message': False})
            self._create_row(i, commit, status)

        # Process pending UI events right after each batch so clicks are handled
        try:
            self.update()
        except Exception:
            pass

        # Update progress and schedule next batch
        if end_index < len(self.filtered_commits):
            if end_index % 25 == 0:
                self.count_label.configure(text=f"{end_index}/{len(self.filtered_commits)} commits rendered")
            # Interleave with user events explicitly using a tiny delay
            self.after(10, lambda: self._add_rows_progressively(end_index, processed_commits))
        else:
            self._finalize_commit_list()

    def _finalize_commit_list(self):
        """Finalize the commit list after all commits have been added."""
        # Update final count
        self.count_label.configure(text=f"{len(self.filtered_commits)} commits")

        # Set initial preview if commits exist
        if self.filtered_commits:
            self._update_preview(self.filtered_commits[0])

        # Done rendering, clear global busy
        try:
            if hasattr(self, "_render_start_time"):
                elapsed = time.perf_counter() - self._render_start_time
                rows = len(self.filtered_commits)
                rps = (rows / elapsed) if elapsed > 0 else rows
                self.logger.info(f"[PROFILE] Commit list rendered: {rows} rows in {elapsed:.2f}s ({rps:.1f} rows/s)")
        except Exception:
            pass
        self._notify_busy(False, "")

    def _format_commit_display(self, commit: GitHubCommit) -> str:
        """Format commit for display in list (non-blocking; no DB calls)."""
        # Short SHA
        short_sha = commit.sha[:8]

        # Author name (short)
        author_name = commit.author.name or commit.author.login or "Unknown"
        if len(author_name) > 20:
            author_name = author_name[:17] + "..."

        # Short message
        message = commit.message.split('\n')[0]  # First line only
        if len(message) > 60:
            message = message[:57] + "..."

        # Format date
        date_str = commit.date.strftime("%m/%d %H:%M") if commit.date else "Unknown"

        # Determine processed state from cache only to avoid UI-thread DB I/O
        cache = self._processed_cache.get(commit.sha, {})
        processed = bool(cache.get("message"))
        status = "✓" if processed else " "

        return f"{status} {short_sha} | {author_name} | {date_str} | {message}"

    def _format_commit_display_with_status(self, commit: GitHubCommit, processed_status: Dict[str, bool]) -> str:
        """Format commit for display in list with message processing status only."""
        short_sha = commit.sha[:8]
        author_name = commit.author.name or commit.author.login or "Unknown"
        if len(author_name) > 20:
            author_name = author_name[:17] + "..."
        message = commit.message.split('\n')[0]
        if len(message) > 60:
            message = message[:57] + "..."
        date_str = commit.date.strftime("%m/%d %H:%M") if commit.date else "Unknown"
        msg_status = "M" if processed_status.get('message', False) else " "
        status = f"[{msg_status}]"
        return f"{status} {short_sha} | {author_name} | {date_str} | {message}"

    def _on_commit_selected(self, selection):
        """Handle commit selection in listbox."""
        if self.db_busy:
            # Ignore selection while DB is busy to prevent race conditions
            return
        if selection is None or not self.filtered_commits:
            return

        try:
            # Prefer fast lookup maps to avoid DB queries in selection path
            if isinstance(selection, str):
                commit = self._text_to_commit.get(selection)
                if commit:
                    self._update_preview(commit)
            elif isinstance(selection, int):
                commit = self._index_to_commit.get(selection)
                if commit:
                    self._update_preview(commit)
        except Exception as e:
            self.logger.error(f"Error handling commit selection: {e}")

    def _update_preview(self, commit: GitHubCommit):
        """Update commit preview pane."""
        if not self.preview_text:
            return

        try:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")

            # Commit header
            self.preview_text.insert("1.0", f"Commit: {commit.sha}\n")
            self.preview_text.insert("2.0", f"Author: {commit.author.name or commit.author.login or 'Unknown'}\n")
            self.preview_text.insert("3.0", f"Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S') if commit.date else 'Unknown'}\n")
            self.preview_text.insert("4.0", f"Repository: {self.repository}\n\n")

            # Commit message
            self.preview_text.insert("5.0", "Message:\n")
            self.preview_text.insert("6.0", f"{commit.message}\n\n")

            # Commit stats if available
            if commit.stats:
                self.preview_text.insert("7.0", "Changes:\n")
                if commit.stats.get('additions'):
                    self.preview_text.insert("8.0", f"  +{commit.stats['additions']} additions\n")
                if commit.stats.get('deletions'):
                    self.preview_text.insert("9.0", f"  -{commit.stats['deletions']} deletions\n")
                if commit.stats.get('total'):
                    self.preview_text.insert("10.0", f"  {commit.stats['total']} total changes\n")
                self.preview_text.insert("11.0", "\n")

            # File changes if available
            if commit.files:
                self.preview_text.insert("12.0", "Files Changed:\n")
                for file_info in commit.files[:10]:  # Limit to first 10 files
                    filename = file_info.get('filename', 'Unknown')
                    status = file_info.get('status', 'Unknown')
                    additions = file_info.get('additions', 0)
                    deletions = file_info.get('deletions', 0)

                    self.preview_text.insert("13.0", f"  {status} {filename}")
                    if additions:
                        self.preview_text.insert("14.0", f" (+{additions})")
                    if deletions:
                        self.preview_text.insert("15.0", f" (-{deletions})")
                    self.preview_text.insert("16.0", "\n")

                if len(commit.files) > 10:
                    self.preview_text.insert("17.0", f"  ... and {len(commit.files) - 10} more files\n")

            self.preview_text.configure(state="disabled")

        except Exception as e:
            self.logger.error(f"Error updating preview: {e}")
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"Error loading preview: {str(e)}")
            self.preview_text.configure(state="disabled")



    def _on_search_change(self, *args):
        """Handle search text change."""
        # Debounce search - apply after 500ms of no typing
        if hasattr(self, '_search_timer'):
            self.after_cancel(self._search_timer)

        self._search_timer = self.after(500, self._apply_filters)

    def refresh(self):
        """Refresh commit list."""
        self._load_commits()

    def get_selected_commits(self) -> List[GitHubCommit]:
        """Get currently selected commits."""
        return self.selected_commits.copy()

    def clear_selection(self):
        """Clear all selections."""
        self.selected_commits.clear()
        try:
            for cb in self.commit_message_checkboxes.values():
                try:
                    cb.deselect()
                except Exception:
                    pass
        except Exception:
            pass
        self.on_commits_selected(self.selected_commits)



    def _toggle_select_all_messages(self):
        """Toggle select all messages for processing."""
        if self.db_busy:
            return
        select_all = self.select_all_message_var.get()

        # Enter busy state
        self._set_busy(True, "Updating message selections...")

        # Log the click immediately for debugging
        self.logger.info(f"🔴 PROCESS MESSAGES CHECKBOX CLICKED - select_all: {select_all}")

        # Update UI immediately for maximum responsiveness
        for commit in self.filtered_commits:
            if select_all:
                if commit not in self.selected_commits:
                    self.selected_commits.append(commit)

        # Notify parent of selection change immediately
        self.on_commits_selected(self.selected_commits)

        # Update UI row checkboxes immediately
        for sha, cb in self.commit_message_checkboxes.items():
            try:
                if select_all:
                    cb.select()
                else:
                    cb.deselect()
            except Exception:
                pass

        # Do ALL database operations in background thread - don't block GUI at all
        def update_database():
            try:
                self.logger.info(f"Background thread: Processing {len(self.filtered_commits)} commits for messages")
                
                to_remove: List[GitHubCommit] = []
                for commit in self.filtered_commits:
                    if select_all:
                        self.database.mark_commit_processed(self.repository, commit.sha, "message")
                    else:
                        self.database.mark_commit_unprocessed(self.repository, commit.sha, "message")
                        # Update cache and selection without extra DB reads
                        try:
                            self._processed_cache.setdefault(commit.sha, {})["message"] = False
                            other_selected = False
                        except Exception:
                            other_selected = False
                        if not other_selected:
                            to_remove.append(commit)
                
                self.logger.info("Background thread: Database operations completed for messages")
                # Apply removals once on UI thread
                def apply_removals():
                    try:
                        for c in to_remove:
                            if c in self.selected_commits:
                                self.selected_commits.remove(c)
                        self.on_commits_selected(self.selected_commits)
                    except Exception:
                        pass
                    finally:
                        self._set_busy(False)
                self.after(0, apply_removals)
                
            except Exception as e:
                self.logger.error(f"Error updating database for messages: {e}")

        # Start background thread immediately - don't wait
        threading.Thread(target=update_database, daemon=True).start()
        self.logger.info("Background thread started for message processing")


    def _refresh_display(self):
        """Refresh the display to show updated processing status."""
        # Quick refresh without reloading from database
        def refresh_background():
            try:
                # Get current processing status
                processed_commits = self._batch_check_processed_commits(self.filtered_commits)
                
                # Update display on main thread
                self.after(0, lambda: self._update_display_status(processed_commits))
                
            except Exception as e:
                self.logger.error(f"Error refreshing display: {e}")
        
        threading.Thread(target=refresh_background, daemon=True).start()

    def _create_row(self, index: int, commit: GitHubCommit, processed_status: Dict[str, bool]):
        """Create a row with a message checkbox at the front and text label after it."""
        try:
            row_frame = ctk.CTkFrame(self.commit_listbox, fg_color="transparent")
            row_frame.grid(row=index, column=0, sticky="ew", padx=0)
            row_frame.grid_columnconfigure(1, weight=1)  # Text label stretches

            def _mk_msg_cb(c=commit):
                return lambda: self._on_message_row_toggle(c)

            msg_cb = ctk.CTkCheckBox(
                row_frame,
                text="M",
                width=24,
                font=self._row_font,
                command=_mk_msg_cb(commit)
            )
            msg_cb.grid(row=0, column=0, padx=(6, 6), pady=2, sticky="w")

            display_text = self._format_commit_display_with_status(commit, processed_status)
            text_label = ctk.CTkLabel(
                row_frame,
                text=display_text,
                anchor="w",
                justify="left",
                font=self._row_font
            )
            text_label.grid(row=0, column=1, sticky="ew")

            try:
                self._index_to_commit[index] = commit
                self._text_to_commit[display_text] = commit
            except Exception:
                pass

            def _on_label_click(_event=None, c=commit):
                self._update_preview(c)
            text_label.bind("<Button-1>", _on_label_click)

            if processed_status.get('message'):
                msg_cb.select()

            self.commit_message_checkboxes[commit.sha] = msg_cb
        except Exception as e:
            self.logger.error(f"Error creating commit row: {e}")

    def _attach_row_checkboxes(self, processed_commits: Dict[str, Dict[str, bool]]):
        """Deprecated helper kept for compatibility; now uses _create_row per item."""
        self.commit_message_checkboxes.clear()
        for i, commit in enumerate(self.filtered_commits):
            self._create_row(i, commit, processed_commits.get(commit.sha, {'message': False}))

    def _on_message_row_toggle(self, commit: GitHubCommit):
        """Handle per-row message checkbox toggle with non-blocking DB update."""
        if self.db_busy:
            cb = self.commit_message_checkboxes.get(commit.sha)
            if cb:
                cb.toggle()
            return

        msg_cb = self.commit_message_checkboxes.get(commit.sha)
        if not msg_cb:
            return

        message_selected = msg_cb.get()
        self._set_busy(True, "Updating selection...")

        def update_db():
            try:
                if message_selected:
                    self.database.mark_commit_processed(self.repository, commit.sha, "message")
                else:
                    self.database.mark_commit_unprocessed(self.repository, commit.sha, "message")
                try:
                    self._processed_cache.setdefault(commit.sha, {})["message"] = message_selected
                except Exception:
                    pass

                if message_selected:
                    if commit not in self.selected_commits:
                        self.selected_commits.append(commit)
                else:
                    if commit in self.selected_commits:
                        self.selected_commits.remove(commit)

                self.after(0, lambda: self.on_commits_selected(self.selected_commits))
            except Exception as e:
                self.logger.error(f"Error updating message selection: {e}")
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=update_db, daemon=True).start()


    def _set_busy(self, busy: bool, text: str = "Working..."):
        """Toggle busy UI and disable controls during DB operations."""
        try:
            self.db_busy = busy
            if busy:
                if self.select_all_message_cb:
                    self.select_all_message_cb.configure(state="disabled")
                if self.refresh_button:
                    self.refresh_button.configure(state="disabled")
                self.busy_label.configure(text=text)
                self.busy_label.grid()
                self.busy_progress.grid()
                self.busy_progress.start()
            else:
                if self.select_all_message_cb:
                    self.select_all_message_cb.configure(state="normal")
                if self.refresh_button:
                    self.refresh_button.configure(state="normal")
                self.busy_progress.stop()
                self.busy_label.grid_remove()
                self.busy_progress.grid_remove()
            # Notify parent/main window about busy state (for global banner)
            self._notify_busy(busy, text)
        except Exception as e:
            self.logger.error(f"Error toggling busy state: {e}")

    def _notify_busy(self, busy: bool, text: str = "Working..."):
        """Notify parent window of busy state to show/hide a global banner."""
        try:
            if hasattr(self, "on_busy_change") and self.on_busy_change:
                # Ensure call on UI thread
                self.after(0, lambda b=busy, t=text: self.on_busy_change(b, t))
        except Exception:
            pass

    def _update_display_status(self, processed_commits: Dict[str, Dict[str, bool]]):
        """Update the display with current processing status."""
        # Clear and repopulate the list with updated status
        self.commit_listbox.delete(0, "end")

        for i, commit in enumerate(self.filtered_commits):
            status = processed_commits.get(commit.sha, {'message': False})
            self._create_row(i, commit, status)
