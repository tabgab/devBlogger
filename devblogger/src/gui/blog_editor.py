#!/usr/bin/env python3
"""
DevBlogger - Blog Editor Component
"""

import logging
import threading
from datetime import datetime
from typing import List, Optional, Callable
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from ..ai.manager import DevBloggerAIProviderManager
from ..github.models import GitHubCommit
from ..config.settings import Settings


class BlogEditor(ctk.CTkFrame):
    """Blog editor for generating and editing blog entries."""

    def __init__(
        self,
        parent,
        ai_manager: DevBloggerAIProviderManager,
        settings: Settings,
        commits: List[GitHubCommit],
        repository: str
    ):
        """Initialize blog editor."""
        super().__init__(parent)

        self.ai_manager = ai_manager
        self.settings = settings
        self.commits = commits
        self.repository = repository
        self.logger = logging.getLogger(__name__)

        # UI state
        self.generation_in_progress = False
        self.current_blog_content = ""
        self.selected_provider = None

        # Setup UI
        self._setup_ui()
        self._load_initial_content()

    def _setup_ui(self):
        """Setup user interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Blog Entry Generation",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=(0, 20))

        # Commit count
        self.commit_count_label = ctk.CTkLabel(
            header_frame,
            text=f"{len(self.commits)} commits selected",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.commit_count_label.grid(row=0, column=1)

        # Main content
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        # Controls
        self._create_controls(content_frame)

        # Editor area
        self._create_editor_area(content_frame)

    def _create_controls(self, parent):
        """Create control widgets."""
        # Controls frame
        controls_frame = ctk.CTkFrame(parent)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(1, weight=1)

        # AI Provider selection
        provider_label = ctk.CTkLabel(controls_frame, text="AI Provider:")
        provider_label.grid(row=0, column=0, padx=(0, 10))

        self.provider_var = ctk.StringVar()
        self.provider_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.provider_var,
            values=["Loading..."],
            command=self._on_provider_changed,
            width=150
        )
        self.provider_dropdown.grid(row=0, column=1, padx=(0, 10))

        # Prompt configuration
        prompt_label = ctk.CTkLabel(controls_frame, text="Prompt:")
        prompt_label.grid(row=0, column=2, padx=(0, 10))

        self.prompt_text = ctk.CTkTextbox(
            controls_frame,
            height=60,
            wrap="word",
            font=ctk.CTkFont(size=11)
        )
        self.prompt_text.grid(row=0, column=3, padx=(0, 10), sticky="ew")

        # Load default prompt
        default_prompt = self.settings.get_default_prompt()
        if default_prompt:
            self.prompt_text.insert("1.0", default_prompt)

        # Control buttons
        buttons_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))

        # Generate button
        self.generate_button = ctk.CTkButton(
            buttons_frame,
            text="Generate Blog Entry",
            command=self._generate_blog_entry,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        )
        self.generate_button.grid(row=0, column=0, padx=(0, 10))

        # Save button
        self.save_button = ctk.CTkButton(
            buttons_frame,
            text="Save to File",
            command=self._save_blog_entry,
            fg_color="blue",
            hover_color="darkblue",
            height=40,
            state="disabled"
        )
        self.save_button.grid(row=0, column=1, padx=(0, 10))

        # Reset button
        self.reset_button = ctk.CTkButton(
            buttons_frame,
            text="Reset",
            command=self._reset_editor,
            fg_color="orange",
            hover_color="darkorange",
            height=40
        )
        self.reset_button.grid(row=0, column=2)

    def _create_editor_area(self, parent):
        """Create blog editor area."""
        # Editor frame
        editor_frame = ctk.CTkFrame(parent)
        editor_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(0, weight=1)

        # Editor header
        editor_header = ctk.CTkFrame(editor_frame)
        editor_header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        editor_title = ctk.CTkLabel(
            editor_header,
            text="Blog Entry Editor",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        editor_title.grid(row=0, column=0)

        # Generation info
        self.generation_info = ctk.CTkLabel(
            editor_header,
            text="Ready to generate blog entry",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.generation_info.grid(row=0, column=1, padx=(20, 0))

        # Text editor
        editor_container = ctk.CTkFrame(editor_frame)
        editor_container.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        editor_container.grid_columnconfigure(0, weight=1)
        editor_container.grid_rowconfigure(0, weight=1)

        self.blog_editor = ctk.CTkTextbox(
            editor_container,
            wrap="word",
            font=ctk.CTkFont(size=12),
            undo=True
        )
        self.blog_editor.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ctk.CTkScrollbar(editor_container, command=self.blog_editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.blog_editor.configure(yscrollcommand=scrollbar.set)

    def _load_initial_content(self):
        """Load initial content and setup providers."""
        try:
            # Load available providers
            providers = list(self.ai_manager.get_all_providers().keys())
            self.provider_dropdown.configure(values=providers)

            # Set active provider
            active_provider = self.ai_manager.get_active_provider()
            if active_provider:
                self.provider_var.set(active_provider.name)
                self.selected_provider = active_provider.name

            # Load default prompt if available
            default_prompt = self.settings.get_default_prompt()
            if default_prompt:
                self.prompt_text.delete("1.0", "end")
                self.prompt_text.insert("1.0", default_prompt)

        except Exception as e:
            self.logger.error(f"Error loading initial content: {e}")

    def _on_provider_changed(self, provider_name: str):
        """Handle provider selection change."""
        self.selected_provider = provider_name
        self.logger.info(f"Selected AI provider: {provider_name}")

    def _generate_blog_entry(self):
        """Generate blog entry from selected commits."""
        if self.generation_in_progress:
            return

        if not self.commits:
            CTkMessagebox(
                title="No Commits",
                message="No commits selected for blog generation.",
                icon="warning"
            )
            return

        if not self.selected_provider:
            CTkMessagebox(
                title="No Provider",
                message="Please select an AI provider.",
                icon="warning"
            )
            return

        # Get prompt
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            CTkMessagebox(
                title="No Prompt",
                message="Please enter a prompt for blog generation.",
                icon="warning"
            )
            return

        # Start generation
        self.generation_in_progress = True
        self._update_ui_state()

        def generate_thread():
            try:
                # Prepare commit data for AI
                commit_data = self._prepare_commit_data()

                # Generate blog entry
                response = self.ai_manager.generate_with_active(
                    prompt=f"{prompt}\n\nCommit Data:\n{commit_data}",
                    max_tokens=2000,
                    temperature=0.7
                )

                # Update editor with generated content
                self.after(0, lambda: self._handle_generation_success(response.text))

            except Exception as e:
                self.logger.error(f"Error generating blog entry: {e}")
                self.after(0, lambda: self._handle_generation_error(str(e)))
            finally:
                self.generation_in_progress = False
                self.after(0, self._update_ui_state)

        threading.Thread(target=generate_thread, daemon=True).start()

    def _prepare_commit_data(self) -> str:
        """Prepare commit data for AI processing."""
        commit_summaries = []

        for commit in self.commits:
            summary = f"""
