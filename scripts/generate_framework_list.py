#!/usr/bin/env python3
"""
Generate framework list markdown from configs/frameworks.yaml

This ensures DRY - frameworks are defined once in YAML and auto-generated
everywhere else. Run this script to regenerate FRAMEWORKS.md whenever
frameworks.yaml changes.

Usage:
    python scripts/generate_framework_list.py
"""

import yaml
from pathlib import Path


def generate_framework_list():
    """Generate markdown framework list from YAML"""

    # Load frameworks config
    config_path = Path(__file__).parent.parent / "configs" / "frameworks.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    frameworks = config["frameworks"]

    # Generate markdown
    lines = []
    lines.append("<!-- AUTO-GENERATED from configs/frameworks.yaml -->")
    lines.append("<!-- Run scripts/generate_framework_list.py to update -->")
    lines.append("")

    # Sort frameworks: recommended first, then alphabetically
    sorted_frameworks = sorted(
        frameworks.items(),
        key=lambda x: (not x[1].get("recommended", False), x[1]["name"])
    )

    for fw_id, fw in sorted_frameworks:
        emoji = fw.get("emoji", "")
        name = fw["name"]
        desc = fw.get("description", "")
        best_for = fw.get("best_for", "")
        recommended = fw.get("recommended", False)

        # Build line
        parts = []
        parts.append(f"- **{name}**")

        if recommended:
            parts.append("⭐ (Recommended)")

        if desc:
            parts.append(f": {desc}")

        if best_for:
            parts.append(f" - {best_for}")

        lines.append("".join(parts))

    return "\n".join(lines)


def main():
    """Generate and save framework list"""
    output_path = Path(__file__).parent.parent / "FRAMEWORKS.md"

    content = generate_framework_list()

    with open(output_path, "w") as f:
        f.write(content)
        f.write("\n")

    print(f"✅ Generated {output_path}")
    print(f"   {len(content.splitlines())} lines")
    print("\n" + "="*60)
    print("Preview:")
    print("="*60)
    print(content)


if __name__ == "__main__":
    main()
