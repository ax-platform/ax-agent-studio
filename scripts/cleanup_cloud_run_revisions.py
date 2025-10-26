#!/usr/bin/env python3
"""
Cloud Run Revision Cleanup Utility

Cleans up old Cloud Run revisions, keeping only the N most recent ones.
Saves storage costs by deleting unused container images.

Usage:
    python scripts/cleanup_cloud_run_revisions.py --service SERVICE_NAME --region REGION [options]

Examples:
    # Dry run (preview what will be deleted)
    python scripts/cleanup_cloud_run_revisions.py \\
        --service pax-platform-frontend \\
        --region us-central1 \\
        --keep 5 \\
        --dry-run

    # Actually delete old revisions
    python scripts/cleanup_cloud_run_revisions.py \\
        --service pax-platform-frontend \\
        --region us-central1 \\
        --keep 5

    # Clean up multiple services
    python scripts/cleanup_cloud_run_revisions.py \\
        --service pax-platform-frontend \\
        --service pax-platform-backend \\
        --region us-central1 \\
        --keep 3
"""

import subprocess
import sys
import argparse
from typing import List, Tuple
from datetime import datetime


def run_command(cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr"""
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def check_gcloud_installed() -> bool:
    """Check if gcloud CLI is installed"""
    code, _, _ = run_command(["which", "gcloud"])
    return code == 0


def list_revisions(service: str, region: str) -> List[dict]:
    """List all revisions for a Cloud Run service"""
    cmd = [
        "gcloud", "run", "revisions", "list",
        f"--service={service}",
        f"--region={region}",
        "--format=json"
    ]

    code, stdout, stderr = run_command(cmd)

    if code != 0:
        print(f"❌ Error listing revisions: {stderr}", file=sys.stderr)
        return []

    import json
    try:
        revisions = json.loads(stdout)
        # Sort by creation time (newest first)
        revisions.sort(key=lambda r: r.get('metadata', {}).get('creationTimestamp', ''), reverse=True)
        return revisions
    except json.JSONDecodeError:
        print(f"❌ Error parsing gcloud output", file=sys.stderr)
        return []


def get_revision_traffic(revision: dict) -> int:
    """Get traffic percentage for a revision"""
    status = revision.get('status', {})
    traffic = status.get('traffic', [])
    if traffic and len(traffic) > 0:
        return traffic[0].get('percent', 0)
    return 0


def delete_revision(service: str, revision_name: str, region: str, dry_run: bool = False) -> bool:
    """Delete a Cloud Run revision"""
    if dry_run:
        print(f"  [DRY RUN] Would delete: {revision_name}")
        return True

    cmd = [
        "gcloud", "run", "revisions", "delete",
        revision_name,
        f"--region={region}",
        "--quiet"
    ]

    code, _, stderr = run_command(cmd, capture_output=True)

    if code != 0:
        print(f"  ❌ Error deleting {revision_name}: {stderr}", file=sys.stderr)
        return False

    print(f"  ✅ Deleted: {revision_name}")
    return True


def cleanup_service(service: str, region: str, keep: int, dry_run: bool = False) -> Tuple[int, int]:
    """Clean up old revisions for a service"""
    print(f"\n🔍 Checking service: {service} (region: {region})")

    revisions = list_revisions(service, region)

    if not revisions:
        print(f"  ℹ️  No revisions found or error occurred")
        return 0, 0

    print(f"  📊 Found {len(revisions)} total revisions")

    # Separate active (with traffic) and inactive revisions
    active_revisions = [r for r in revisions if get_revision_traffic(r) > 0]
    inactive_revisions = [r for r in revisions if get_revision_traffic(r) == 0]

    if active_revisions:
        print(f"  🟢 {len(active_revisions)} active revision(s) with traffic (will NOT delete)")
        for rev in active_revisions:
            name = rev['metadata']['name']
            traffic = get_revision_traffic(rev)
            print(f"    - {name} ({traffic}% traffic)")

    # Keep the N most recent revisions (including active ones)
    revisions_to_keep = revisions[:keep]
    revisions_to_delete = [r for r in revisions[keep:] if get_revision_traffic(r) == 0]

    keep_names = {r['metadata']['name'] for r in revisions_to_keep}

    print(f"  ✅ Keeping {len(revisions_to_keep)} most recent revision(s):")
    for rev in revisions_to_keep:
        name = rev['metadata']['name']
        created = rev['metadata'].get('creationTimestamp', 'unknown')
        traffic = get_revision_traffic(rev)
        traffic_str = f" ({traffic}% traffic)" if traffic > 0 else ""
        print(f"    - {name} (created: {created}){traffic_str}")

    if not revisions_to_delete:
        print(f"  ℹ️  No old revisions to delete")
        return 0, 0

    print(f"\n  🗑️  Will delete {len(revisions_to_delete)} old revision(s):")
    for rev in revisions_to_delete:
        name = rev['metadata']['name']
        created = rev['metadata'].get('creationTimestamp', 'unknown')
        print(f"    - {name} (created: {created})")

    if dry_run:
        print(f"\n  [DRY RUN] Would delete {len(revisions_to_delete)} revisions")
        return len(revisions_to_delete), 0

    # Confirm before deleting
    print(f"\n  ⚠️  About to delete {len(revisions_to_delete)} revisions")
    confirm = input("  Continue? [y/N]: ").strip().lower()

    if confirm != 'y':
        print("  ❌ Cancelled")
        return 0, 0

    # Delete old revisions
    deleted_count = 0
    failed_count = 0

    print(f"\n  🗑️  Deleting old revisions...")
    for rev in revisions_to_delete:
        name = rev['metadata']['name']
        success = delete_revision(service, name, region, dry_run=False)
        if success:
            deleted_count += 1
        else:
            failed_count += 1

    return deleted_count, failed_count


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old Cloud Run revisions to save storage costs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--service",
        action="append",
        required=True,
        help="Cloud Run service name(s). Can specify multiple times."
    )

    parser.add_argument(
        "--region",
        required=True,
        help="GCP region (e.g., us-central1)"
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of most recent revisions to keep (default: 5)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    # Check gcloud is installed
    if not check_gcloud_installed():
        print("❌ Error: gcloud CLI is not installed", file=sys.stderr)
        print("Install from: https://cloud.google.com/sdk/docs/install", file=sys.stderr)
        sys.exit(1)

    print("🧹 Cloud Run Revision Cleanup Utility")
    print(f"Settings:")
    print(f"  - Keep: {args.keep} most recent revisions")
    print(f"  - Region: {args.region}")
    print(f"  - Dry run: {args.dry_run}")

    # Process each service
    total_deleted = 0
    total_failed = 0

    for service in args.service:
        deleted, failed = cleanup_service(
            service=service,
            region=args.region,
            keep=args.keep,
            dry_run=args.dry_run
        )
        total_deleted += deleted
        total_failed += failed

    # Summary
    print("\n" + "="*60)
    print("📊 Summary:")
    print(f"  - Services processed: {len(args.service)}")
    print(f"  - Revisions deleted: {total_deleted}")
    if total_failed > 0:
        print(f"  - Failed deletions: {total_failed}")

    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to actually delete.")
    else:
        print(f"\n✅ Cleanup complete!")


if __name__ == "__main__":
    main()