Commit: {commit.sha}
Author: {commit.author.name or commit.author.login or 'Unknown'}
Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S') if commit.date else 'Unknown'}
Message: {commit.message}

"""
            if commit.files:
                summary += "Files Changed:\n"
                for file_info in commit.files[:5]:  # Limit to first 5 files
                    filename = file_info.get('filename', 'Unknown')
                    status = file_info.get('status', 'Unknown')
                    additions = file_info.get('additions', 0)
                    deletions = file_info.get('deletions', 0)

                    summary += f"  {status} {filename}"
                    if additions:
                        summary += f" (+{additions})"
                    if deletions:
                        summary += f" (-{deletions})"
                    summary += "\n"

                if len(commit.files) > 5:
                    summary += f"  ... and {len(commit.files) - 5} more files\n"

            commit_summaries.append(summary)

        return "\n".join(commit_summaries)

    def _handle_generation_success(self, content: str):
        """Handle successful blog generation."""
        # Update editor
        self.blog_editor.delete("1.0", "end")
        self.blog_editor.insert("1.0", content)

        # Update info
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.generation_info.configure(
            text=f"Generated on {timestamp} using {self.selected_provider}"
        )

        # Enable save button
        self.save_button.configure(state="normal")

        # Store content
        self.current_blog_content = content

        CTkMessagebox(
            title="Generation Complete",
            message="Blog entry generated successfully!",
            icon="check"
        )

    def _handle_generation_error(self, error_message: str):
        """Handle blog generation error."""
        CTkMessagebox(
            title="Generation Error",
            message=f"Failed to generate blog entry: {error_message}",
            icon="cancel"
        )

        self.generation_info.configure(
            text=f"Generation failed: {error_message}"
        )

    def _update_ui_state(self):
        """Update UI based on generation state."""
        if self.generation_in_progress:
            self.generate_button.configure(
                state="disabled",
                text="Generating...",
                fg_color="gray"
            )
            self.generation_info.configure(text="Generating blog entry...")
        else:
            self.generate_button.configure(
                state="normal",
                text="Generate Blog Entry",
                fg_color="green"
            )

    def _save_blog_entry(self):
        """Save blog entry to file."""
        if not self.current_blog_content:
            CTkMessagebox(
                title="No Content",
                message="No blog content to save.",
                icon="warning"
            )
            return

        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            repo_name = self.repository.replace("/", "_")
            filename = f"{repo_name}_{timestamp}.md"

            # Get output directory
            output_dir = self.settings.get_generated_entries_dir()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Full path
            filepath = output_dir / filename

            # Prepare content with metadata
            metadata = f"""---
