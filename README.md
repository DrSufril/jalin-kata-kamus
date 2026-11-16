# Jalin Kata — Malay word list

A list of 48,926 attested Malay word forms, produced for the word game
**Jalin Kata** (*Jalin Kata: Permainan Menghubungkan Perkataan Bahasa
Malaysia*). This repository exists to satisfy the source and licence
obligations for the GPL-covered part of that word data.

## Licence

The word list in this repository — `wordlist.txt`, the derived forms in it, and
the build scripts that produce it — is licensed under the **GNU General Public
License, version 2**. The full text is in [COPYING](COPYING).

The list is derived from:

| Input | Origin | Licence |
|---|---|---|
| `ms_MY.aff` — affix rules | MIMOS Open Source R&D, 2004, with UPSI and PTS Publications Sdn Bhd | GPL-2.0 |
| `ms_MY.dic` — word stems | fetched by you, see below | no licence statement in the file |
| `wn-msa-all.tab` — Malay lemmas | WordNet Bahasa (Bond et al., 2011–2014) | MIT |

`ms_MY.aff` is included verbatim in this repository. Its header states, in the
original words of the authors, *"Fail affik ini dilesenkan di bawah GPL"* and
*"Released under GPL"*.

`wn-msa-all.tab` is **not** redistributed here; the MIT lemmas are a small
minority of the output and are attributed in
[LICENSES/MIT-WordNet-Bahasa.txt](LICENSES/MIT-WordNet-Bahasa.txt).

## Why this repository exists

The app loads the word list as a data file at launch. The list is a covered
work under the GPL because it is produced by applying GPL-licensed affix
rules. Publishing it here, with the scripts that generate it, gives every
recipient of the app the corresponding source for that data.

The app itself is a separate, proprietary work; it reads this list as text and
links no GPL code. The list and the app are aggregated, not combined.

## Rebuilding the list

You need Python 3 and two upstream downloads.

```bash
# 1. word stems — not redistributed here (no licence statement in file)
curl -LO https://raw.githubusercontent.com/fakhrullah/MalayLanguage/master/ms_MY.dic
shasum -a 256 ms_MY.dic
#   99333684ccf14f2d... — see SHA256SUMS

# 2. WP-format lemma file (MIT)
curl -LO https://raw.githubusercontent.com/limaginaire/Bahasa-Wordnet/master/wn-msa-all.tab

# 3. build
mkdir -p data/raw data/out
cp ms_MY.dic ms_MY.aff wn-msa-all.tab data/raw/
python3 build_wordlist.py
```

`build_wordlist.py` writes `data/out/wordlist.txt`. It is attested-only: a form
ships only if one of the inputs contains it. Generated affixed forms are
opt-in via `--expand`, and are deliberately excluded here because in a word
game a false positive is worse than a false negative.

The committed `wordlist.txt` is the output of that command, unmodified.

## Contents

| File | What it is |
|---|---|
| `wordlist.txt` | 48,926 words, one per line, lowercase, sorted |
| `ms_MY.aff` | affix rules, verbatim, GPL-2.0 |
| `build_wordlist.py` | normalise, expand, deduplicate, filter compounds |
| `hunspell_expand.py` | applies `.aff` rules to `.dic` stems |
| `COPYING` | GPL-2.0 |
| `LICENSES/` | MIT notice for WordNet Bahasa |
| `SHA256SUMS` | checksums for the files in this directory |

Particles and clitics (`-lah`, `-kah`, `-nya`, `-ku`, `-mu`) and hyphenated
reduplication (`rumah-rumah`) are excluded deliberately. Multi-word entries
(2,215 of them) are filtered to `compounds.txt` upstream and are not playable.

## Corrections

This data is **not** from *Kamus Dewan Perdana*. It is not validated by Dewan
Bahasa dan Pustaka, and no DBP endorsement is claimed. The app's licence
request to DBP is separate and pending.
