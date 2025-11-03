"""
Framework Validator

Validates framework registry at startup to catch configuration issues early.
Ensures all frameworks have required components before allowing deployment.
"""

import importlib
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


def validate_frameworks(base_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate all frameworks have required components.

    Returns:
        (success: bool, errors: List[str])
    """
    frameworks_file = base_dir / "configs" / "frameworks.yaml"

    if not frameworks_file.exists():
        return False, [f"Framework registry not found: {frameworks_file}"]

    # Load frameworks
    with open(frameworks_file) as f:
        data = yaml.safe_load(f)

    if not data or "frameworks" not in data:
        return False, ["Framework registry missing 'frameworks' key"]

    frameworks = data["frameworks"]
    errors = []
    warnings = []

    print(f"\n🔍 Validating {len(frameworks)} framework(s)...")

    for framework_id, config in frameworks.items():
        print(f"\n   Checking {framework_id}...")

        # Check required fields
        required_fields = ["name", "emoji", "requires_provider", "requires_model"]
        for field in required_fields:
            if field not in config:
                errors.append(
                    f"Framework '{framework_id}': Missing required field '{field}'"
                )

        # Check provider logic
        if not config.get("requires_provider", True):
            # If provider not required, must have implicit provider
            if "provider" not in config:
                errors.append(
                    f"Framework '{framework_id}': requires_provider=false but no 'provider' specified"
                )

        # Check default model if model required
        if config.get("requires_model") and "default_model" not in config:
            warnings.append(
                f"Framework '{framework_id}': requires_model=true but no 'default_model' specified"
            )

        # Try to detect monitor module (best effort)
        # We check common patterns since monitor path isn't in registry yet
        monitor_module_patterns = [
            f"ax_agent_studio.monitors.{framework_id}_monitor",
            f"ax_agent_studio.monitors.{framework_id}",
        ]

        monitor_found = False
        for module_path in monitor_module_patterns:
            try:
                importlib.import_module(module_path)
                print(f"      ✅ Monitor module found: {module_path}")
                monitor_found = True
                break
            except ImportError:
                continue

        if not monitor_found:
            # This is a warning, not error, since monitor path isn't in registry yet
            warnings.append(
                f"Framework '{framework_id}': Could not find monitor module (tried {monitor_module_patterns})"
            )

        print(f"      ✅ {framework_id} validated")

    # Print summary
    print(f"\n{'=' * 60}")
    if errors:
        print(f"❌ Framework validation FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"   • {err}")
    else:
        print(f"✅ All {len(frameworks)} frameworks validated successfully")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for warn in warnings:
            print(f"   • {warn}")

    print(f"{'=' * 60}\n")

    return len(errors) == 0, errors


def get_framework_monitor_types(base_dir: Path) -> List[str]:
    """
    Get list of valid monitor types from framework registry.

    This can be used for dynamic type validation instead of hardcoded Literals.
    """
    frameworks_file = base_dir / "configs" / "frameworks.yaml"

    if not frameworks_file.exists():
        return []

    with open(frameworks_file) as f:
        data = yaml.safe_load(f)

    if not data or "frameworks" not in data:
        return []

    return list(data["frameworks"].keys())


def should_show_provider(framework_id: str, base_dir: Path) -> bool:
    """
    Determine if provider should be shown for a framework type.

    This can replace hardcoded logic in frontend/backend.
    """
    frameworks_file = base_dir / "configs" / "frameworks.yaml"

    if not frameworks_file.exists():
        return True  # Default to showing provider if registry not found

    with open(frameworks_file) as f:
        data = yaml.safe_load(f)

    if not data or "frameworks" not in data:
        return True

    framework = data["frameworks"].get(framework_id)
    if not framework:
        return True

    # Show provider if framework requires it (i.e., not implicit)
    return framework.get("requires_provider", True)


if __name__ == "__main__":
    # Test validation
    from pathlib import Path

    base_dir = Path(__file__).parent.parent.parent
    success, errors = validate_frameworks(base_dir)

    if success:
        print("✅ Framework validation passed")

        # Test helper functions
        monitor_types = get_framework_monitor_types(base_dir)
        print(f"\nValid monitor types: {monitor_types}")

        for mt in monitor_types:
            show_provider = should_show_provider(mt, base_dir)
            print(f"  {mt}: show_provider={show_provider}")
    else:
        print("❌ Framework validation failed")
        for err in errors:
            print(f"  {err}")
