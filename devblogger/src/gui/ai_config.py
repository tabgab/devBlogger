#!/usr/bin/env python3
"""
DevBlogger - AI Configuration Panel
"""

import logging
from typing import Dict, Any, Optional
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

        # Header - reduce padding
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="AI Provider Configuration",
            font=ctk.CTkFont(size=16, weight="bold")  # Smaller font
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

        # Main content - reduce padding
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Create tabbed interface for providers
        self._create_provider_tabs(content_frame)

    def _create_provider_tabs(self, parent):
        """Create custom tabbed interface for different providers."""
        # Create tab buttons frame - positioned at top
        self.tab_buttons_frame = ctk.CTkFrame(parent)
        self.tab_buttons_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        
        # Create tab content frame - takes up remaining space
        self.tab_content_frame = ctk.CTkFrame(parent)
        self.tab_content_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.tab_content_frame.grid_columnconfigure(0, weight=1)
        self.tab_content_frame.grid_rowconfigure(0, weight=1)
        
        # Create common controls frame - at bottom
        self.common_controls_frame = ctk.CTkFrame(parent)
        self.common_controls_frame.grid(row=2, column=0, padx=0, pady=0, sticky="ew")
        
        # Update parent grid to give weight to content area
        parent.grid_rowconfigure(0, weight=0)  # Tab buttons - no weight
        parent.grid_rowconfigure(1, weight=1)  # Tab content - all weight
        parent.grid_rowconfigure(2, weight=0)  # Common controls - no weight
        
        # Create tab buttons
        self.current_provider_tab = "ChatGPT"
        self._create_provider_tab_buttons()
        
        # Create tab content areas
        self._create_provider_tab_contents()
        
        # Create common controls
        self._create_common_controls()
        
        # Show initial tab
        self._show_provider_tab("ChatGPT")

    def _create_provider_tab_buttons(self):
        """Create custom tab buttons for AI providers."""
        self.provider_tab_buttons = {}
        
        # ChatGPT tab button
        chatgpt_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="ChatGPT",
            command=lambda: self._show_provider_tab("ChatGPT"),
            width=120
        )
        chatgpt_btn.grid(row=0, column=0, padx=(5, 2), pady=5)
        self.provider_tab_buttons["ChatGPT"] = chatgpt_btn
        
        # Gemini tab button
        gemini_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="Gemini",
            command=lambda: self._show_provider_tab("Gemini"),
            width=120
        )
        gemini_btn.grid(row=0, column=1, padx=2, pady=5)
        self.provider_tab_buttons["Gemini"] = gemini_btn
        
        # Ollama tab button
        ollama_btn = ctk.CTkButton(
            self.tab_buttons_frame,
            text="Ollama",
            command=lambda: self._show_provider_tab("Ollama"),
            width=120
        )
        ollama_btn.grid(row=0, column=2, padx=(2, 5), pady=5)
        self.provider_tab_buttons["Ollama"] = ollama_btn

    def _create_provider_tab_contents(self):
        """Create tab content areas for AI providers."""
        self.provider_tab_contents = {}
        
        # ChatGPT tab content
        self._create_chatgpt_content()
        
        # Gemini tab content
        self._create_gemini_content()
        
        # Ollama tab content
        self._create_ollama_content()

    def _show_provider_tab(self, tab_name):
        """Show the specified provider tab."""
        # Hide all tab contents
        for name, content in self.provider_tab_contents.items():
            content.grid_remove()
        
        # Update button states
        for name, button in self.provider_tab_buttons.items():
            if name == tab_name:
                button.configure(fg_color=("gray75", "gray25"))  # Active state
            else:
                button.configure(fg_color=("gray90", "gray13"))  # Inactive state
        
        # Show selected tab content
        if tab_name in self.provider_tab_contents:
            self.provider_tab_contents[tab_name].grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        
        self.current_provider_tab = tab_name

    def _create_chatgpt_content(self):
        """Create ChatGPT configuration content."""
        content = ctk.CTkFrame(self.tab_content_frame)
        content.grid_columnconfigure(1, weight=1)
        self.provider_tab_contents["ChatGPT"] = content

        # API Key
        api_key_label = ctk.CTkLabel(content, text="API Key:")
        api_key_label.grid(row=0, column=0, padx=(10, 10), pady=(10, 5), sticky="w")

        self.chatgpt_api_key = ctk.CTkEntry(
            content,
            placeholder_text="sk-...",
            show="•",
            width=300
        )
        self.chatgpt_api_key.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.chatgpt_model = ctk.CTkOptionMenu(
            content,
            values=["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"],
            width=200
        )
        self.chatgpt_model.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=2, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.chatgpt_max_tokens = ctk.CTkEntry(content, width=100)
        self.chatgpt_max_tokens.insert(0, "2000")
        self.chatgpt_max_tokens.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=3, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

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
        test_button.grid(row=4, column=0, padx=(10, 10), pady=(20, 0))

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
        self.chatgpt_status.grid(row=5, column=0, columnspan=2, pady=(10, 10))

    def _create_gemini_content(self):
        """Create Gemini configuration content."""
        content = ctk.CTkFrame(self.tab_content_frame)
        content.grid_columnconfigure(1, weight=1)
        self.provider_tab_contents["Gemini"] = content

        # API Key
        api_key_label = ctk.CTkLabel(content, text="API Key:")
        api_key_label.grid(row=0, column=0, padx=(10, 10), pady=(10, 5), sticky="w")

        self.gemini_api_key = ctk.CTkEntry(
            content,
            placeholder_text="AIza...",
            show="•",
            width=300
        )
        self.gemini_api_key.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.gemini_model = ctk.CTkOptionMenu(
            content,
            values=["gemini-pro", "gemini-pro-vision"],
            width=200
        )
        self.gemini_model.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=2, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.gemini_max_tokens = ctk.CTkEntry(content, width=100)
        self.gemini_max_tokens.insert(0, "2000")
        self.gemini_max_tokens.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=3, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

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
        test_button.grid(row=4, column=0, padx=(10, 10), pady=(20, 0))

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
        self.gemini_status.grid(row=5, column=0, columnspan=2, pady=(10, 10))

    def _create_ollama_content(self):
        """Create Ollama configuration content."""
        content = ctk.CTkFrame(self.tab_content_frame)
        content.grid_columnconfigure(1, weight=1)
        self.provider_tab_contents["Ollama"] = content

        # Base URL
        url_label = ctk.CTkLabel(content, text="Base URL:")
        url_label.grid(row=0, column=0, padx=(10, 10), pady=(10, 5), sticky="w")

        self.ollama_url = ctk.CTkEntry(
            content,
            placeholder_text="http://localhost:11434",
            width=300
        )
        self.ollama_url.insert(0, "http://localhost:11434")
        self.ollama_url.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="ew")

        # Model selection
        model_label = ctk.CTkLabel(content, text="Model:")
        model_label.grid(row=1, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        # Model input frame for both dropdown and manual entry
        model_frame = ctk.CTkFrame(content, fg_color="transparent")
        model_frame.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")
        model_frame.grid_columnconfigure(0, weight=1)

        self.ollama_model = ctk.CTkEntry(
            model_frame,
            placeholder_text="Enter model name (e.g., llama3.1:latest)",
            width=250
        )
        self.ollama_model.grid(row=0, column=0, sticky="ew")

        # Refresh models button
        refresh_models_button = ctk.CTkButton(
            model_frame,
            text="↻",
            command=self._refresh_ollama_models,
            width=30,
            height=28
        )
        refresh_models_button.grid(row=0, column=1, padx=(5, 0))

        # Available models display
        self.ollama_models_label = ctk.CTkLabel(
            content,
            text="Available models: Loading...",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.ollama_models_label.grid(row=2, column=1, padx=(0, 10), pady=(2, 5), sticky="w")

        # Max tokens
        max_tokens_label = ctk.CTkLabel(content, text="Max Tokens:")
        max_tokens_label.grid(row=3, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.ollama_max_tokens = ctk.CTkEntry(content, width=100)
        self.ollama_max_tokens.insert(0, "2000")
        self.ollama_max_tokens.grid(row=3, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Temperature
        temp_label = ctk.CTkLabel(content, text="Temperature:")
        temp_label.grid(row=4, column=0, padx=(10, 10), pady=(0, 5), sticky="w")

        self.ollama_temperature = ctk.CTkEntry(content, width=100)
        self.ollama_temperature.insert(0, "0.7")
        self.ollama_temperature.grid(row=4, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        # Test button
        test_button = ctk.CTkButton(
            content,
            text="Test Connection",
            command=self._test_ollama,
            width=120
        )
        test_button.grid(row=5, column=0, padx=(10, 10), pady=(20, 0))

        # Save button
        save_button = ctk.CTkButton(
            content,
            text="Save Configuration",
            command=self._save_ollama_config,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        )
        save_button.grid(row=5, column=1, padx=(0, 10), pady=(20, 0))

        # Status label
        self.ollama_status = ctk.CTkLabel(
            content,
            text="Not configured",
            font=ctk.CTkFont(size=11),
            text_color="red"
        )
        self.ollama_status.grid(row=6, column=0, columnspan=2, pady=(10, 10))


    def _create_common_controls(self):
        """Create common controls for all providers."""
        # Active provider selection
        provider_label = ctk.CTkLabel(self.common_controls_frame, text="Active Provider:")
        provider_label.grid(row=0, column=0, padx=(10, 10), pady=5)

        self.active_provider_var = ctk.StringVar()
        self.active_provider_dropdown = ctk.CTkOptionMenu(
            self.common_controls_frame,
            variable=self.active_provider_var,
            values=["Loading..."],
            command=self._on_active_provider_changed,
            width=150
        )
        self.active_provider_dropdown.grid(row=0, column=1, padx=(0, 10), pady=5)

        # Refresh status button
        refresh_button = ctk.CTkButton(
            self.common_controls_frame,
            text="Refresh Status",
            command=self._refresh_status,
            width=120
        )
        refresh_button.grid(row=0, column=2, padx=(0, 10), pady=5)

        # Test all providers button
        test_all_button = ctk.CTkButton(
            self.common_controls_frame,
            text="Test All",
            command=self._test_all_providers,
            width=100
        )
        test_all_button.grid(row=0, column=3, padx=(0, 10), pady=5)

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
                self.ollama_model.delete(0, "end")
                self.ollama_model.insert(0, ollama_config.get("model", "llama3.1:latest"))
                self.ollama_max_tokens.delete(0, "end")
                self.ollama_max_tokens.insert(0, str(ollama_config.get("max_tokens", 2000)))
                self.ollama_temperature.delete(0, "end")
                self.ollama_temperature.insert(0, str(ollama_config.get("temperature", 0.7)))

            # DON'T auto-refresh Ollama models or status - only when user clicks
            # Set initial status without testing
            self._set_initial_status()

        except Exception as e:
            self.logger.error(f"Error loading provider configs: {e}")

    def _set_initial_status(self):
        """Set initial status without testing connections."""
        try:
            # Just check if providers are configured, don't test connections
            providers = list(self.ai_manager.get_all_providers().keys())
            self.active_provider_dropdown.configure(values=providers)
            
            # Set basic status based on configuration only
            configured_count = 0
            
            # Check ChatGPT
            if self.chatgpt_api_key.get():
                self.chatgpt_status.configure(text="✓ Configured", text_color="blue")
                configured_count += 1
            else:
                self.chatgpt_status.configure(text="✗ Not configured", text_color="red")
            
            # Check Gemini
            if self.gemini_api_key.get():
                self.gemini_status.configure(text="✓ Configured", text_color="blue")
                configured_count += 1
            else:
                self.gemini_status.configure(text="✗ Not configured", text_color="red")
            
            # Check Ollama
            if self.ollama_url.get() and self.ollama_model.get():
                self.ollama_status.configure(text="✓ Configured", text_color="blue")
                configured_count += 1
            else:
                self.ollama_status.configure(text="✗ Not configured", text_color="red")
            
            # Update summary
            self.status_label.configure(text=f"{configured_count}/3 configured (click 'Refresh Status' to test)")
            
            # Set Ollama models status
            self.ollama_models_label.configure(text="Available models: Click ↻ to refresh")
            
        except Exception as e:
            self.logger.error(f"Error setting initial status: {e}")

    def _refresh_status(self):
        """Refresh provider status information by testing connections."""
        try:
            # Update active provider dropdown
            providers = list(self.ai_manager.get_all_providers().keys())
            self.active_provider_dropdown.configure(values=providers)

            # Set current active provider - prefer configured providers (don't test)
            configured_providers = self.ai_manager.get_configured_providers()
            
            if configured_providers:
                # Auto-select the first configured provider
                self.active_provider_var.set(configured_providers[0])
                self.ai_manager.set_active_provider(configured_providers[0])
            else:
                # Check current active provider
                active = self.ai_manager.get_active_provider()
                if active:
                    self.active_provider_var.set(active.name)

            # Update individual provider status by testing connections
            self._update_provider_status("chatgpt", self.chatgpt_status)
            self._update_provider_status("gemini", self.gemini_status)
            self._update_provider_status("ollama", self.ollama_status)
            
            # Update status label after testing
            configured_count = len(configured_providers)
            self.status_label.configure(
                text=f"{configured_count}/3 configured (testing connections...)"
            )

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
                    # Schedule UI update on main thread
                    def update_success():
                        if hasattr(self, 'test_in_progress'):  # Check if widget still exists
                            self._update_test_result(status_label, "✓ Working", "green")
                    self.after(0, update_success)
                else:
                    def update_failure():
                        if hasattr(self, 'test_in_progress'):  # Check if widget still exists
                            self._update_test_result(status_label, "✗ Not working", "red")
                    self.after(0, update_failure)
            except Exception as e:
                self.logger.error(f"Error testing {provider_name}: {e}")
                def update_error():
                    if hasattr(self, 'test_in_progress'):  # Check if widget still exists
                        self._update_test_result(status_label, "✗ Error", "red")
                self.after(0, update_error)
            finally:
                # Always reset the flag
                def reset_flag():
                    if hasattr(self, 'test_in_progress'):  # Check if widget still exists
                        self.test_in_progress = False
                self.after(0, reset_flag)

        import threading
        threading.Thread(target=test_thread, daemon=True).start()

    def _update_test_result(self, status_label: ctk.CTkLabel, text: str, color: str):
        """Update test result on main thread."""
        status_label.configure(text=text, text_color=color)
        self.test_in_progress = False

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
                self.logger.info(f"{provider_name.title()} configuration saved successfully!")
                # Update status to show success
                status_label.configure(text="✓ Configuration saved", text_color="green")
                self._refresh_status()
                
                # Call callback if it exists
                if hasattr(self, '_on_provider_config_changed') and callable(self._on_provider_config_changed):
                    self._on_provider_config_changed()
            else:
                self.logger.error(f"Failed to save {provider_name} configuration")
                status_label.configure(text="✗ Save failed", text_color="red")

        except Exception as e:
            self.logger.error(f"Error saving {provider_name} config: {e}")
            status_label.configure(text="✗ Save error", text_color="red")

    def _on_active_provider_changed(self, provider_name: str):
        """Handle active provider change."""
        try:
            self.ai_manager.set_active_provider(provider_name)
            self.logger.info(f"Active provider changed to: {provider_name}")
            # Update status to reflect the change
            self._refresh_status()
        except Exception as e:
            self.logger.error(f"Error changing active provider: {e}")
            # Only show error dialogs, not success dialogs
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

    def _refresh_ollama_models(self):
        """Refresh available Ollama models."""
        def refresh_thread():
            try:
                # Get Ollama provider
                ollama_provider = self.ai_manager.get_provider("ollama")
                if ollama_provider:
                    # Get available models
                    models = ollama_provider.get_available_models()
                    if models:
                        models_text = ", ".join(models[:5])  # Show first 5 models
                        if len(models) > 5:
                            models_text += f" (+{len(models) - 5} more)"
                        self.after(0, lambda: self.ollama_models_label.configure(
                            text=f"Available models: {models_text}"
                        ))
                    else:
                        self.after(0, lambda: self.ollama_models_label.configure(
                            text="Available models: None found (run 'ollama pull <model>' to install)"
                        ))
                else:
                    self.after(0, lambda: self.ollama_models_label.configure(
                        text="Available models: Ollama not configured"
                    ))
            except Exception as e:
                self.logger.error(f"Error refreshing Ollama models: {e}")
                self.after(0, lambda: self.ollama_models_label.configure(
                    text="Available models: Error loading (check Ollama connection)"
                ))

        import threading
        threading.Thread(target=refresh_thread, daemon=True).start()
