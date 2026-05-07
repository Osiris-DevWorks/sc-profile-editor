"""
Discord Release Notification Script

Posts release announcements to Discord via webhook.
Usage: python scripts/discord_notify.py <version> <release_url>
Example: python scripts/discord_notify.py v0.4.0 https://github.com/Osiris-DevWorks/sc-profile-editor/releases/tag/v0.4.0
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

WEBHOOK_URL = os.getenv("DISCORD_RELEASE_WEBHOOK_URL")


def parse_changelog_for_version(version: str) -> dict:
    """Parse CHANGELOG.md to extract changes for the given version."""
    changelog_path = project_root / "docs" / "CHANGELOG.md"

    if not changelog_path.exists():
        return {"added": [], "changed": [], "fixed": []}

    with open(changelog_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the version section
    version_clean = version.lstrip("v")
    in_version_section = False
    current_category = None
    changes = {"added": [], "changed": [], "fixed": []}

    for line in lines:
        # Check if we're starting the version section
        if f"## [{version_clean}]" in line:
            in_version_section = True
            continue

        # Stop if we hit the next version section
        if in_version_section and line.startswith("## [") and version_clean not in line:
            break

        if in_version_section:
            # Check for category headers
            if line.startswith("### Added"):
                current_category = "added"
            elif line.startswith("### Changed"):
                current_category = "changed"
            elif line.startswith("### Fixed"):
                current_category = "fixed"
            elif line.startswith("### "):
                current_category = None  # Other categories we don't track
            # Add bullet points to current category
            elif current_category and line.strip().startswith("-"):
                # Clean up the line
                item = line.strip()[1:].strip()
                changes[current_category].append(item)

    return changes


def create_embed(version: str, release_url: str) -> dict:
    """Create a Discord embed for the release announcement."""
    changes = parse_changelog_for_version(version)

    # Build description with changes
    description_parts = [
        f"🎉 **New release available!**\n",
        f"[View on GitHub]({release_url})\n"
    ]

    # Add changes
    if changes["added"]:
        description_parts.append("\n**✨ Added**")
        for item in changes["added"][:3]:  # Limit to first 3 items
            description_parts.append(f"• {item}")
        if len(changes["added"]) > 3:
            description_parts.append(f"• ...and {len(changes['added']) - 3} more")

    if changes["changed"]:
        description_parts.append("\n**🔄 Changed**")
        for item in changes["changed"][:3]:
            description_parts.append(f"• {item}")
        if len(changes["changed"]) > 3:
            description_parts.append(f"• ...and {len(changes['changed']) - 3} more")

    if changes["fixed"]:
        description_parts.append("\n**🐛 Fixed**")
        for item in changes["fixed"][:3]:
            description_parts.append(f"• {item}")
        if len(changes["fixed"]) > 3:
            description_parts.append(f"• ...and {len(changes['fixed']) - 3} more")

    description_parts.append(f"\n📥 **[Download Now]({release_url})**")

    embed = {
        "title": f"SC Profile Editor {version}",
        "description": "\n".join(description_parts),
        "color": 0x00A8E8,  # Star Citizen blue
        "url": release_url,
        "footer": {
            "text": "SC Profile Editor"
        },
        "thumbnail": {
            "url": "https://raw.githubusercontent.com/Osiris-DevWorks/sc-profile-editor/main/assets/icon.png"
        }
    }

    return embed


def send_discord_notification(version: str, release_url: str) -> bool:
    """Send release notification to Discord via webhook."""
    if not WEBHOOK_URL:
        print("Warning: DISCORD_RELEASE_WEBHOOK_URL not set in .env file")
        print("Skipping Discord notification.")
        return False

    embed = create_embed(version, release_url)

    payload = {
        "content": "@everyone",
        "embeds": [embed],
        "username": "SC Profile Editor Releases",
        "allowed_mentions": {
            "parse": ["everyone"]
        }
    }

    data = json.dumps(payload).encode('utf-8')

    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'SC-Profile-Viewer-Release-Bot/1.0'
            }
        )

        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"[SUCCESS] Posted release {version} to Discord!")
                return True
            else:
                print(f"[WARNING] Unexpected response status: {response.status}")
                return False

    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to post to Discord: HTTP {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[ERROR] Error posting to Discord: {e}")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/discord_notify.py <version> <release_url>")
        print("Example: python scripts/discord_notify.py v0.4.0 https://github.com/Osiris-DevWorks/sc-profile-editor/releases/tag/v0.4.0")
        sys.exit(1)

    version = sys.argv[1]
    release_url = sys.argv[2]

    print(f"Posting release notification for {version}...")
    success = send_discord_notification(version, release_url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
