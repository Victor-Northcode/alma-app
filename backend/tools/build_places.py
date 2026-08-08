"""Build the bundled place index from the GeoNames dump.

Run once when the gazetteer needs refreshing; the result is committed as
`data/places.sqlite` so the service has no network dependency and no runtime
geocoding bill.

    python tools/build_places.py --source /path/to/geonames

Expects `cities5000.txt`, `admin1CodesASCII.txt` and `countryInfo.txt` from
https://download.geonames.org/export/dump/ .

GeoNames data is CC BY 4.0. That is a licence on the *data*, not on our
source, and it costs us an attribution line — which is in the README and in
`data/ATTRIBUTION.md`. The engine's licence gate covers Python packages; this
note is here because a data licence will not show up there.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import unicodedata
from pathlib import Path

#: Alternate names are what let someone type "Milano" or "Милан" and find
#: Milan. A big city can carry three hundred spellings; after accent-folding
#: many collapse together, so we deduplicate first and only then cap. The cap
#: is generous because the failure mode is silent — Tokyo's Japanese spelling
#: sat past position 40 and the city was simply unfindable in its own
#: language.
MAX_ALTERNATES = 200


def fold(text: str) -> str:
    """Strip accents so "Zürich" and "Zurich" reach the same index entry."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _load_admin1(path: Path) -> dict[str, str]:
    table: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            table[parts[0]] = parts[1]
    return table


def _load_countries(path: Path) -> dict[str, str]:
    table: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 5:
            table[parts[0]] = parts[4]
    return table


def build(source: Path, target: Path) -> int:
    admin1 = _load_admin1(source / "admin1CodesASCII.txt")
    countries = _load_countries(source / "countryInfo.txt")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    db = sqlite3.connect(target)
    db.executescript(
        """
        PRAGMA journal_mode = OFF;
        CREATE TABLE place (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            ascii       TEXT NOT NULL,
            -- The primary name, accent-folded. Kept as a column so search can
            -- tell "this is what the place is called" from "this is one of a
            -- hundred nicknames": Jakarta really is listed as "New York Van
            -- Java", and without this it outranks New York for "new york".
            fold_name   TEXT NOT NULL,
            -- Every folded spelling, pipe-delimited, so search can ask "is
            -- this exactly what somewhere is called in some language?" with a
            -- single substring test. Without it "roma" answers with Roma in
            -- Lesotho and "münchen" with a Swiss suburb, because Rome and
            -- Munich are both indexed under their English names.
            fold_alts   TEXT NOT NULL,
            country     TEXT NOT NULL,
            country_name TEXT NOT NULL,
            region      TEXT,
            latitude    REAL NOT NULL,
            longitude   REAL NOT NULL,
            timezone    TEXT NOT NULL,
            population  INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE place_fts USING fts5(
            search, content='', tokenize='unicode61 remove_diacritics 2'
        );
        """
    )

    rows = 0
    with (source / "cities5000.txt").open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 18:
                continue
            (
                geoname_id, name, ascii_name, alternates, latitude, longitude,
                _fclass, _fcode, country, _cc2, admin1_code, *rest
            ) = parts
            population = int(parts[14] or 0)
            timezone = parts[17]
            if not timezone:
                continue

            region = admin1.get(f"{country}.{admin1_code}") if admin1_code else None
            folded = dict.fromkeys(
                [fold(name), fold(ascii_name)]
                + [fold(a) for a in alternates.split(",") if a]
            )
            kept = list(folded)[:MAX_ALTERNATES]
            search = " ".join(
                kept + [fold(countries.get(country, country)), fold(region or "")]
            )
            fold_alts = "|" + "|".join(kept) + "|"

            db.execute(
                "INSERT INTO place VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    int(geoname_id), name, ascii_name, fold(name), fold_alts, country,
                    countries.get(country, country), region,
                    float(latitude), float(longitude), timezone, population,
                ),
            )
            db.execute(
                "INSERT INTO place_fts(rowid, search) VALUES (?, ?)",
                (int(geoname_id), search),
            )
            rows += 1
            del rest

    db.executescript(
        """
        CREATE INDEX place_population ON place(population DESC);
        CREATE INDEX place_country ON place(country);
        CREATE INDEX place_fold_name ON place(fold_name);
        """
    )
    db.commit()
    db.execute("VACUUM")
    db.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--target", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "places.sqlite"
    )
    args = parser.parse_args()

    rows = build(args.source, args.target)
    size = args.target.stat().st_size / 1_000_000
    print(f"wrote {rows:,} places to {args.target} ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
