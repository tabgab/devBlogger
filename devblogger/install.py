#!/usr/bin/env python3
"""
DevBlogger - Installation Script
Automated installation and setup for DevBlogger
"""

import sys
import subprocess
import platform
import os
from pathlib import Path
import argparse


def run_command(command, description, check=True):
    """Run a shell command with error handling."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e.stderr.strip()}")
        if check:
            sys.exit(1)
        return e


def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")

    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"   ❌ Python {version.major}.{version.minor} is not supported")
        print("   ℹ️  Please install Python 3.8 or higher")
        sys.exit(1)

    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} is compatible")


def check_uv_installation():
    """Check if UV is installed."""
    print("🔍 Checking UV installation...")

    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ UV is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ⚠️  UV is not installed")
        print("   ℹ️  Installing UV...")
        install_uv()
        return True


def install_uv():
    """Install UV package manager."""
    system = platform.system().lower()

    if system == "linux":
        run_command(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "Installing UV for Linux"
        )
    elif system == "darwin":  # macOS
        run_command(
            "/bin/bash -c \"$(curl -fsSL https://astral.sh/uv/install.sh)\"",
            "Installing UV for macOS"
        )
    elif system == "windows":
        run_command(
            "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"",
            "Installing UV for Windows"
        )
    else:
        print(f"   ❌ Unsupported platform: {system}")
        print("   ℹ️  Please install UV manually from https://github.com/astral-sh/uv")
        sys.exit(1)


def create_virtual_environment():
    """Create UV virtual environment and install dependencies."""
    print("📦 Creating virtual environment and installing dependencies...")

    venv_path = Path("devblogger-env")

    # Create virtual environment
    try:
        run_command(
            "uv venv devblogger-env",
            "Creating UV virtual environment"
        )
    except Exception as e:
        print(f"   ⚠️  UV venv failed: {e}")
        print("   ℹ️  Trying alternative approach...")

        # Try creating venv with Python
        try:
            run_command(
                "python -m venv devblogger-env",
                "Creating virtual environment with Python"
            )
        except Exception as e:
            print(f"   ❌ Failed to create virtual environment: {e}")
            print("   ℹ️  Please create manually:")
            print("      uv venv devblogger-env")
            print("      or")
            print("      python -m venv devblogger-env")
            sys.exit(1)

    # Install dependencies into virtual environment
    try:
        if Path("pyproject.toml").exists():
            # Use UV sync to install all dependencies from pyproject.toml
            # Activate environment first, then run uv sync
            if os.name == 'nt':  # Windows
                activate_script = venv_path / "Scripts" / "activate"
                run_command(
                    f"{activate_script} && uv sync",
                    "Installing all dependencies with UV sync"
                )

                # Also install requirements.txt if it exists (for any additional deps)
                if Path("requirements.txt").exists():
                    run_command(
                        f"{activate_script} && uv pip install -r requirements.txt",
                        "Installing additional dependencies from requirements.txt"
                    )
            else:  # Unix/Linux/Mac
                activate_script = venv_path / "bin" / "activate"
                run_command(
                    f"source {activate_script} && uv sync",
                    "Installing all dependencies with UV sync"
                )

                # Also install requirements.txt if it exists (for any additional deps)
                if Path("requirements.txt").exists():
                    run_command(
                        f"source {activate_script} && uv pip install -r requirements.txt",
                        "Installing additional dependencies from requirements.txt"
                    )
        else:
            # Fallback to requirements.txt only
            if os.name == 'nt':  # Windows
                activate_script = venv_path / "Scripts" / "activate"
                run_command(
                    f"{activate_script} && uv pip install -r requirements.txt",
                    "Installing dependencies with UV pip"
                )
            else:  # Unix/Linux/Mac
                activate_script = venv_path / "bin" / "activate"
                run_command(
                    f"source {activate_script} && uv pip install -r requirements.txt",
                    "Installing dependencies with UV pip"
                )
    except Exception as e:
        print(f"   ⚠️  UV sync/pip failed: {e}")
        print("   ℹ️  Trying with regular pip...")

        # Activate environment and use pip
        if os.name == 'nt':  # Windows
            activate_script = venv_path / "Scripts" / "activate"
            pip_cmd = f"{activate_script} && pip install -e . && pip install -r requirements.txt"
        else:  # Unix/Linux/Mac
            activate_script = venv_path / "bin" / "activate"
            pip_cmd = f"source {activate_script} && pip install -e . && pip install -r requirements.txt"

        try:
            run_command(
                pip_cmd,
                "Installing dependencies with pip"
            )
        except Exception as e:
            print(f"   ❌ Failed to install dependencies: {e}")
            print("   ℹ️  Please install manually:")
            print(f"      source {venv_path}/bin/activate")
            print("      uv sync")
            print("      uv pip install -r requirements.txt")
            sys.exit(1)

    print(f"   ✅ Virtual environment created at: {venv_path}")
    print(f"   ✅ Dependencies installed successfully")


def create_activation_script():
    """Create activation script for easy startup."""
    print("🚀 Creating activation script...")

    script_content = """#!/bin/bash
