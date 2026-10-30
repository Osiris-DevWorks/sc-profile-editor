"""
Extract one version's section from docs/CHANGELOG.md.

Usage:
    python scripts/release_notes.py v0.10.2            # print to stdout
    python scripts/release_notes.py 0.10.2 notes.md    # write to a file

Used by .github/workflows/release.yml to build the GitHub Release body, so a
release's notes are the CHANGELOG section for that version, nothing else to
maintain. Exits non-zero when the section is missing so the workflow fails
loudly instead of publishing an empty release.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "docs" / "CHANGELOG.md"


def section_for(version: str, text: str) -> str:
    version = version.lstrip("v").strip()
    header = re.compile(rf"^## \[{re.escape(version)}\]")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if header.match(line)), None)
    if start is None:
        return ""
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    return "\n".join(lines[start + 1:end]).strip() + "\n"


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    notes = section_for(sys.argv[1], CHANGELOG.read_text(encoding="utf-8"))
    if not notes.strip():
        print(f"No '## [{sys.argv[1].lstrip('v')}]' section in {CHANGELOG}", file=sys.stderr)
        return 1
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