title: Development Blog Entry - {repo_name}
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
repository: {self.repository}
commits: {len(self.commits)}
generated_by: {self.selected_provider}
---

"""

            full_content = metadata + self.current_blog_content

            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)

            CTkMessagebox(
                title="File Saved",
                message=f"Blog entry saved to:\n{filepath}",
                icon="check"
            )

            self.logger.info(f"Blog entry saved to: {filepath}")

        except Exception as e:
            self.logger.error(f"Error saving blog entry: {e}")
            CTkMessagebox(
                title="Save Error",
                message=f"Failed to save blog entry: {str(e)}",
                icon="cancel"
            )

    def _reset_editor(self):
        """Reset editor to initial state."""
        # Clear editor
        self.blog_editor.delete("1.0", "end")
        self.current_blog_content = ""

        # Reset info
        self.generation_info.configure(text="Ready to generate blog entry")

        # Disable save button
        self.save_button.configure(state="disabled")

        # Clear prompt if it was modified
        default_prompt = self.settings.get_default_prompt()
        if default_prompt:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", default_prompt)

        CTkMessagebox(
            title="Editor Reset",
            message="Blog editor has been reset.",
            icon="info"
        )

    def get_blog_content(self) -> str:
        """Get current blog content."""
        return self.current_blog_content

    def set_blog_content(self, content: str):
        """Set blog content."""
        self.current_blog_content = content
        self.blog_editor.delete("1.0", "end")
        self.blog_editor.insert("1.0", content)
        self.save_button.configure(state="normal")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.generation_info.configure(
            text=f"Content loaded on {timestamp}"
        )

    def regenerate_with_different_provider(self, provider_name: str):
        """Regenerate blog entry with a different AI provider."""
        if not self.commits:
            CTkMessagebox(
                title="No Commits",
                message="No commits available for regeneration.",
                icon="warning"
            )
            return

        # Get current prompt
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            CTkMessagebox(
                title="No Prompt",
                message="Please enter a prompt for blog generation.",
                icon="warning"
            )
            return

        # Check if provider is available
        provider = self.ai_manager.get_provider(provider_name)
        if not provider or not provider.is_configured():
            CTkMessagebox(
                title="Provider Not Available",
                message=f"Provider {provider_name} is not configured.",
                icon="warning"
            )
            return

        # Temporarily switch provider
        original_provider = self.selected_provider
        self.selected_provider = provider_name

        try:
            # Start regeneration
            self.generation_in_progress = True
            self._update_ui_state()

            def regenerate_thread():
                try:
                    # Prepare commit data for AI
                    commit_data = self._prepare_commit_data()

                    # Generate blog entry with new provider
                    response = self.ai_manager.generate_with_active(
                        prompt=f"{prompt}\n\nCommit Data:\n{commit_data}",
                        max_tokens=2000,
                        temperature=0.7
                    )

                    # Update editor with regenerated content
                    self.after(0, lambda: self._handle_regeneration_success(response.text, provider_name))

                except Exception as e:
                    self.logger.error(f"Error regenerating blog entry: {e}")
                    self.after(0, lambda: self._handle_generation_error(str(e)))
                finally:
                    self.generation_in_progress = False
                    self.after(0, self._update_ui_state)

            threading.Thread(target=regenerate_thread, daemon=True).start()

        except Exception as e:
            self.selected_provider = original_provider
            self.logger.error(f"Error during regeneration: {e}")
            CTkMessagebox(
                title="Regeneration Error",
                message=f"Failed to regenerate blog entry: {str(e)}",
                icon="cancel"
            )

    def _handle_regeneration_success(self, content: str, provider_name: str):
        """Handle successful regeneration."""
        # Update editor
        self.blog_editor.delete("1.0", "end")
        self.blog_editor.insert("1.0", content)

        # Update info
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.generation_info.configure(
            text=f"Regenerated on {timestamp} using {provider_name}"
        )

        # Enable save button
        self.save_button.configure(state="normal")

        # Store content
        self.current_blog_content = content

        CTkMessagebox(
            title="Regeneration Complete",
            message=f"Blog entry regenerated successfully using {provider_name}!",
            icon="check"
        )
