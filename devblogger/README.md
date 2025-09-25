# DevBlogger

**Semi-automatic development blog system** - Generate professional blog entries from your GitHub commits using AI.

![DevBlogger Logo](https://via.placeholder.com/800x200/4A90E2/FFFFFF?text=DevBlogger)

## Overview

DevBlogger is a powerful desktop application that transforms your GitHub commit history into professional development blog entries. Using advanced AI models (ChatGPT, Google Gemini, and Ollama), it analyzes your commits and generates engaging, well-structured blog posts that showcase your development work.

## Features

### 🚀 **Core Functionality**
- **GitHub Integration**: OAuth authentication with read-only repository access
- **Multi-AI Support**: ChatGPT, Google Gemini, and Ollama integration
- **Smart Commit Analysis**: Advanced filtering and selection of commits
- **Professional Output**: Clean markdown with proper frontmatter and metadata
- **File Management**: Organized storage with search and export capabilities

### 🎯 **User Experience**
- **Modern GUI**: Built with CustomTkinter for a professional interface
- **Tabbed Interface**: Organized workflow with GitHub, AI Config, and Blog tabs
- **Real-time Status**: Live indicators for GitHub connection and AI provider status
- **Progress Tracking**: Visual feedback during blog generation
- **Error Handling**: Comprehensive error messages and recovery options

### 📊 **Analytics & Management**
- **Generation Statistics**: Detailed stats about commits and changes
- **Storage Analytics**: Track usage by repository and AI provider
- **Search & Filter**: Find entries by title, repository, or tags
- **Export Options**: Export to JSON or combined markdown formats
- **Backup & Recovery**: Built-in backup and storage validation

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- A GitHub account
- API keys for AI providers (optional, for enhanced features)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd devblogger
   ```

2. **Run the installation script**
   ```bash
   python install.py
   ```

3. **Start the application**
   ```bash
   ./run_devblogger.sh
   ```

   **Alternative startup:**
   ```bash
   source devblogger-env/bin/activate
   python -m src.main
   ```

   **Note**: DevBlogger requires a graphical environment to run. If you encounter a "Cannot run GUI application in headless environment" error, ensure you're running in a desktop environment with display capabilities.

### AI Provider Setup

#### ChatGPT (OpenAI)
1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. In DevBlogger, go to AI Configuration tab
3. Select ChatGPT tab and enter your API key
4. Test the connection and save

#### Google Gemini
1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. In DevBlogger, go to AI Configuration tab
3. Select Gemini tab and enter your API key
4. Test the connection and save

#### Ollama (Local AI)
1. Install [Ollama](https://ollama.ai/) on your system
2. Pull desired models manually:
   ```bash
   ollama pull llama2
   ollama pull codellama
   ollama pull mistral
   ```
3. In DevBlogger, go to AI Configuration tab
4. Select Ollama tab and verify the base URL (default: http://localhost:11434)
5. Test the connection and save

**Note**: DevBlogger will only use Ollama if it's already installed on your system. It will never download or install models automatically.

## Usage

### Basic Workflow

1. **Authenticate with GitHub**
   - Click "Login to GitHub" in the GitHub tab
   - Authorize the application (read-only access)
   - Select your repository from the dropdown

2. **Browse and Select Commits**
   - Use filters to find relevant commits (date range, search, max count)
   - Check commits you want to include in your blog entry
   - Preview commit details in the right pane

3. **Configure AI Generation**
   - Choose your preferred AI provider
   - Customize the prompt if needed
   - Review generation settings

4. **Generate Blog Entry**
   - Click "Generate Blog Entry"
   - Review the generated content
   - Edit if necessary
   - Save to file

### Advanced Features

#### Custom Prompts
Create custom prompts for different types of blog entries:

```markdown
Write a technical deep-dive blog post about the recent changes in the authentication system.
Focus on the security improvements, performance optimizations, and architectural decisions.
Include code examples where relevant and explain the rationale behind each change.
```

#### Bulk Generation
Generate blog entries for multiple repositories at once using the bulk generation feature.

#### Regeneration
Regenerate existing blog entries with different AI providers to get varied perspectives.

## Configuration

### Settings File
DevBlogger stores configuration in `~/.devblogger/settings.json`:

```json
{
  "window_size": [1200, 800],
  "default_prompt": "Your custom prompt here...",
  "ai_providers": {
    "chatgpt": {
      "api_key": "your-openai-key",
      "model": "gpt-4",
      "max_tokens": 2000,
      "temperature": 0.7
    },
    "gemini": {
      "api_key": "your-gemini-key",
      "model": "gemini-pro",
      "max_tokens": 2000,
      "temperature": 0.7
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama2",
      "max_tokens": 2000,
      "temperature": 0.7
    }
  },
  "active_ai_provider": "chatgpt"
}
```

### Command Line Options

```bash
# Run with custom config directory
python -m src.main --config-dir /path/to/config

# Run with debug logging
python -m src.main --debug

# Show version
python -m src.main --version
```

## Architecture

### Core Components

```
src/
├── main.py                 # Application entry point
├── config/                 # Configuration management
│   ├── settings.py        # Settings and preferences
│   └── database.py        # Database operations
├── github/                 # GitHub integration
│   ├── auth.py            # OAuth authentication
│   ├── client.py          # GitHub API client
│   └── models.py          # GitHub data models
├── ai/                     # AI provider integration
│   ├── base.py            # Base AI provider interface
│   ├── manager.py         # AI provider management
│   ├── openai_client.py   # ChatGPT/OpenAI client
│   ├── gemini_client.py   # Google Gemini client
│   └── ollama_client.py   # Ollama local AI client
├── blog/                   # Blog generation system
│   ├── generator.py       # Core generation engine
│   ├── storage.py         # File storage management
│   └── manager.py         # High-level blog management
└── gui/                    # User interface
    ├── main_window.py     # Main application window
    ├── login_dialog.py    # GitHub authentication dialog
    ├── commit_browser.py  # Commit selection interface
    ├── ai_config.py       # AI configuration panel
    └── blog_editor.py     # Blog editing interface
```

### Data Flow

1. **GitHub Authentication** → OAuth flow with callback server
2. **Repository Selection** → List and select target repository
3. **Commit Retrieval** → Fetch commits via GitHub API
4. **Commit Filtering** → Apply date, search, and count filters
5. **AI Generation** → Send filtered commits to AI provider
6. **Content Processing** → Clean and format AI response
7. **File Storage** → Save as markdown with metadata
8. **Index Management** → Update storage index and statistics

## API Reference

### BlogManager

Main interface for blog operations:

```python
from src.blog.manager import BlogManager

# Generate blog from commits
result = blog_manager.generate_blog_from_commits(
    commits=selected_commits,
    repository="owner/repo",
    prompt="Custom prompt...",
    provider="chatgpt"
)

# Get blog entries
entries = blog_manager.get_blog_entries(
    repository="owner/repo",
    limit=10
)

# Search entries
results = blog_manager.search_entries("feature")
```

### Settings

Configuration management:

```python
from src.config.settings import Settings

settings = Settings()
settings.set_window_size(1400, 900)
settings.set_default_prompt("Custom prompt...")
settings.set_ai_provider_config("chatgpt", config_dict)
```

### GitHub Client

GitHub API operations:

```python
from src.github.client import GitHubClient

client = GitHubClient(auth, settings)
repositories = client.get_user_repositories()
commits = client.get_repository_commits("owner", "repo")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v tests/
```

### Test Structure

- `tests/test_config.py` - Configuration and database tests
- `tests/test_ai.py` - AI provider integration tests
- `tests/test_blog.py` - Blog generation and storage tests
- `tests/test_github.py` - GitHub integration tests (planned)

## Development

### Project Structure

```
devblogger/
├── src/                    # Source code
├── tests/                  # Test suite
├── docs/                   # Documentation
├── assets/                 # Images and icons
├── requirements.txt        # Python dependencies
├── pyproject.toml         # UV project configuration
├── README.md              # This file
└── LICENSE                # License file
```

### Adding New AI Providers

1. Create a new provider class inheriting from `AIProvider`
2. Implement required methods: `is_configured()`, `test_connection()`, `generate_text()`
3. Add provider registration in `DevBloggerAIProviderManager`
4. Update configuration schema in `Settings`
5. Add tests for the new provider

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Troubleshooting

### Common Issues

#### GitHub Authentication Fails
- Check your internet connection
- Verify GitHub credentials
- Ensure the OAuth app is properly configured

#### AI Provider Connection Issues
- Verify API keys are correct
- Check API quotas and limits
- Ensure network connectivity for Ollama

#### Empty Commit Lists
- Check repository permissions
- Verify the repository exists and is accessible
- Try refreshing the repository list

#### Blog Generation Errors
- Ensure commits have meaningful messages
- Check AI provider configuration
- Verify API quotas haven't been exceeded

#### GUI Application in Headless Environment
- **Error**: "Cannot run GUI application in headless environment!"
- **Cause**: DevBlogger requires a graphical environment to run
- **Solutions**:
  - Run on a desktop/laptop with display capabilities
  - Use X11 forwarding: `ssh -X user@server`
  - Use VNC or similar remote desktop solution
  - Run in a virtual machine with GUI support

### Debug Mode

Run with debug logging:

```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.main import main
main()
"
```

### Logs Location

Logs are stored in:
- Linux/macOS: `~/.devblogger/logs/`
- Windows: `%APPDATA%\DevBlogger\logs\`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Full Documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

## Changelog

### Version 0.1.0
- Initial release
- GitHub OAuth integration
- Multi-AI provider support (ChatGPT, Gemini, Ollama)
- Professional markdown generation
- File management and storage
- Comprehensive test suite

### Planned Features
- [ ] GitHub webhooks for automatic blog generation
- [ ] Batch processing for multiple repositories
- [ ] Custom themes and templates
- [ ] Integration with static site generators
- [ ] Mobile-responsive web interface
- [ ] Plugin system for additional AI providers

---

**DevBlogger** - Transform your development work into compelling blog content with the power of AI.
