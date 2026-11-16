#!/usr/bin/env python3
"""Build the word list for Jalin Kata, a Bahasa Malaysia word-tile game.

Design constraint that drives everything here:

    DBP's Kamus Dewan Perdana is copyrighted and explicitly cannot be
    bulk-reproduced (see legal/). We therefore build from sources that are
    genuinely licensed for reuse, and structure the output so a licensed
    DBP list can be dropped in later with no code changes.

Sources:
    wn-msa-all.tab   WordNet Bahasa, Malay lemmas   MIT
    ms_MY.aff        Hunspell ms_MY affix rules      GPL-2.0 (MIMOS, 2004)
    ms_MY.dic        Hunspell ms_MY word stems       no licence statement in file

The licence statement lives in ms_MY.aff itself; earlier builds recorded the
Hunspell data as GFDL, which was wrong. See legal/THIRD-PARTY-NOTICES.md.
The derived list is released under GPL-2.0 via wordlist-gpl/.

Default behaviour is ATTESTED-ONLY: a word ships only if it appears in a
source. Generated affixed forms are opt-in (--expand) and kept in a
separate file, because false positives damage a word game far more than
false negatives.

Outputs (data/out/):
    wordlist.txt      attested words, sorted, one per line
    generated.txt     optional affix-generated candidates (--expand)
    compounds.txt     multi-word entries (excluded from play)
    meta.json         counts, sources, licences, build provenance

Usage:
    python3 tools/build_wordlist.py
    python3 tools/build_wordlist.py --expand
    python3 tools/build_wordlist.py --swift-resources
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from affix_ms import generate_forms  # noqa: E402
from hunspell_expand import expand as hunspell_expand  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "out"

ALPHA_ONLY = re.compile(r"^[a-z]{2,}$")
HYPHENATED = re.compile(r"^[a-z]+(-[a-z]+)+$")

# WordNet quality codes. Y = hand-checked, O = automatic high quality,
# M = automatic medium. Default keeps Y and O only.
WORDNET_GOODNESS = {"Y", "O"}


def load_wordnet(path: Path, goodness: set[str]) -> tuple[set[str], set[str]]:
    """Return (single_words, compounds) from WordNet Bahasa.

    File is TSV: synset, lang, goodness, lemma
    lang 'M' = Malay (zsm); 'B' is the msa supertype covering Malay and
    Indonesian, so it is deliberately excluded to avoid Indonesian forms.
    """
    words: set[str] = set()
    compounds: set[str] = set()
    if not path.exists():
        print(f"  ! missing {path}", file=sys.stderr)
        return words, compounds

    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            _, lang, qual, lemma = parts[0], parts[1], parts[2], parts[3]
            if lang != "M" or qual not in goodness:
                continue
            lemma = lemma.strip().lower()
            if " " in lemma:
                compounds.add(lemma)
            elif ALPHA_ONLY.match(lemma) or HYPHENATED.match(lemma):
                words.add(lemma)
    return words, compounds


def load_hunspell(path: Path) -> tuple[set[str], set[str]]:
    """Parse a Hunspell .dic file (first line is the entry count).

    This reads stems only. Use load_hunspell_expanded() when the .aff file
    is available, which yields the full inflected/derived set.
    """
    words: set[str] = set()
    compounds: set[str] = set()
    if not path.exists():
        print(f"  ! missing {path}", file=sys.stderr)
        return words, compounds

    with path.open(encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for line in lines[1:] if lines and lines[0].strip().isdigit() else lines:
        entry = line.split("/", 1)[0].strip().lower()
        if not entry:
            continue
        if " " in entry:
            compounds.add(entry)
        elif ALPHA_ONLY.match(entry) or HYPHENATED.match(entry):
            words.add(entry)
    return words, compounds


def load_hunspell_expanded(dic: Path, aff: Path) -> tuple[set[str], set[str]]:
    """Full valid-word set via the .aff rules (preferred over stems only)."""
    if not dic.exists():
        print(f"  ! missing {dic}", file=sys.stderr)
        return set(), set()
    if not aff.exists():
        print(f"  ! missing {aff} — falling back to stems only", file=sys.stderr)
        return load_hunspell(dic)

    with dic.open(encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    compounds: set[str] = set()
    for line in lines[1:] if lines and lines[0].strip().isdigit() else lines:
        entry = line.split("/", 1)[0].split("#", 1)[0].strip().lower()
        if " " in entry:
            compounds.add(entry)

    words = hunspell_expand(dic, aff)
    return words, compounds


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Jalin Kata word list")
    ap.add_argument("--expand", action="store_true",
                    help="also generate affixed forms from attested roots")
    ap.add_argument("--expand-all", action="store_true",
                    help="generate from every attested word (noisy; review)")
    ap.add_argument("--stems-only", action="store_true",
                    help="use Hunspell stems only, skipping .aff expansion")
    ap.add_argument("--swift-resources", action="store_true",
                    help="copy output into the Swift package resources")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("loading sources...")
    wn_words, wn_comp = load_wordnet(RAW / "wn-msa-all.tab", WORDNET_GOODNESS)
    if args.stems_only:
        hs_words, hs_comp = load_hunspell(RAW / "ms_MY.dic")
        hs_label = "Hunspell ms_MY (stems only)"
    else:
        hs_words, hs_comp = load_hunspell_expanded(RAW / "ms_MY.dic",
                                                   RAW / "ms_MY.aff")
        hs_label = "Hunspell ms_MY (affix-expanded)"
    print(f"  WordNet Bahasa (Malay, Y+O): {len(wn_words):>7} words, "
          f"{len(wn_comp)} compounds")
    print(f"  {hs_label}: {len(hs_words):>7} words, {len(hs_comp)} compounds")

    attested = wn_words | hs_words
    overlap = len(wn_words & hs_words)
    print(f"  union:                       {len(attested):>7} words "
          f"({overlap} in both)")

    # --- optional affix expansion -------------------------------------
    generated: set[str] = set()
    if args.expand or args.expand_all:
        base = attested if args.expand_all else wn_words
        print(f"generating affixed forms from {len(base)} roots...")
        for root in base:
            generated.update(generate_forms(root))
        generated -= attested  # only keep forms the sources didn't attest
        print(f"  generated candidates:        {len(generated):>7}")

    # --- write -------------------------------------------------------
    (OUT / "wordlist.txt").write_text("\n".join(sorted(attested)) + "\n",
                                      encoding="utf-8")
    compounds = wn_comp | hs_comp
    (OUT / "compounds.txt").write_text("\n".join(sorted(compounds)) + "\n",
                                       encoding="utf-8")
    if generated:
        (OUT / "generated.txt").write_text("\n".join(sorted(generated)) + "\n",
                                           encoding="utf-8")

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attested_words": len(attested),
        "generated_candidates": len(generated),
        "compounds_excluded": len(compounds),
        "sources": [
            {"name": "WordNet Bahasa (Malay lemmas)",
             "file": "wn-msa-all.tab",
             "licence": "MIT",
             "copyright": ("Francis Bond, Nurril Hirfana Mohamed Noor, "
                           "Suerya Sapuan, Muhammad Zulhelmy Mohamed Rosman, "
                           "Hammam Riza, Tan Enya Kong (2011-2014)"),
             "url": "https://github.com/limaginaire/Bahasa-Wordnet"},
            {"name": "Hunspell ms_MY affix rules",
             "file": "ms_MY.aff",
             "licence": "GPL-2.0",
             "copyright": ("MIMOS Open Source R&D (2004), with UPSI and "
                           "PTS Publications Sdn Bhd"),
             "url": "https://github.com/fakhrullah/MalayLanguage"},
            {"name": "Hunspell ms_MY word stems",
             "file": "ms_MY.dic",
             "licence": ("not stated in the file; see "
                         "legal/THIRD-PARTY-NOTICES.md"),
             "url": "https://github.com/fakhrullah/MalayLanguage"},
        ],
        "data_licence": ("GPL-2.0 for the derived list; published at "
                         "wordlist-gpl/"),
        "notices": "legal/THIRD-PARTY-NOTICES.md",
        "authority": ("NOT validated against Kamus Dewan Perdana. "
                      "Replace with a licensed DBP list (see legal/) "
                      "before App Store release."),
        "policy": ("attested-only" if not generated
                   else "attested + generated candidates (review required)"),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2) + "\n",
                                   encoding="utf-8")

    print("\nwrote:")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size:>9,} bytes")

    # --- copy into the app -------------------------------------------
    if args.swift_resources:
        dest = ROOT / "KataKit" / "Sources" / "KataKit" / "Resources"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "wordlist.txt").write_text(
            (OUT / "wordlist.txt").read_text(encoding="utf-8"),
            encoding="utf-8")
        print(f"\ncopied -> {dest.relative_to(ROOT)}/wordlist.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
