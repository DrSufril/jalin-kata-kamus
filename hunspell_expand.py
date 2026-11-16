"""Expand a Hunspell/MySpell dictionary into its full valid word set.

A Hunspell .dic file lists *stems* plus affix flags; the .aff file defines
what those flags do. Reading .dic alone therefore undercounts badly — it is
why 'menulis' and 'menyapu' appear to be missing.

This module applies the .aff rules faithfully, which is more reliable than
re-deriving Malay morphology ourselves: the dictionary's own flags decide
which allomorph applies, so exceptions like tani -> petani (not penani)
come out right.

Supported: PFX, SFX, strip strings, regex conditions, cross-products.
Not supported: COMPOUND*, NEEDAFFIX, PFX/SFX capitalisation tricks,
phonetic REP rules (irrelevant for word validity).

Licence note: ms_MY .dic/.aff are GFDL/GPL (MIMOS/PTS/UPSI). Fine for a
prototype; for an App Store release prefer a licensed DBP list (see
legal/) or a CC-BY source.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

Rule = tuple[str, str, str]  # (strip, add, condition)


def parse_aff(path: Path) -> tuple[dict[str, list[Rule]],
                                   dict[str, list[Rule]],
                                   dict[str, bool], dict[str, bool]]:
    """Return (prefixes, suffixes, pfx_cross, sfx_cross)."""
    prefixes: dict[str, list[Rule]] = defaultdict(list)
    suffixes: dict[str, list[Rule]] = defaultdict(list)
    pfx_cross: dict[str, bool] = {}
    sfx_cross: dict[str, bool] = {}

    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        kind = parts[0]
        if kind not in ("PFX", "SFX"):
            continue

        # header: PFX flag Y n   |  entry: PFX flag strip add condition
        if len(parts) == 4 and parts[2] in ("Y", "N") and parts[3].isdigit():
            flag, cross = parts[1], parts[2] == "Y"
            (pfx_cross if kind == "PFX" else sfx_cross)[flag] = cross
            continue
        if len(parts) != 5:
            continue

        flag, strip, add, cond = parts[1], parts[2], parts[3], parts[4]
        rule: Rule = ("" if strip == "0" else strip,
                      "" if add == "0" else add,
                      cond)
        (prefixes if kind == "PFX" else suffixes)[flag].append(rule)

    return prefixes, suffixes, pfx_cross, sfx_cross


def _pfx_apply(word: str, rules: list[Rule]) -> list[str]:
    out = []
    for strip, add, cond in rules:
        if not re.match(cond, word):
            continue
        if strip and not word.startswith(strip):
            continue
        out.append(add + word[len(strip):])
    return out


def _sfx_apply(word: str, rules: list[Rule]) -> list[str]:
    out = []
    for strip, add, cond in rules:
        if not re.search(cond + r"\Z", word):
            continue
        if strip and not word.endswith(strip):
            continue
        out.append(word[: len(word) - len(strip)] + add)
    return out


ALPHA = re.compile(r"^[a-z]{3,}$")


def expand(dic_path: Path, aff_path: Path,
           *, allow_suffixes: bool = True) -> set[str]:
    """Return every word form the dictionary considers valid."""
    prefixes, suffixes, pfx_cross, sfx_cross = parse_aff(aff_path)

    forms: set[str] = set()
    text = dic_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if lines and lines[0].strip().isdigit():
        lines = lines[1:]

    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        word, _, flags = line.partition("/")
        word = word.strip().lower()
        if not word or " " in word:
            continue
        flags = [f for f in flags if not f.isspace()]

        forms.add(word)

        # prefixes
        prefixed: set[str] = {word}
        for f in flags:
            if f in prefixes:
                for pf in _pfx_apply(word, prefixes[f]):
                    prefixed.add(pf)
                    forms.add(pf)

        if not allow_suffixes:
            continue

        # suffixes on the bare stem
        suffixed: set[str] = set()
        for f in flags:
            if f in suffixes:
                for sf in _sfx_apply(word, suffixes[f]):
                    suffixed.add(sf)
                    forms.add(sf)

        # cross-products: prefixed stems taking suffixes
        for f in flags:
            if f not in prefixes or not pfx_cross.get(f, False):
                continue
            for pf in _pfx_apply(word, prefixes[f]):
                for g in flags:
                    if g not in suffixes or not sfx_cross.get(g, False):
                        continue
                    for sf in _sfx_apply(pf, suffixes[g]):
                        forms.add(sf)

    return {w for w in forms if ALPHA.match(w)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    dic = root / "data" / "raw" / "ms_MY.dic"
    aff = root / "data" / "raw" / "ms_MY.aff"
    if not aff.exists():
        print(f"missing {aff}", file=sys.stderr)
        raise SystemExit(1)
    got = expand(dic, aff)
    print(f"expanded forms: {len(got):,}")
    for probe in ("menulis", "menyapu", "petani", "penani", "membaca",
                  "pembelajaran", "mengebom", "berenang", "mengarang"):
        print(f"  {probe:15} {'YES' if probe in got else 'no'}")
