#!/usr/bin/env python3
"""
DevBlogger - Commit Browser Component
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import customtkinter as ctk
from CTkListbox import CTkListbox
from CTkMessagebox import CTkMessagebox

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
        on_commits_selected: Callable[[List[GitHubCommit]], None]
    ):
        """Initialize commit browser."""
        super().__init__(parent)

        self.github_client = github_client
        self.repository = repository
        self.database = database
        self.on_commits_selected = on_commits_selected
        self.logger = logging.getLogger(__name__)

        # State
        self.all_commits: List[GitHubCommit] = []
        self.filtered_commits: List[GitHubCommit] = []
        self.selected_commits: List[GitHubCommit] = []
        self.commit_message_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.commit_comments_checkboxes: Dict[str, ctk.CTkCheckBox] = {}

        # UI components
        self.commit_listbox: Optional[CTkListbox] = None
        self.preview_text: Optional[ctk.CTkTextbox] = None

        # Setup UI
        self._setup_ui()
        self._load_commits()

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
        refresh_button = ctk.CTkButton(
            right_controls,
            text="Refresh",
            command=self._load_commits,
            width=80
        )
        refresh_button.grid(row=0, column=2)

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
        select_all_message_cb = ctk.CTkCheckBox(
            list_header,
            text="Process Messages",
            variable=self.select_all_message_var,
            command=self._toggle_select_all_messages
        )
        select_all_message_cb.grid(row=0, column=0)

        self.select_all_comments_var = ctk.BooleanVar()
        select_all_comments_cb = ctk.CTkCheckBox(
            list_header,
            text="Process Comments",
            variable=self.select_all_comments_var,
            command=self._toggle_select_all_comments
        )
        select_all_comments_cb.grid(row=0, column=1, padx=(10, 0))

        # Commit count label
        self.count_label = ctk.CTkLabel(
            list_header,
            text="0 commits",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.count_label.grid(row=0, column=2, padx=(20, 0))

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

        self.preview_text = ctk.CTkTextbox(
            preview_container,
            wrap="word",
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")

    def _load_commits(self):
        """Load commits from GitHub."""
        def load_commits_thread():
            try:
                self.logger.info(f"Loading commits for {self.repository}")

                # Show loading state
                self.after(0, self._show_loading_state)

                # Get commits from GitHub
                owner, repo = self.repository.split('/')
                commits = self.github_client.get_repository_commits(
                    owner=owner,
                    repo=repo,
                    per_page=200  # Load more commits for filtering
                )

                # Store commits
                self.all_commits = commits
                self.logger.info(f"Loaded {len(commits)} commits")

                # Apply filters
                self.after(0, self._apply_filters)

            except Exception as e:
                self.logger.error(f"Error loading commits: {e}")
                self.after(0, lambda: self._show_error(f"Failed to load commits: {str(e)}"))

        threading.Thread(target=load_commits_thread, daemon=True).start()

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
        """Update the commit list display."""
        # Clear existing items
        self.commit_listbox.delete(0, "end")
        self.commit_message_checkboxes.clear()
        self.commit_comments_checkboxes.clear()

        if not self.filtered_commits:
            self.commit_listbox.insert(0, "No commits found")
            self.count_label.configure(text="0 commits")
            return

        # Add commits to list
        for i, commit in enumerate(self.filtered_commits):
            # Create display text
            display_text = self._format_commit_display(commit)

            # Add to listbox
            self.commit_listbox.insert(i, display_text)

            # Create frame for checkboxes
            checkbox_frame = ctk.CTkFrame(self.commit_listbox, fg_color="transparent")
            checkbox_frame.grid(row=i, column=1, sticky="w", padx=(10, 0))

            # Message checkbox
            message_cb = ctk.CTkCheckBox(
                checkbox_frame,
                text="",
                width=20,
                command=lambda c=commit: self._on_message_checkbox_changed(c)
            )
            message_cb.grid(row=0, column=0, padx=(0, 5))
            self.commit_message_checkboxes[commit.sha] = message_cb

            # Comments checkbox
            comments_cb = ctk.CTkCheckBox(
                checkbox_frame,
                text="",
                width=20,
                command=lambda c=commit: self._on_comments_checkbox_changed(c)
            )
            comments_cb.grid(row=0, column=1)
            self.commit_comments_checkboxes[commit.sha] = comments_cb

            # Check if commit was previously processed for messages
            if self.database.is_commit_processed(self.repository, commit.sha, "message"):
                message_cb.select()

            # Check if commit was previously processed for comments
            if self.database.is_commit_processed(self.repository, commit.sha, "comments"):
                comments_cb.select()

        # Update count
        self.count_label.configure(text=f"{len(self.filtered_commits)} commits")

        # Clear preview if no commits
        if self.filtered_commits:
            self._update_preview(self.filtered_commits[0])

    def _format_commit_display(self, commit: GitHubCommit) -> str:
        """Format commit for display in list."""
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

        # Check if processed
        processed = self.database.is_commit_processed(self.repository, commit.sha)
        status = "✓" if processed else " "

        return f"{status} {short_sha} | {author_name} | {date_str} | {message}"

    def _on_commit_selected(self, selection):
        """Handle commit selection in listbox."""
        if not selection or not self.filtered_commits:
            return

        # Get selected commit
        selected_index = self.commit_listbox.curselection()
        if selected_index:
            commit = self.filtered_commits[selected_index[0]]
            self._update_preview(commit)

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

    def _on_commit_checkbox_changed(self, commit: GitHubCommit):
        """Handle commit checkbox change."""
        checkbox = self.commit_checkboxes.get(commit.sha)
        if not checkbox:
            return

        is_selected = checkbox.get()

        if is_selected:
            if commit not in self.selected_commits:
                self.selected_commits.append(commit)
        else:
            if commit in self.selected_commits:
                self.selected_commits.remove(commit)

        # Notify parent
        self.on_commits_selected(self.selected_commits)

    def _toggle_select_all(self):
        """Toggle select all commits."""
        select_all = self.select_all_var.get()

        # Update all checkboxes
        for commit in self.filtered_commits:
            checkbox = self.commit_checkboxes.get(commit.sha)
            if checkbox:
                if select_all:
                    checkbox.select()
                    if commit not in self.selected_commits:
                        self.selected_commits.append(commit)
                else:
                    checkbox.deselect()
                    if commit in self.selected_commits:
                        self.selected_commits.remove(commit)

        # Notify parent
        self.on_commits_selected(self.selected_commits)

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
        self.select_all_var.set(False)

        # Update checkboxes
        for checkbox in self.commit_checkboxes.values():
            checkbox.deselect()

        self.on_commits_selected(self.selected_commits)

    def _on_message_checkbox_changed(self, commit: GitHubCommit):
        """Handle message checkbox change."""
        message_cb = self.commit_message_checkboxes.get(commit.sha)
        comments_cb = self.commit_comments_checkboxes.get(commit.sha)

        if not message_cb or not comments_cb:
            return

        message_selected = message_cb.get()
        comments_selected = comments_cb.get()

        # Mark as processed in database
        if message_selected:
            self.database.mark_commit_processed(self.repository, commit.sha, "message")
        else:
            self.database.mark_commit_unprocessed(self.repository, commit.sha, "message")

        # Update commit selection
        if message_selected or comments_selected:
            if commit not in self.selected_commits:
                self.selected_commits.append(commit)
        else:
            if commit in self.selected_commits:
                self.selected_commits.remove(commit)

        self.on_commits_selected(self.selected_commits)

    def _on_comments_checkbox_changed(self, commit: GitHubCommit):
        """Handle comments checkbox change."""
        message_cb = self.commit_message_checkboxes.get(commit.sha)
        comments_cb = self.commit_comments_checkboxes.get(commit.sha)

        if not message_cb or not comments_cb:
            return

        message_selected = message_cb.get()
        comments_selected = comments_cb.get()

        # Mark as processed in database
        if comments_selected:
            self.database.mark_commit_processed(self.repository, commit.sha, "comments")
        else:
            self.database.mark_commit_unprocessed(self.repository, commit.sha, "comments")

        # Update commit selection
        if message_selected or comments_selected:
            if commit not in self.selected_commits:
                self.selected_commits.append(commit)
        else:
            if commit in self.selected_commits:
                self.selected_commits.remove(commit)

        self.on_commits_selected(self.selected_commits)

    def _toggle_select_all_messages(self):
        """Toggle select all message checkboxes."""
        select_all = self.select_all_message_var.get()

        for commit in self.filtered_commits:
            message_cb = self.commit_message_checkboxes.get(commit.sha)
            if message_cb:
                if select_all:
                    message_cb.select()
                    self.database.mark_commit_processed(self.repository, commit.sha, "message")
                else:
                    message_cb.deselect()
                    self.database.mark_commit_unprocessed(self.repository, commit.sha, "message")

        # Update selection
        self._update_selection_from_checkboxes()

    def _toggle_select_all_comments(self):
        """Toggle select all comments checkboxes."""
        select_all = self.select_all_comments_var.get()

        for commit in self.filtered_commits:
            comments_cb = self.commit_comments_checkboxes.get(commit.sha)
            if comments_cb:
                if select_all:
                    comments_cb.select()
                    self.database.mark_commit_processed(self.repository, commit.sha, "comments")
                else:
                    comments_cb.deselect()
                    self.database.mark_commit_unprocessed(self.repository, commit.sha, "comments")

        # Update selection
        self._update_selection_from_checkboxes()

    def _update_selection_from_checkboxes(self):
        """Update selected commits based on checkbox states."""
        new_selection = []

        for commit in self.filtered_commits:
            message_cb = self.commit_message_checkboxes.get(commit.sha)
            comments_cb = self.commit_comments_checkboxes.get(commit.sha)

            if message_cb and comments_cb:
                message_selected = message_cb.get()
                comments_selected = comments_cb.get()

                if message_selected or comments_selected:
                    new_selection.append(commit)

        self.selected_commits = new_selection
        self.on_commits_selected(self.selected_commits)
