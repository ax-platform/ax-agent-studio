#!/usr/bin/env python3
"""
Remove emojis from all source files for Windows compatibility.

Emojis can cause encoding issues on Windows systems, especially in terminals
and some text editors. This script removes all emoji characters from source files.

Usage:
    python scripts/remove_emojis.py          # Dry run (shows what would change)
    python scripts/remove_emojis.py --apply  # Actually modify files
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Emoji pattern - covers emoji ranges, variation selectors, and joiners
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000027BF"  # Miscellaneous Symbols
    "\U0001F1E6-\U0001F1FF"  # flags
    "\uFE0E\uFE0F"           # variation selectors (text/emoji style)
    "\u200D"                 # zero-width joiner (combines emoji sequences)
    "\u200B\u200C"           # zero-width space, zero-width non-joiner
    "]+",
    flags=re.UNICODE
)

# File extensions to process
EXTENSIONS = {'.py', '.md', '.yaml', '.yml', '.json', '.sh', '.bat', '.txt'}

# Directories to skip
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'data',
             'logs', 'dist', 'build', '.eggs', 'htmlcov', '.pytest_cache',
             '.tox', 'agent_files', 'agent_memory'}

# Files to skip (allowed to have emojis)
SKIP_FILES = {
    'configs/prompts/_base.yaml',  # System prompts showing emoji reaction examples
}


def should_skip_file(filepath: str) -> bool:
    """Check if file should be skipped."""
    for skip_pattern in SKIP_FILES:
        if skip_pattern in filepath:
            return True
    return False


def find_files_with_emojis(root_dir: str = '.') -> List[Tuple[str, int]]:
    """Find all files containing emojis.

    Returns:
        List of (filepath, emoji_count) tuples
    """
    files_with_emojis = []

    for root, dirs, files in os.walk(root_dir):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if Path(file).suffix in EXTENSIONS:
                filepath = os.path.join(root, file)

                # Skip allowed files
                if should_skip_file(filepath):
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        emoji_matches = EMOJI_PATTERN.findall(content)
                        if emoji_matches:
                            files_with_emojis.append((filepath, len(emoji_matches)))
                except Exception as e:
                    print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    return sorted(files_with_emojis, key=lambda x: x[1], reverse=True)


def remove_emojis_from_file(filepath: str, dry_run: bool = True) -> bool:
    """Remove emojis from a file.

    Args:
        filepath: Path to file
        dry_run: If True, don't actually modify the file

    Returns:
        True if file was modified (or would be modified in dry run)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()

        cleaned_content = EMOJI_PATTERN.sub('', original_content)

        if original_content != cleaned_content:
            if not dry_run:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    apply_changes = '--apply' in sys.argv or '-a' in sys.argv

    print("=" * 70)
    print("EMOJI REMOVAL SCRIPT")
    print("=" * 70)
    print()

    if apply_changes:
        print("MODE: APPLY CHANGES (files will be modified)")
    else:
        print("MODE: DRY RUN (no files will be modified)")
        print("Run with --apply to actually modify files")
    print()

    # Find all files with emojis
    print("Scanning for emojis...")
    files_with_emojis = find_files_with_emojis()

    if not files_with_emojis:
        print("No emojis found! Codebase is clean.")
        return 0

    print(f"Found {len(files_with_emojis)} files with emojis")
    print()

    # Process files
    modified_count = 0
    total_emojis = 0

    for filepath, emoji_count in files_with_emojis:
        total_emojis += emoji_count
        if remove_emojis_from_file(filepath, dry_run=not apply_changes):
            modified_count += 1
            status = "CLEANED" if apply_changes else "WOULD CLEAN"
            print(f"[{status}] {filepath} ({emoji_count} emojis)")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files processed: {len(files_with_emojis)}")
    print(f"Files modified: {modified_count}")
    print(f"Total emojis removed: {total_emojis}")

    if not apply_changes:
        print()
        print("This was a DRY RUN. No files were modified.")
        print("Run with --apply to actually remove emojis.")
        return 1
    else:
        print()
        print("All emojis have been removed!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
