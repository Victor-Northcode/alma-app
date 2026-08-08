"""The licence gate is a guard, so it needs its own guard.

A gate that has never been shown to reject anything is indistinguishable from
a gate that always passes. These tests feed it the exact shapes that matter:
the AGPL packages the spec bans by name, a transitive copyleft dependency, and
the metadata quirks that made the real run noisy (full licence text pasted
into the field, our own package having no licence at all).
"""

from __future__ import annotations

import pytest

from tools.license_gate import _classify, _normalise


@pytest.mark.parametrize(
    "name,licence",
    [
        ("libephemeris", "AGPL-3.0-only"),
        # The exact trap from the spec: metadata claiming a permissive licence
        # on a package that is banned by name. Name wins.
        ("libephemeris", "Apache-2.0"),
        ("pyswisseph", "AGPL-3.0"),
        ("kerykeion", "AGPL-3.0"),
        ("rebound", "GPL-3.0-or-later"),
    ],
)
def test_named_bans_are_refused_whatever_the_metadata_says(name, licence):
    verdict, reason = _classify(name, licence)
    assert verdict == "forbidden", f"{name} slipped through as {verdict}"
    assert reason


@pytest.mark.parametrize(
    "licence",
    ["GPL-3.0", "AGPL-3.0-only", "LGPL-2.1", "GNU General Public License v3", "SSPL-1.0"],
)
def test_copyleft_is_refused_for_any_package(licence):
    verdict, _ = _classify("some-transitive-dep", licence)
    assert verdict == "forbidden"


@pytest.mark.parametrize(
    "licence",
    ["MIT", "BSD-3-Clause", "Apache-2.0", "ISC", "MIT AND PSF-2.0", "Apache-2.0 OR BSD-2-Clause"],
)
def test_permissive_licences_pass(licence):
    verdict, _ = _classify("some-dep", licence)
    assert verdict == "ok"


def test_a_compound_licence_fails_if_any_term_is_copyleft():
    """'MIT OR GPL-3.0' still lets a GPL term reach us — refuse it."""
    verdict, _ = _classify("dual-licensed-dep", "MIT OR GPL-3.0")
    assert verdict == "forbidden"


def test_missing_licence_is_undetermined_not_allowed():
    """Silence is not consent: an undeclared licence fails the build."""
    verdict, _ = _classify("mystery-dep", "")
    assert verdict == "unknown"
    assert _classify("mystery-dep", "UNKNOWN")[0] == "unknown"


def test_full_licence_text_in_metadata_is_still_classified():
    """timezonefinder pastes the whole MIT text into the licence field."""
    pasted = (
        "The MIT License (MIT)\n\nCopyright (c) 2016 Jannik Michelfeit\n\n"
        "Permission is hereby granted, free of charge, to any person..."
    )
    assert _normalise(pasted) == "The MIT License (MIT)"
    assert _classify("timezonefinder", pasted)[0] == "ok"


def test_first_party_package_is_skipped():
    """Our own code is not a supply-chain input to audit."""
    assert _classify("alma-backend", "UNKNOWN")[0] == "skip"


def test_documented_exception_passes_with_its_reason():
    verdict, reason = _classify("certifi", "Mozilla Public License 2.0 (MPL 2.0)")
    assert verdict == "ok"
    assert "MPL-2.0" in reason


def test_an_undocumented_non_allowlisted_licence_does_not_pass():
    """MPL is accepted for certifi by name — not for anything else by default."""
    assert _classify("some-other-dep", "Mozilla Public License 2.0 (MPL 2.0)")[0] == "unknown"
