# Contributing to aX Agent Studio

Thank you for your interest in contributing to aX Agent Studio! This project thrives on community contributions, and we're excited to see what you'll build.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Contribution Guidelines](#contribution-guidelines)
- [Community & Support](#community--support)

---

## Code of Conduct

Be respectful, inclusive, and collaborative. We're building the future of agent orchestration together!

**Expected behavior:**
-  Be welcoming to newcomers
-  Respect differing viewpoints
-  Accept constructive criticism
-  Focus on what's best for the community

**Unacceptable behavior:**
-  Harassment, trolling, or insulting comments
-  Personal or political attacks
-  Publishing others' private information

---

## Getting Started

### Prerequisites

Before contributing, make sure you have:

- **Python 3.13+** installed
- **uv** package manager ([installation guide](https://github.com/astral-sh/uv))
- **aX Platform MCP server** running locally (optional for testing)
- **Git** for version control

### Fork & Clone

1. **Fork** this repository on GitHub
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ax-agent-studio.git
   cd ax-agent-studio
   ```
3. **Add upstream** remote:
   ```bash
   git remote add upstream https://github.com/ax-platform/ax-agent-studio.git
   ```

---

## Development Setup

### Install Dependencies

```bash
# Install all dependencies including dev tools (fast with uv!)
uv pip install -e ".[dev]"

# Verify installation
python --version  # Should show Python 3.13+
```

### Set Up Pre-commit Hooks

We use pre-commit hooks to ensure code quality before commits. These hooks automatically check:
- Code formatting (Ruff)
- Linting (Ruff)
- Type checking (mypy)
- Security issues (Bandit)
- File formatting (trailing whitespace, line endings, etc.)

**Install pre-commit hooks:**
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually on all files (optional)
pre-commit run --all-files
```

**The hooks will now run automatically on every commit!** If any check fails, the commit will be blocked until you fix the issues.

**Manual linting and formatting:**
```bash
# Run linter
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Type check
mypy src/

# Security check
bandit -r src/ -c pyproject.toml
```

### Run the Dashboard Locally

```bash
# Start dashboard
python scripts/start_dashboard.py

# Or manually:
PYTHONPATH=src uv run uvicorn ax_agent_studio.dashboard.backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 to verify it works.

### Run Tests (if available)

```bash
# Unit tests
python tests/test_message_parsing.py

# End-to-end tests
python tests/test_gemini_e2e.py
```

---

## How to Contribute

### Types of Contributions We Love

1. ** Bug Fixes** - Find and fix bugs, improve error handling
2. ** New Features** - Add new monitor types, tools, or integrations
3. ** Documentation** - Improve README, add tutorials, fix typos
4. ** Tests** - Add test coverage, improve test reliability
5. ** UI/UX** - Enhance dashboard design, improve user experience
6. ** Performance** - Optimize message processing, reduce latency
7. ** Examples** - Create example agents, demos, or integration guides

### Contribution Workflow

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # Or: fix/bug-description
   ```

2. **Make your changes**:
   - Follow existing code style (see [Style Guide](#style-guide))
   - Write clear commit messages
   - Add tests if applicable
   - Update documentation

3. **Test your changes**:
   ```bash
   # Run relevant monitors to test
   PYTHONPATH=src uv run python -m ax_agent_studio.monitors.echo_monitor test_agent

   # Run tests if available
   python tests/test_your_feature.py
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: Add your feature description"

   # Use conventional commits:
   # feat: New feature
   # fix: Bug fix
   # docs: Documentation changes
   # test: Adding tests
   # refactor: Code refactoring
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**:
   - Go to GitHub and create a PR from your fork to `ax-platform/ax-agent-studio`
   - Fill out the PR template with:
     - **Description** of changes
     - **Why** this change is needed
     - **Testing** performed
     - **Screenshots** (if UI changes)

---

## Contribution Guidelines

### Code Style

**Python:**
- Follow **PEP 8** style guide (enforced by Ruff)
- Use **Ruff** for linting and formatting (configured in `pyproject.toml`)
- Line length: **100 characters**
- Use **async/await** for I/O operations
- Add **type hints** where helpful (checked by mypy)
- Write **docstrings** for functions/classes
- Pre-commit hooks will automatically format and lint your code

**Example:**
```python
async def handle_message(msg: dict) -> str:
    """
    Process incoming message and return response.

    Args:
        msg: Message dictionary with 'sender', 'content', 'id'

    Returns:
        Response string to send back to sender
    """
    sender = msg.get("sender", "unknown")
    content = msg.get("content", "")
    return f"Echo: {content}"
```

**JavaScript (Dashboard):**
- Use **modern ES6+** syntax
- Prefer `const`/`let` over `var`
- Add comments for complex logic
- Keep functions small and focused

### Commit Messages

Use **conventional commits** format:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding/updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Maintenance tasks

**Examples:**
```
feat: Add Anthropic Claude support to langgraph monitor

Added Claude integration using langchain-anthropic.
Supports Claude Opus, Sonnet, and Haiku models.

Closes #123
```

```
fix: Prevent infinite loop in echo monitor

Added regex check to skip messages containing "Echo received"
to prevent self-replies.
```

### Pull Request Guidelines

**Before submitting:**
-  Code runs without errors
-  Pre-commit hooks pass (run `pre-commit run --all-files`)
-  CI/CD checks pass (linting, formatting, tests)
-  Tests pass (if applicable)
-  Documentation updated
-  No sensitive data (API keys, credentials) committed
-  Branch is up to date with `main`

**PR Description should include:**
- **What** changed
- **Why** it was needed
- **How** to test it
- **Screenshots** (for UI changes)
- **Related issues** (e.g., "Closes #123")

**Example PR:**
```markdown
## Description
Adds support for Anthropic Claude models in the LangGraph monitor.

## Why
Community requested Claude support. Claude Opus/Sonnet perform well on reasoning tasks.

## Changes
- Added `langchain-anthropic` dependency
- Created `get_anthropic_llm()` in provider utils
- Updated dashboard UI to show Claude models
- Added example config for Claude agent

## Testing
1. Start dashboard
2. Select "LangGraph Monitor"
3. Choose "Claude" provider
4. Select "claude-opus-4-5" model
5. Send test message → agent responds

## Screenshots
[Screenshot of Claude dropdown in dashboard]

Closes #123
```

---

## Specific Contribution Areas

### 1. Creating New Monitor Types

Want to create a custom monitor (e.g., RAG monitor, code executor)?

**Steps:**
1. Copy `src/ax_agent_studio/monitors/echo_monitor.py` as a template
2. Implement your `handle_message()` function
3. Add to dashboard: `dashboard/backend/config_loader.py`
4. Document in `README.md`

**Example monitors to build:**
- RAG monitor (query vector database)
- Code executor (run code snippets safely)
- Web scraper (fetch and summarize URLs)
- Translator (multi-language support)

### 2. Adding New LLM Providers

Currently supported: OpenAI, Anthropic, Google Gemini, AWS Bedrock, Ollama

**Want to add a new provider?** (e.g., Mistral, Cohere, local models)

1. Add dependency to `pyproject.toml`:
   ```bash
   uv add langchain-mistral
   ```
2. Create provider function in monitor (e.g., `get_mistral_llm()`)
3. Update dashboard UI: `dashboard/frontend/app.js`
4. Test and document

### 3. Improving the Dashboard

The dashboard is vanilla HTML/JS/CSS. Contributions welcome!

**Ideas:**
- Dark mode toggle
- Better log filtering/search
- Agent performance metrics
- Real-time message viewer
- Deployment group templates

**Files:**
- Frontend: `src/ax_agent_studio/dashboard/frontend/`
- Backend: `src/ax_agent_studio/dashboard/backend/main.py`

### 4. Writing Documentation

Documentation is crucial for adoption!

**Needed:**
- Tutorials for beginners
- Video walkthroughs
- Architecture diagrams
- Integration guides (Slack, Discord, webhooks)
- Best practices for production deployment

**Where:**
- README.md - Getting started and developer docs
- Examples in `examples/` folder (create it!)

### 5. Creating Example Agents

Help others learn by creating example agent configs!

**Ideas:**
- Customer support bot (with RAG)
- DevOps alert handler
- Social media monitor
- Code review assistant
- Meeting summarizer

**Structure:**
```
examples/
├── customer_support/
│   ├── agent_config.json
│   ├── system_prompt.txt
│   └── README.md (how to use)
```

---

## Community & Support

### Get Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/ax-platform/ax-agent-studio/issues)
- **Discussions**: [Ask questions, share ideas](https://github.com/ax-platform/ax-agent-studio/discussions)
- **Discord**: (Coming soon!)

### Stay Updated

- ⭐ **Star** this repo to get updates
-  **Watch** for new releases
-  Follow **aX Platform** on social media (links TBD)

---

## Recognition

Contributors will be recognized in:
- **README.md** contributors section
- **Release notes** for significant contributions
- **Hall of Fame** (coming soon!)

---

## Questions?

If you're unsure about anything:
1. Look at **existing code** for patterns
2. Ask in **GitHub Discussions**
3. Open a **draft PR** and ask for feedback

**We're here to help!** Don't be shy - all skill levels welcome.

---

## License

By contributing to aX Agent Studio, you agree that your contributions will be licensed under the **MIT License**.

---

**Thank you for making aX Agent Studio better! **

Let's build the future of agent orchestration together.
