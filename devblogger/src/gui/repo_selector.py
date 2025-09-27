#!/usr/bin/env python3
"""
DevBlogger - Repository Selector Component
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Callable
import customtkinter as ctk

from ..github.client import GitHubClient
from ..github.models import GitHubRepository


class RepositorySelector(ctk.CTkFrame):
    """Repository selector component."""

    def __init__(self, master, github_client: GitHubClient, on_repository_selected: Callable[[GitHubRepository], None]):
        """Initialize repository selector."""
        super().__init__(master)
        self.github_client = github_client
        self.on_repository_selected = on_repository_selected
        self.logger = logging.getLogger(__name__)

        # State
        self.repositories: List[GitHubRepository] = []
        self.selected_repository: Optional[GitHubRepository] = None

        # UI components
        self.search_var = tk.StringVar()
        self.repo_var = tk.StringVar()

        self._setup_ui()
        self._load_repositories()

    def _setup_ui(self):
        """Setup the user interface."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Select Repository",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(20, 10))

        # Search frame
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.pack(side="left", padx=(0, 10))

        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Type to search repositories..."
        )
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind('<KeyRelease>', self._on_search)

        # Repository list
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Listbox for repositories
        self.repo_listbox = tk.Listbox(
            list_frame,
            selectmode="single",
            yscrollcommand=scrollbar.set,
            font=("Arial", 11),
            bg="white",
            selectbackground="#4A90E2",
            selectforeground="white"
        )
        self.repo_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.repo_listbox.yview)

        # Bind selection event
        self.repo_listbox.bind('<<ListboxSelect>>', self._on_repository_select)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Refresh button
        refresh_button = ctk.CTkButton(
            buttons_frame,
            text="🔄 Refresh",
            command=self._load_repositories,
            width=100
        )
        refresh_button.pack(side="left", padx=(0, 10))

        # Select button
        self.select_button = ctk.CTkButton(
            buttons_frame,
            text="✅ Select",
            command=self._select_repository,
            width=100,
            state="disabled"
        )
        self.select_button.pack(side="right")

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Loading repositories...",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 10))

    def _load_repositories(self):
        """Load repositories from GitHub."""
        try:
            self.status_label.configure(text="Loading repositories...")
            self.repo_listbox.delete(0, tk.END)
            self.repositories.clear()

            # Get repositories from GitHub
            repos_data = self.github_client.get_user_repositories()

            if not repos_data:
                self.status_label.configure(text="No repositories found")
                return

            # Convert to repository objects
            for repo_data in repos_data:
                try:
                    repo = GitHubRepository.from_dict(repo_data)
                    self.repositories.append(repo)
                except Exception as e:
                    self.logger.warning(f"Error creating repository object: {e}")

            # Sort repositories by name
            self.repositories.sort(key=lambda r: r.full_name.lower())

            # Populate listbox
            for repo in self.repositories:
                display_name = f"{repo.full_name}"
                if repo.description:
                    display_name += f" - {repo.description[:50]}..."
                self.repo_listbox.insert(tk.END, display_name)

            self.status_label.configure(text=f"Found {len(self.repositories)} repositories")

        except Exception as e:
            self.logger.error(f"Error loading repositories: {e}")
            self.status_label.configure(text="Error loading repositories")
            messagebox.showerror("Error", f"Failed to load repositories: {str(e)}")

    def _on_search(self, event):
        """Handle search input."""
        search_term = self.search_var.get().lower()

        if not search_term:
            # Show all repositories
            self._populate_listbox()
            return

        # Filter repositories
        filtered_repos = [
            repo for repo in self.repositories
            if search_term in repo.full_name.lower() or
               (repo.description and search_term in repo.description.lower())
        ]

        # Update listbox
        self.repo_listbox.delete(0, tk.END)
        for repo in filtered_repos:
            display_name = f"{repo.full_name}"
            if repo.description:
                display_name += f" - {repo.description[:50]}..."
            self.repo_listbox.insert(tk.END, display_name)

    def _populate_listbox(self):
        """Populate the listbox with all repositories."""
        self.repo_listbox.delete(0, tk.END)
        for repo in self.repositories:
            display_name = f"{repo.full_name}"
            if repo.description:
                display_name += f" - {repo.description[:50]}..."
            self.repo_listbox.insert(tk.END, display_name)

    def _on_repository_select(self, event):
        """Handle repository selection."""
        selection = self.repo_listbox.curselection()
        if not selection:
            self.select_button.configure(state="disabled")
            return

        index = selection[0]
        if 0 <= index < len(self.repositories):
            self.selected_repository = self.repositories[index]
            self.select_button.configure(state="normal")
        else:
            self.select_button.configure(state="disabled")

    def _select_repository(self):
        """Select the currently selected repository."""
        if not self.selected_repository:
            return

        try:
            self.on_repository_selected(self.selected_repository)
            self.logger.info(f"Selected repository: {self.selected_repository.full_name}")
        except Exception as e:
            self.logger.error(f"Error selecting repository: {e}")
            messagebox.showerror("Error", f"Failed to select repository: {str(e)}")

    def get_selected_repository(self) -> Optional[GitHubRepository]:
        """Get the currently selected repository."""
        return self.selected_repository

    def refresh(self):
        """Refresh the repository list."""
        self._load_repositories()

    def clear_selection(self):
        """Clear the current selection."""
        self.selected_repository = None
        self.repo_listbox.selection_clear(0, tk.END)
        self.select_button.configure(state="disabled")


class RepositorySelectorDialog(ctk.CTkToplevel):
    """Dialog for repository selection."""

    def __init__(self, parent, github_client: GitHubClient, on_repository_selected: Callable[[GitHubRepository], None]):
        """Initialize repository selector dialog."""
        super().__init__(parent)
        self.github_client = github_client
        self.on_repository_selected = on_repository_selected

        # Dialog configuration
        self.title("Select Repository")
        self.geometry("600x500")
        self.resizable(True, True)

        # Make dialog modal (non-grabbing to keep main window responsive)
        self.transient(parent)
        # self.grab_set()  # removed to avoid modal grab causing click issues on macOS

        # Center dialog
        self._center_dialog()

        # Create repository selector
        self.repo_selector = RepositorySelector(
            self,
            github_client,
            self._on_repository_selected
        )
        self.repo_selector.pack(fill="both", expand=True, padx=10, pady=10)

        # Focus on dialog
        self.focus_force()

    def _center_dialog(self):
        """Center the dialog on the screen."""
        self.update_idletasks()

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate position
        x = (screen_width - 600) // 2
        y = (screen_height - 500) // 2

        self.geometry(f"600x500+{x}+{y}")

    def _on_repository_selected(self, repository: GitHubRepository):
        """Handle repository selection."""
        self.on_repository_selected(repository)
        self.destroy()


def show_repository_selector(parent, github_client: GitHubClient, on_repository_selected: Callable[[GitHubRepository], None]):
    """Show repository selector dialog."""
    dialog = RepositorySelectorDialog(parent, github_client, on_repository_selected)
    parent.wait_window(dialog)
