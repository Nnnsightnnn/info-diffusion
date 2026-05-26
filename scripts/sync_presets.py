#!/usr/bin/env python3
"""Sync presets.py → dashboard.html JS PRESETS block.

This is the build step that keeps the static web app's preset list in lockstep
with the Python source of truth. Run from anywhere — paths are resolved
relative to this file's location.

Replaces everything between
    // PRESETS_BEGIN
    // PRESETS_END
in dashboard.html with a freshly-generated `const PRESETS = { ... };` block.

Called by .github/workflows/pages.yml before the Pages deploy. Also safe to
run locally if you want the working tree to reflect a presets.py edit before
committing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Make sure we can `from presets import PRESETS` regardless of cwd
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from presets import PRESETS  # noqa: E402

DASHBOARD = REPO_ROOT / "docs" / "dashboard.html"
MARKER_RE = re.compile(r"// PRESETS_BEGIN.*?// PRESETS_END", re.DOTALL)


def build_js_block() -> str:
    lines = ["// PRESETS_BEGIN", "const PRESETS = {"]
    for p in PRESETS:
        cfg = {
            "seed_viewers":       p.seed_viewers,
            "population_size":    p.population_size,
            "conversation_rate":  p.conversation_rate,
            "spread_probability": p.spread_probability,
            "recovery_rate":      p.recovery_rate,
        }
        # ensure_ascii=False keeps emoji as real Unicode (not \uXXXX), which
        # also dodges re.sub interpreting the \u as a regex backreference.
        lines.append(
            f"  {json.dumps(p.display, ensure_ascii=False)}: "
            f"{json.dumps(cfg, ensure_ascii=False)},"
        )
    lines.append("};")
    lines.append("// PRESETS_END")
    return "\n".join(lines)


def main() -> int:
    if not DASHBOARD.exists():
        print(f"ERROR: {DASHBOARD} not found", file=sys.stderr)
        return 1

    html = DASHBOARD.read_text()
    new_block = build_js_block()
    # Use a lambda so re.sub treats `new_block` as a literal — otherwise any
    # backslash sequence in the replacement (e.g. \uXXXX) gets interpreted.
    new_html, n_subs = MARKER_RE.subn(lambda _m: new_block, html)

    if n_subs == 0:
        print(
            "ERROR: PRESETS_BEGIN / PRESETS_END markers not found in "
            f"{DASHBOARD.name}. Did someone edit the block by hand?",
            file=sys.stderr,
        )
        return 2

    if new_html == html:
        print(f"{DASHBOARD.name} already in sync with presets.py "
              f"({len(PRESETS)} presets) — no changes.")
        return 0

    DASHBOARD.write_text(new_html)
    print(f"Synced {len(PRESETS)} presets from presets.py → {DASHBOARD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