# DevBlogger Activation Script
# This script activates the virtual environment and runs DevBlogger

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/devblogger-env"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please run the installation script first:"
    echo "  python install.py"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Check if activation worked
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# Run DevBlogger
echo "🚀 Starting DevBlogger..."
python -m src.main "$@"
"""

    script_path = Path("run_devblogger.sh")
    with open(script_path, "w") as f:
        f.write(script_content)

    # Make executable
    script_path.chmod(0o755)

    print(f"   ✅ Created activation script: {script_path}")
    print("   ℹ️  Usage: ./run_devblogger.sh")


def check_ollama_availability():
    """Check if Ollama is available on the system."""
    print("🤖 Checking Ollama availability...")

    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ Ollama is installed: {result.stdout.strip()}")

        # Check what models are available
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            # Models are available
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # More than just the header
                print(f"   ✅ Found {len(lines) - 1} model(s) available:")
                for line in lines[1:]:  # Skip header
                    model_name = line.split()[0]
                    print(f"      • {model_name}")
            else:
                print("   ℹ️  Ollama is installed but no models are available")
                print("   ℹ️  To use Ollama, install models manually:")
                print("      ollama pull llama2")
                print("      ollama pull codellama")
                print("      ollama pull mistral")
        else:
            print("   ℹ️  Ollama is installed but no models are available")
            print("   ℹ️  To use Ollama, install models manually:")
            print("      ollama pull llama2")
            print("      ollama pull codellama")
            print("      ollama pull mistral")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ℹ️  Ollama is not installed")
        print("   ℹ️  DevBlogger works perfectly without Ollama")
        print("   ℹ️  You can use ChatGPT and Gemini for AI generation")
        print("   ℹ️  To add Ollama support later:")
        print("      1. Install from https://ollama.ai/")
        print("      2. Pull models: ollama pull llama2")


def create_directories():
    """Create necessary directories."""
    print("📁 Creating application directories...")

    directories = [
        "Generated_Entries",
        "logs",
        "assets",
        "docs"
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ Created {directory}/")


def create_sample_config():
    """Create sample configuration file."""
    print("⚙️  Creating sample configuration...")

    config_content = """# DevBlogger Configuration
# This is a sample configuration file. Copy this to your config directory.

[window]
width = 1200
height = 800

[ai_providers.chatgpt]
api_key = "your-openai-api-key-here"
model = "gpt-4"
max_tokens = 2000
temperature = 0.7

[ai_providers.gemini]
api_key = "your-google-gemini-api-key-here"
model = "gemini-pro"
max_tokens = 2000
temperature = 0.7

[ai_providers.ollama]
base_url = "http://localhost:11434"
model = "llama2"
max_tokens = 2000
temperature = 0.7

[blog]
default_prompt = "Write a concise, informative, and interesting development blog entry based on the provided commit information. Focus on the most significant changes and improvements. Write in first person as if you are the developer describing your work. Keep the tone professional but engaging. Highlight technical achievements, challenges overcome, and the impact of the changes."
"""

    with open("devblogger_config.sample", "w") as f:
        f.write(config_content)

    print("   ✅ Created devblogger_config.sample")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")

    try:
        result = run_command(
            "python -m pytest tests/ -v",
            "Running test suite",
            check=False
        )

        if result.returncode == 0:
            print("   ✅ All tests passed!")
        else:
            print("   ⚠️  Some tests failed. Check the output above.")
            print("   ℹ️  This is normal if you haven't configured API keys yet.")

    except Exception as e:
        print(f"   ❌ Error running tests: {e}")


def main():
    """Main installation function."""
    print("🚀 DevBlogger Installation Script")
    print("=" * 40)

    parser = argparse.ArgumentParser(description="Install DevBlogger")
    parser.add_argument("--skip-tests", action="store_true",
                       help="Skip running tests")
    args = parser.parse_args()

    # Define virtual environment path
    venv_path = Path("devblogger-env")

    try:
        # Pre-installation checks
        check_python_version()
        check_uv_installation()

        # Installation steps
        create_virtual_environment()
        create_activation_script()

        # Always check Ollama availability (never install it)
        check_ollama_availability()

        create_directories()
        create_sample_config()

        if not args.skip_tests:
            run_tests()

        # Success message
        print("\n" + "=" * 40)
        print("🎉 Installation completed successfully!")
        print("✅ Virtual environment created and populated!")
        print(f"📍 Virtual environment location: {venv_path}")
        print("\n🔧 To activate the virtual environment and run DevBlogger:")
        if os.name == 'nt':  # Windows
            print("  devblogger-env\\Scripts\\activate")
            print("  python -m src.main")
        else:  # Unix/Linux/Mac
            print("  source devblogger-env/bin/activate")
            print("  python -m src.main")
        print("\nOr use the activation script:")
        print("  ./run_devblogger.sh")
        print("\nFor more information, see README.md")

    except KeyboardInterrupt:
        print("\n\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
