#!/usr/bin/env python3
"""
new_skill.py — scaffold a skill directory.

    python .agents/skills/skill-writer/scripts/new_skill.py retrieval-regression

Creates the folder, a SKILL.md with the frontmatter filled in and the body left
as prompts, and empty reference/ and scripts/ directories. Writing the content
is your job; this just removes the boilerplate.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEMPLATE = """---
name: {name}
description: >
  Use when <list the situations that should trigger this, and the phrasings a
  user would actually type>. Describe moments, not contents.
---

# {title}

<One or two sentences: what this procedure is for and when it applies.>

## Steps

1. <first step>
2. <second step>

## Detail

<Anything long, occasional, or lookup-shaped goes in reference/ and is
referenced from here, so it costs nothing until it is needed.>

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| | | |

<Fill this in from what actually went wrong, not from what you imagine might.>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="kebab-case skill name")
    parser.add_argument("--root", default=".agents/skills")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.name):
        sys.exit(f"'{args.name}' is not kebab-case. Use letters, digits and hyphens.")

    base = Path(args.root) / args.name
    if base.exists():
        sys.exit(f"{base} already exists.")

    (base / "reference").mkdir(parents=True)
    (base / "scripts").mkdir()
    (base / "reference" / ".gitkeep").touch()
    (base / "scripts" / ".gitkeep").touch()

    title = args.name.replace("-", " ").capitalize()
    (base / "SKILL.md").write_text(
        TEMPLATE.format(name=args.name, title=title), encoding="utf-8"
    )

    print(f"Created {base}/")
    print(f"  SKILL.md      <- write this")
    print(f"  reference/    <- long or occasional detail")
    print(f"  scripts/      <- anything deterministic")
    print("\nWhen it is written, test it from a FRESH session using wording a real")
    print("user would choose. If it does not fire, fix the description.")


if __name__ == "__main__":
    main()
