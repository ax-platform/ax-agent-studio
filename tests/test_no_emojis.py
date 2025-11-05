#!/usr/bin/env python3
"""
Test to ensure no emoji characters exist in source files.

Emojis can cause encoding issues on Windows systems. This test ensures
the codebase remains emoji-free for cross-platform compatibility.

Run with: pytest tests/test_no_emojis.py
"""

import os
import re
from pathlib import Path

import pytest

# Emoji pattern - covers emoji ranges, variation selectors, and joiners
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map symbols
    "\U0001f700-\U0001f77f"  # alchemical symbols
    "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
    "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
    "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
    "\U0001fa00-\U0001fa6f"  # Chess Symbols
    "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000027bf"  # Miscellaneous Symbols
    "\U0001f1e6-\U0001f1ff"  # flags
    "\ufe0e\ufe0f"  # variation selectors (text/emoji style)
    "\u200d"  # zero-width joiner (combines emoji sequences)
    "\u200b\u200c"  # zero-width space, zero-width non-joiner
    "]+",
    flags=re.UNICODE,
)

# File extensions to check
EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".json", ".sh", ".bat", ".txt"}

# Directories to skip
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "data",
    "logs",
    "dist",
    "build",
    ".eggs",
    "htmlcov",
    ".pytest_cache",
    ".tox",
    "agent_files",
    "agent_memory",
    "uv.lock",
}

# Files to skip (allowed to have emojis)
SKIP_FILES = {
    "CHANGELOG.md",  # Historical changelog may contain emojis
    "docs/HANDOFF",  # Internal docs (gitignored)
    "docs/SESSION",  # Internal docs (gitignored)
    ".claude/",  # Claude-specific files (gitignored)
    "configs/prompts/_base.yaml",  # System prompts showing emoji reaction examples
}


def should_skip_file(filepath: str) -> bool:
    """Check if file should be skipped."""
    for skip_pattern in SKIP_FILES:
        if skip_pattern in filepath:
            return True
    return False


def find_files_with_emojis():
    """Find all files containing emojis."""
    files_with_emojis = []
    project_root = Path(__file__).parent.parent

    for root, dirs, files in os.walk(project_root):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if Path(file).suffix in EXTENSIONS:
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, project_root)

                # Skip allowed files
                if should_skip_file(relative_path):
                    continue

                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        emoji_matches = EMOJI_PATTERN.findall(content)
                        if emoji_matches:
                            # Find line numbers with emojis
                            lines_with_emojis = []
                            for i, line in enumerate(content.split("\n"), 1):
                                if EMOJI_PATTERN.search(line):
                                    # Show emoji and context
                                    preview = line[:80] + "..." if len(line) > 80 else line
                                    lines_with_emojis.append(f"    Line {i}: {preview}")

                            files_with_emojis.append(
                                {
                                    "path": relative_path,
                                    "count": len(emoji_matches),
                                    "lines": lines_with_emojis[:5],  # Show first 5 occurrences
                                }
                            )
                except Exception:
                    # Skip files that can't be read
                    pass

    return files_with_emojis


def test_no_emojis_in_source_files():
    """Test that source files contain no emoji characters."""
    files_with_emojis = find_files_with_emojis()

    if files_with_emojis:
        error_message = [
            "\nEmoji characters found in source files!",
            "Emojis cause encoding issues on Windows. Please remove them.",
            "",
            "Files with emojis:",
        ]

        for file_info in files_with_emojis:
            error_message.append(f"\n  {file_info['path']} ({file_info['count']} emojis)")
            error_message.extend(file_info["lines"])

        error_message.extend(
            [
                "",
                "To fix this:",
                "  python scripts/remove_emojis.py --apply",
                "",
                "Or manually remove emojis from the files listed above.",
            ]
        )

        pytest.fail("\n".join(error_message))


if __name__ == "__main__":
    # Allow running directly for quick checks
    files = find_files_with_emojis()
    if files:
        print(f"Found {len(files)} files with emojis:")
        for f in files:
            print(f"  {f['path']}: {f['count']} emojis")
    else:
        print("No emojis found! Codebase is clean.")
