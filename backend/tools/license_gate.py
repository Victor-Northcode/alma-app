#!/usr/bin/env python3
"""Fail the build if a copyleft dependency appears — including transitively.

The spec makes this P0 for a reason: libephemeris shipped pre-releases whose
PyPI metadata said Apache-2.0 and later corrected to AGPL-3.0-only. A licence
is not a fact you check once at selection time; it is a property of a version,
and it moves. This gate runs on every build and re-reads what is actually
installed.

Exit codes: 0 clean, 1 a forbidden licence is present, 2 the gate could not
determine a licence (treated as a failure — unknown is not the same as fine).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

# Permissive licences the spec allows outright.
ALLOWED = {
    "mit", "mit-0", "mit license", "the mit license (mit)", "expat",
    "bsd", "bsd license", "bsd-2-clause", "bsd-3-clause", "bsd 3-clause",
    "apache", "apache-2.0", "apache 2.0", "apache software license",
    "isc", "isc license (iscl)",
    "psf", "psf-2.0", "python software foundation license",
    "zlib", "0bsd", "cc0-1.0", "unlicense", "public domain",
}

# Anything in this family makes the service's own source disclosable.
# Both spellings are needed: metadata carries the abbreviation ("AGPL-3.0")
# about as often as the expanded name ("GNU Affero General Public License"),
# and the expanded form contains no "gpl" substring to match on.
FORBIDDEN_MARKERS = (
    "gpl", "agpl", "lgpl", "sspl", "cc-by-sa", "osl", "epl", "cddl",
    "general public license", "affero", "server side public license",
    "eclipse public license", "common development and distribution",
)

# Packages whose licence is not on the allowlist but is understood and accepted,
# each with the reason. Anything not listed here and not allowed fails the gate.
EXCEPTIONS: dict[str, str] = {
    "certifi": (
        "MPL-2.0. File-level copyleft: obligations attach only to modifications of "
        "certifi's own files, which we do not make. It does not reach our source."
    ),
}

# Never allowed regardless of what their metadata claims, because the spec bans
# them by name. Guards against a metadata error re-admitting them silently.
BANNED_PACKAGES = {"pyswisseph", "swisseph", "libephemeris", "kerykeion", "rebound", "assist"}

# Our own distributions — first-party code, not a supply-chain input.
FIRST_PARTY = {"alma-backend", "alma"}


def _normalise(licence: str) -> str:
    """Reduce a metadata licence field to something classifiable.

    Some packages put an SPDX id here; others paste the entire licence text.
    The identifying part is always the first line, so take that and drop a
    trailing copyright notice if the name and notice share a line.
    """
    first = licence.strip().splitlines()[0] if licence.strip() else ""
    return re.split(r"\s+Copyright\b", first)[0].strip()


def _installed() -> list[dict[str, str]]:
    out = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json", "--with-urls"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print("license gate: pip-licenses failed to run", file=sys.stderr)
        print(out.stderr, file=sys.stderr)
        sys.exit(2)
    return json.loads(out.stdout)


def _classify(name: str, licence: str) -> tuple[str, str]:
    """Return (verdict, reason). Verdict is 'ok', 'forbidden' or 'unknown'."""
    key = name.strip().lower()
    if key in BANNED_PACKAGES:
        return "forbidden", "banned by name in the specification"
    if key in FIRST_PARTY:
        return "skip", "first-party package"

    text = _normalise(licence).lower()
    if not text or text in {"unknown", "unknown license"}:
        return "unknown", "no licence declared in package metadata"

    # A compound expression is fine only when *every* term is acceptable.
    terms = [
        t.strip(" ()")
        for t in text.replace(" and ", ";").replace(" or ", ";").replace(",", ";").split(";")
        if t.strip(" ()")
    ]

    for term in terms:
        if any(marker in term for marker in FORBIDDEN_MARKERS):
            # "GPL" appears inside "LGPL"; both are forbidden here anyway.
            return "forbidden", f"copyleft term: {term}"

    if key in EXCEPTIONS:
        return "ok", f"documented exception — {EXCEPTIONS[key]}"

    if all(any(term.startswith(a) or a in term for a in ALLOWED) for term in terms):
        return "ok", ""

    return "unknown", f"licence not on the allowlist: {licence}"


def main() -> int:
    packages = _installed()
    forbidden: list[tuple[str, str, str]] = []
    unknown: list[tuple[str, str, str]] = []
    exceptions: list[tuple[str, str]] = []

    for pkg in packages:
        name = pkg.get("Name", "")
        licence = pkg.get("License", "")
        verdict, reason = _classify(name, licence)
        if verdict == "skip":
            continue
        if verdict == "forbidden":
            forbidden.append((name, licence, reason))
        elif verdict == "unknown":
            unknown.append((name, _normalise(licence), reason))
        elif reason:
            exceptions.append((name, licence))

    print(f"license gate: {len(packages)} packages checked")
    for name, licence in exceptions:
        print(f"  accepted by exception: {name} ({licence})")

    if forbidden:
        print("\nFORBIDDEN — a copyleft dependency would force disclosure of our source:")
        for name, licence, reason in forbidden:
            print(f"  {name}: {_normalise(licence)}  [{reason}]")
    if unknown:
        print("\nUNDETERMINED — resolve each before shipping:")
        for name, licence, reason in unknown:
            print(f"  {name}: {licence or '(none)'}  [{reason}]")

    if forbidden:
        return 1
    if unknown:
        return 2
    print("clean: no GPL / AGPL / LGPL, direct or transitive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
