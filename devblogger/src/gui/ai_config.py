#!/usr/bin/env python3
"""
DevBlogger - AI Configuration Panel
"""

import logging
from typing import Dict, Any, Optional
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from ..ai.manager import DevBloggerAIProviderManager
from ..config.settings import Settings


class AIConfigurationPanel(ctk.CTkFrame):
    """AI configuration panel for managing AI providers."""

    def __init__(self, parent, ai_manager: DevBloggerAIProviderManager, settings: Settings):
        """Initialize AI configuration panel."""
        super().__init__(parent)

        self.ai_manager = ai_manager
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # UI state
        self.current_provider: Optional[str] = None
        self.test_in_progress: bool = False

        # Setup UI
        self._setup_ui()
        self._load_providers()

    def _setup_ui(self):
        """Setup user interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="AI Provider Configuration",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=(0, 20))

        # Status summary
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="Loading provider status...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.grid(row=0, column=1)

        # Main content
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Create tabbed interface for providers
        self._create_provider_tabs(content_frame)

    def _create_provider_tabs(self, parent):
        """Create tabbed interface for different providers."""
        # Tab view
        self.tab_view = ctk.CTkTabview(parent)
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        self.tab_view.grid_columnconfigure(0, weight=1)
        self.tab_view.grid_rowconfigure(0, weight=1)

        # Create tabs for each provider
        self._create_chatgpt_tab()
        self._create_gemini_tab()
        self._create_ollama_tab()

        # Common controls
        self._create_common_controls(parent)

    def _create_chatgpt_tab(self):
        """Create ChatGPT configuration tab."""
        chatgpt_tab = self.tab_view.add("ChatGPT")

        # ChatGPT configuration content
        content = ctk.CTkFrame(chatgpt_tab)
        content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)

        # API Key
        api_key_label = ctk.CTkLabel(content, text="API Key:")
        api_key_label.grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.chatgpt_api_key = ctk.CTkEntry(
            content,
            placeholder_text="sk-...",
            show="•",
            width=300
        )
        self.chatgpt_api_key.grid(row=0, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.chatgpt_model = ctk.CTkOptionMenu(
            content,
            values=["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"],
            width=200
        )
        self.chatgpt_model.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=2, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.chatgpt_max_tokens = ctk.CTkEntry(content, width=100)
        self.chatgpt_max_tokens.insert(0, "2000")
        self.chatgpt_max_tokens.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=3, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.chatgpt_temperature = ctk.CTkEntry(content, width=100)
        self.chatgpt_temperature.insert(0, "0.7")
        self.chatgpt_temperature.grid(row=3, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Test button
        test_button = ctk.CTkButton(
            content,
            text="Test Connection",
            command=self._test_chatgpt,
            width=120
        )
        test_button.grid(row=4, column=0, padx=(0, 10), pady=(20, 0))

        # Save button
        save_button = ctk.CTkButton(
            content,
            text="Save Configuration",
            command=self._save_chatgpt_config,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        )
        save_button.grid(row=4, column=1, padx=(0, 10), pady=(20, 0))

        # Status label
        self.chatgpt_status = ctk.CTkLabel(
            content,
            text="Not configured",
            font=ctk.CTkFont(size=11),
            text_color="red"
        )
        self.chatgpt_status.grid(row=5, column=0, columnspan=2, pady=(10, 0))

    def _create_gemini_tab(self):
        """Create Google Gemini configuration tab."""
        gemini_tab = self.tab_view.add("Gemini")

        # Gemini configuration content
        content = ctk.CTkFrame(gemini_tab)
        content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)

        # API Key
        api_key_label = ctk.CTkLabel(content, text="API Key:")
        api_key_label.grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.gemini_api_key = ctk.CTkEntry(
            content,
            placeholder_text="AIza...",
            show="•",
            width=300
        )
        self.gemini_api_key.grid(row=0, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.gemini_model = ctk.CTkOptionMenu(
            content,
            values=["gemini-pro", "gemini-pro-vision"],
            width=200
        )
        self.gemini_model.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=2, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.gemini_max_tokens = ctk.CTkEntry(content, width=100)
        self.gemini_max_tokens.insert(0, "2000")
        self.gemini_max_tokens.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=3, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.gemini_temperature = ctk.CTkEntry(content, width=100)
        self.gemini_temperature.insert(0, "0.7")
        self.gemini_temperature.grid(row=3, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Test button
        test_button = ctk.CTkButton(
            content,
            text="Test Connection",
            command=self._test_gemini,
            width=120
        )
        test_button.grid(row=4, column=0, padx=(0, 10), pady=(20, 0))

        # Save button
        save_button = ctk.CTkButton(
            content,
            text="Save Configuration",
            command=self._save_gemini_config,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        )
        save_button.grid(row=4, column=1, padx=(0, 10), pady=(20, 0))

        # Status label
        self.gemini_status = ctk.CTkLabel(
            content,
            text="Not configured",
            font=ctk.CTkFont(size=11),
            text_color="red"
        )
        self.gemini_status.grid(row=5, column=0, columnspan=2, pady=(10, 0))

    def _create_ollama_tab(self):
        """Create Ollama configuration tab."""
        ollama_tab = self.tab_view.add("Ollama")

        # Ollama configuration content
        content = ctk.CTkFrame(ollama_tab)
        content.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)

        # Base URL
        url_label = ctk.CTkLabel(content, text="Base URL:")
        url_label.grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.ollama_url = ctk.CTkEntry(
            content,
            placeholder_text="http://localhost:11434",
            width=300
        )
        self.ollama_url.insert(0, "http://localhost:11434")
        self.ollama_url.grid(row=0, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.ollama_model = ctk.CTkOptionMenu(
            content,
            values=["llama2", "codellama", "mistral", "Loading..."],
            width=200
        )
        self.ollama_model.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=2, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.ollama_max_tokens = ctk.CTkEntry(content, width=100)
        self.ollama_max_tokens.insert(0, "2000")
        self.ollama_max_tokens.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=3, column=0, padx=(0, 10), pady=(0, 5), sticky="w")

        self.ollama_temperature = ctk.CTkEntry(content, width=100)
        self.ollama_temperature.insert(0, "0.7")
        self.ollama_temperature.grid(row=3, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Test button
        test_button = ctk.CTkButton(
            content,
            text="Test Connection",
            command=self._test_ollama,
            width=120
        )
        test_button.grid(row=4, column=0, padx=(0, 10), pady=(20, 0))

        # Save button
        save_button = ctk.CTkButton(
            content,
            text="Save Configuration",
            command=self._save_ollama_config,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        )
        save_button.grid(row=4, column=1, padx=(0, 10), pady=(20, 0))

        # Status label
        self.ollama_status = ctk.CTkLabel(
            content,
            text="Not configured",
            font=ctk.CTkFont(size=11),
            text_color="red"
        )
        self.ollama_status.grid(row=5, column=0, columnspan=2, pady=(10, 0))

    def _create_common_controls(self, parent):
        """Create common controls for all providers."""
        # Common controls frame
        controls_frame = ctk.CTkFrame(parent)
        controls_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Active provider selection
        provider_label = ctk.CTkLabel(controls_frame, text="Active Provider:")
        provider_label.grid(row=0, column=0, padx=(0, 10))

        self.active_provider_var = ctk.StringVar()
        self.active_provider_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.active_provider_var,
            values=["Loading..."],
            command=self._on_active_provider_changed,
            width=150
        )
        self.active_provider_dropdown.grid(row=0, column=1, padx=(0, 10))

        # Refresh status button
        refresh_button = ctk.CTkButton(
            controls_frame,
            text="Refresh Status",
            command=self._refresh_status,
            width=120
        )
        refresh_button.grid(row=0, column=2, padx=(0, 10))

        # Test all providers button
        test_all_button = ctk.CTkButton(
            controls_frame,
            text="Test All",
            command=self._test_all_providers,
            width=100
        )
        test_all_button.grid(row=0, column=3)

    def _load_providers(self):
        """Load provider configurations and status."""
        try:
            # Load ChatGPT config
            chatgpt_config = self.settings.get_ai_provider_config("chatgpt")
            if chatgpt_config.get("api_key"):
                self.chatgpt_api_key.delete(0, "end")
                self.chatgpt_api_key.insert(0, chatgpt_config["api_key"])
                self.chatgpt_model.set(chatgpt_config.get("model", "gpt-4"))
                self.chatgpt_max_tokens.delete(0, "end")
                self.chatgpt_max_tokens.insert(0, str(chatgpt_config.get("max_tokens", 2000)))
                self.chatgpt_temperature.delete(0, "end")
                self.chatgpt_temperature.insert(0, str(chatgpt_config.get("temperature", 0.7)))

            # Load Gemini config
            gemini_config = self.settings.get_ai_provider_config("gemini")
            if gemini_config.get("api_key"):
                self.gemini_api_key.delete(0, "end")
                self.gemini_api_key.insert(0, gemini_config["api_key"])
                self.gemini_model.set(gemini_config.get("model", "gemini-pro"))
                self.gemini_max_tokens.delete(0, "end")
                self.gemini_max_tokens.insert(0, str(gemini_config.get("max_tokens", 2000)))
                self.gemini_temperature.delete(0, "end")
                self.gemini_temperature.insert(0, str(gemini_config.get("temperature", 0.7)))

            # Load Ollama config
            ollama_config = self.settings.get_ai_provider_config("ollama")
            if ollama_config.get("base_url"):
                self.ollama_url.delete(0, "end")
                self.ollama_url.insert(0, ollama_config["base_url"])
                self.ollama_model.set(ollama_config.get("model", "llama2"))
                self.ollama_max_tokens.delete(0, "end")
                self.ollama_max_tokens.insert(0, str(ollama_config.get("max_tokens", 2000)))
                self.ollama_temperature.delete(0, "end")
                self.ollama_temperature.insert(0, str(ollama_config.get("temperature", 0.7)))

            # Update status
            self._refresh_status()

        except Exception as e:
            self.logger.error(f"Error loading provider configs: {e}")

    def _refresh_status(self):
        """Refresh provider status information."""
        try:
            # Get status summary
            status = self.ai_manager.get_provider_status_summary()

            # Update status label
            configured = status["configured_providers"]
            working = status["working_providers"]
            total = status["total_providers"]

            self.status_label.configure(
                text=f"{configured}/{total} configured, {working} working"
            )

            # Update active provider dropdown
            providers = list(self.ai_manager.get_all_providers().keys())
            self.active_provider_dropdown.configure(values=providers)

            # Set current active provider
            active = self.ai_manager.get_active_provider()
            if active:
                self.active_provider_var.set(active.name)

            # Update individual provider status
            self._update_provider_status("chatgpt", self.chatgpt_status)
            self._update_provider_status("gemini", self.gemini_status)
            self._update_provider_status("ollama", self.ollama_status)

        except Exception as e:
            self.logger.error(f"Error refreshing status: {e}")

    def _update_provider_status(self, provider_name: str, status_label: ctk.CTkLabel):
        """Update status for a specific provider."""
        try:
            provider = self.ai_manager.get_provider(provider_name)
            if provider and provider.is_configured():
                if provider.test_connection():
                    status_label.configure(text="✓ Working", text_color="green")
                else:
                    status_label.configure(text="⚠ Configured but not working", text_color="orange")
            else:
                status_label.configure(text="✗ Not configured", text_color="red")
        except Exception:
            status_label.configure(text="✗ Error", text_color="red")

    def _test_chatgpt(self):
        """Test ChatGPT connection."""
        self._test_provider("chatgpt", self.chatgpt_status)

    def _test_gemini(self):
        """Test Gemini connection."""
        self._test_provider("gemini", self.gemini_status)

    def _test_ollama(self):
        """Test Ollama connection."""
        self._test_provider("ollama", self.ollama_status)

    def _test_provider(self, provider_name: str, status_label: ctk.CTkLabel):
        """Test a specific provider."""
        if self.test_in_progress:
            return

        self.test_in_progress = True
        status_label.configure(text="Testing...", text_color="orange")

        def test_thread():
            try:
                provider = self.ai_manager.get_provider(provider_name)
                if provider and provider.test_connection():
                    self.after(0, lambda: status_label.configure(text="✓ Working", text_color="green"))
                else:
                    self.after(0, lambda: status_label.configure(text="✗ Not working", text_color="red"))
            except Exception as e:
                self.logger.error(f"Error testing {provider_name}: {e}")
                self.after(0, lambda: status_label.configure(text="✗ Error", text_color="red"))
            finally:
                self.test_in_progress = False

        import threading
        threading.Thread(target=test_thread, daemon=True).start()

    def _save_chatgpt_config(self):
        """Save ChatGPT configuration."""
        self._save_provider_config("chatgpt", {
            "api_key": self.chatgpt_api_key.get(),
            "model": self.chatgpt_model.get(),
            "max_tokens": int(self.chatgpt_max_tokens.get()),
            "temperature": float(self.chatgpt_temperature.get())
        }, self.chatgpt_status)

    def _save_gemini_config(self):
        """Save Gemini configuration."""
        self._save_provider_config("gemini", {
            "api_key": self.gemini_api_key.get(),
            "model": self.gemini_model.get(),
            "max_tokens": int(self.gemini_max_tokens.get()),
            "temperature": float(self.gemini_temperature.get())
        }, self.gemini_status)

    def _save_ollama_config(self):
        """Save Ollama configuration."""
        self._save_provider_config("ollama", {
            "base_url": self.ollama_url.get(),
            "model": self.ollama_model.get(),
            "max_tokens": int(self.ollama_max_tokens.get()),
            "temperature": float(self.ollama_temperature.get())
        }, self.ollama_status)

    def _save_provider_config(self, provider_name: str, config: Dict[str, Any], status_label: ctk.CTkLabel):
        """Save provider configuration."""
        try:
            success = self.ai_manager.update_provider_config(provider_name, config)

            if success:
                CTkMessagebox(
                    title="Configuration Saved",
                    message=f"{provider_name.title()} configuration saved successfully!",
                    icon="check"
                )
                self._refresh_status()
            else:
                CTkMessagebox(
                    title="Error",
                    message=f"Failed to save {provider_name} configuration.",
                    icon="cancel"
                )

        except Exception as e:
            self.logger.error(f"Error saving {provider_name} config: {e}")
            CTkMessagebox(
                title="Error",
                message=f"Error saving configuration: {str(e)}",
                icon="cancel"
            )

    def _on_active_provider_changed(self, provider_name: str):
        """Handle active provider change."""
        try:
            self.ai_manager.set_active_provider(provider_name)
            CTkMessagebox(
                title="Active Provider Changed",
                message=f"Active provider set to: {provider_name}",
                icon="info"
            )
        except Exception as e:
            self.logger.error(f"Error changing active provider: {e}")
            CTkMessagebox(
                title="Error",
                message=f"Error changing active provider: {str(e)}",
                icon="cancel"
            )

    def _test_all_providers(self):
        """Test all providers."""
        if self.test_in_progress:
            return

        self.test_in_progress = True

        def test_all_thread():
            try:
                results = self.ai_manager.test_all_providers()

                # Update status for each provider
                for provider_name, working in results.items():
                    if provider_name == "chatgpt":
                        status = "✓ Working" if working else "✗ Not working"
                        color = "green" if working else "red"
                        self.after(0, lambda: self.chatgpt_status.configure(text=status, text_color=color))
                    elif provider_name == "gemini":
                        status = "✓ Working" if working else "✗ Not working"
                        color = "green" if working else "red"
                        self.after(0, lambda: self.gemini_status.configure(text=status, text_color=color))
                    elif provider_name == "ollama":
                        status = "✓ Working" if working else "✗ Not working"
                        color = "green" if working else "red"
                        self.after(0, lambda: self.ollama_status.configure(text=status, text_color=color))

                working_count = sum(results.values())
                total_count = len(results)

                self.after(0, lambda: CTkMessagebox(
                    title="Test Results",
                    message=f"Tested {total_count} providers.\n{working_count} working, {total_count - working_count} not working.",
                    icon="info"
                ))

            except Exception as e:
                self.logger.error(f"Error testing all providers: {e}")
                self.after(0, lambda: CTkMessagebox(
                    title="Error",
                    message=f"Error testing providers: {str(e)}",
                    icon="cancel"
                ))
            finally:
                self.test_in_progress = False

        import threading
        threading.Thread(target=test_all_thread, daemon=True).start()
