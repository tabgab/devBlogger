#!/usr/bin/env python3
"""
DevBlogger - Semi-automatic development blog system
Main application entry point
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import non-GUI modules first
from .config.settings import Settings
from .config.database import DatabaseManager
from .ai.manager import DevBloggerAIProviderManager
from .blog.manager import BlogManager

# GUI imports will be done later, after headless check


def main():
    """Main application entry point."""
    try:
        # Initialize the application
        app = DevBloggerApp()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def debug_main():
    """Debug version of main with enhanced logging."""
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('debug.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting debug version of DevBlogger")

    try:
        logger.info("Creating DevBloggerApp instance")
        # Initialize the application
        app = DevBloggerApp()
        logger.info("Running DevBloggerApp")
        app.run()
        logger.info("Application completed successfully")
    except KeyboardInterrupt:
        logger.info("Application terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def is_headless():
    """Check if running in a headless environment."""
    import os

    # Check for DISPLAY environment variable
    if os.name == 'posix' and 'DISPLAY' not in os.environ:
        return True

    # Check for common headless indicators
    headless_indicators = [
        'HEADLESS',
        'CI',
        'CONTINUOUS_INTEGRATION',
        'GITHUB_ACTIONS',
        'GITLAB_CI',
        'TRAVIS'
    ]

    for indicator in headless_indicators:
        if os.environ.get(indicator, '').lower() in ('true', '1', 'yes'):
            return True

    return False


def start_virtual_display():
    """Start a virtual display for GUI applications in headless environments."""
    import subprocess
    import time
    import platform

    try:
        system = platform.system().lower()

        if system == "linux":
            # Try to start Xvfb (X Virtual Framebuffer)
            try:
                # Check if Xvfb is available
                result = subprocess.run(
                    ["which", "Xvfb"],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Start Xvfb on a virtual display
                result = subprocess.run(
                    ["Xvfb", ":99", "-ac", "-screen", "0", "1280x1024x16"],
                    capture_output=True,
                    text=False  # Don't decode as text to avoid encoding issues
                )

                # Set DISPLAY environment variable
                os.environ['DISPLAY'] = ':99'

                # Wait a moment for Xvfb to start
                time.sleep(1)

                print("✅ Started virtual display using Xvfb")
                return True

            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️  Xvfb not available, trying alternative...")

        elif system == "darwin":  # macOS
            # Try to start XQuartz or use existing display
            try:
                # Check if XQuartz is running
                result = subprocess.run(
                    ["pgrep", "-f", "XQuartz"],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    # XQuartz is running, set display
                    os.environ['DISPLAY'] = ':0'
                    print("✅ Using existing XQuartz display")
                    return True
                else:
                    print("⚠️  XQuartz not running, trying to start...")

                    # Try to start XQuartz
                    result = subprocess.run(
                        ["open", "-a", "XQuartz"],
                        capture_output=True,
                        text=True
                    )

                    # Wait for XQuartz to start
                    time.sleep(3)

                    # Check if it started
                    result = subprocess.run(
                        ["pgrep", "-f", "XQuartz"],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        os.environ['DISPLAY'] = ':0'
                        print("✅ Started XQuartz display")
                        return True
                    else:
                        print("❌ Could not start XQuartz")

            except Exception as e:
                print(f"⚠️  Error with XQuartz: {e}")

        # If we get here, we couldn't start a virtual display
        return False

    except Exception as e:
        print(f"❌ Error starting virtual display: {e}")
        return False


def cleanup_virtual_display():
    """Clean up virtual display resources."""
    try:
        import subprocess
        import signal
        import os

        # Kill any Xvfb processes we might have started
        try:
            result = subprocess.run(
                ["pkill", "-f", "Xvfb"],
                capture_output=True,
                text=True
            )
        except:
            pass

        # Kill any XQuartz processes if they were started by us
        try:
            result = subprocess.run(
                ["pkill", "-f", "XQuartz"],
                capture_output=True,
                text=True
            )
        except:
            pass

    except Exception as e:
        # Don't let cleanup errors crash the application
        pass


class DevBloggerApp:
    """Main application class."""

    def __init__(self):
        """Initialize the DevBlogger application."""
        self.settings = None
        self.database = None
        self.main_window = None

    def run(self):
        """Run the application."""
        # Import GUI modules only after headless check
        try:
            import customtkinter as ctk
            from .gui.main_window import MainWindow
        except ImportError as e:
            print(f"Error importing GUI modules: {e}")
            print("Please ensure all dependencies are installed with: uv sync")
            sys.exit(1)

        # Initialize settings and database
        self._initialize_config()

        # Set CustomTkinter appearance
        ctk.set_appearance_mode("System")  # "System", "Dark", or "Light"
        ctk.set_default_color_theme("blue")  # "blue", "green", or "dark-blue"

        # Create and run the main window with proper macOS autorelease pool management
        try:
            # Try to set up proper autorelease pool for macOS
            import platform
            if platform.system() == "Darwin":  # macOS
                try:
                    import objc
                    # Create an autorelease pool for the main thread
                    pool = objc.NSAutoreleasePool.alloc().init()
                    try:
                        self.main_window = MainWindow(self.settings, self.database)
                        self.main_window.mainloop()
                    finally:
                        pool.drain()
                except ImportError:
                    # objc not available, run without pool management
                    self.main_window = MainWindow(self.settings, self.database)
                    self.main_window.mainloop()
            else:
                # Not macOS, run normally
                self.main_window = MainWindow(self.settings, self.database)
                self.main_window.mainloop()
        except Exception as e:
            print(f"Error running main window: {e}")
            # Fallback to basic execution
            self.main_window = MainWindow(self.settings, self.database)
            self.main_window.mainloop()

    def _initialize_config(self):
        """Initialize application configuration and database."""
        try:
            # Create settings instance
            self.settings = Settings()

            # Create database instance
            self.database = DatabaseManager()

            # Ensure required directories exist
            self._ensure_directories()

        except Exception as e:
            print(f"Error initializing configuration: {e}")
            raise

    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.settings.get_generated_entries_dir(),
            self.settings.get_logs_dir(),
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
