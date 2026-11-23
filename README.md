# milpcrypt

A small research toolkit for the thesis **“On Measuring Security Bounds of
Some Ciphers Using Mixed Integer Linear Programming (MILP) Approach”**
(Can Türesin, METU, September 2021).

The end goal is a reproducible implementation of the thesis pipeline:

1. extract the possible/impossible differential paths of an S-box,
2. build the convex hull of the possible paths,
3. extend/reduce the cutting-off inequality set (Sun, Sasaki, Boura),
4. apply the thesis's impossible-path classification to shrink the S-box
   model,
5. build full cipher models and compute minimum active S-box counts.

**Current milestone:** step 1 is implemented and tested for arbitrary
bit-oriented S-boxes, together with an automated consistency check against
the numbers printed in the thesis.

## Quick start

```powershell
git clone https://github.com/johnNash319/milpcrypt.git
cd milpcrypt
python -m pip install -e ".[dev]"

python -m milpcrypt presets
python -m milpcrypt info present
python -m milpcrypt ddt present
python -m milpcrypt differentials present --kind impossible --class other --limit 20
python -m milpcrypt thesis-check
python -m pytest
```

`milpcrypt.exe` is installed in the Python scripts directory, but
`python -m milpcrypt ...` works without touching `PATH`.

### Commands

| Command | Purpose |
| --- | --- |
| `presets` | list the built-in S-boxes (PRESENT, PRINCE, PRINCE inverse, KLEIN) |
| `info SPEC` | DDT summary, differential uniformity, branch number, impossible-path classes |
| `ddt SPEC` | print a small DDT or export it with `--csv PATH` |
| `differentials SPEC` | list possible/impossible paths; filter with `--kind`, `--class`, `--limit` |
| `differentials ... --csv PATH` | export all matching paths as CSV |
| `differentials ... --json PATH` | export all matching paths as JSON |
| `thesis-check` | compare computed values with the thesis tables/text (`--strict` exits 1 on failure) |

`SPEC` can be a preset name, a path to a text file, a hex nibble string
(`c56b90ad3ef84712`), or a comma-separated value list
(`12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2`).

### Example

```text
$ python -m milpcrypt info present
S-box: PRESENT
  hex                 : C56B90AD3EF84712
  size                : 4-bit, 16 values
  permutation         : yes
  differential unif.  : 4
  branch number       : 3

Differential pairs (2^n x 2^n, including the zero path):
  possible            : 97
    of which nonzero  : 96
  impossible          : 159

Impossible-path classes (thesis Chapter 3):
  zero -> nonzero     : 15
  nonzero -> zero     : 15
  weight < branch (3) : 16
  other               : 113
```

## Python API

```python
from milpcrypt import get_preset, ImpossibleClass

sbox = get_preset("present")

print(sbox.ddt[1])                 # difference distribution row for Δin = 1
print(sbox.differential_uniformity())
print(sbox.branch_number())

for path in sbox.impossible_differentials():
    print(path.delta_in_hex, path.delta_out_hex, path.count)

classes = sbox.classify_impossible()
for category in ImpossibleClass:
    print(category.value, len(classes[category]))
```

Conventions:

* All `2^n × 2^n` input/output pairs are counted; the all-zero path
  `(0,0)` is possible and is included by default in ``possible`` counts.
* The differential branch number is
  `min(wt(Δin) + wt(Δout))` over possible paths with `Δin ≠ 0`. This gives
  `3` for PRESENT's S-box and `2` for PRINCE/KLEIN, matching the thesis.
* The impossible-path classes use the thesis's filtering order: zero/nonzero
  conflicts first, then weight below the branch number, then “other”.
  Only the “other” paths need cutting-off inequalities.

## Important validation finding: PRESENT Table 3.2

`python -m milpcrypt thesis-check` recomputes every count and also compares
each DDT printed in the thesis with the DDT of the corresponding S-box.

* PRINCE (Table 3.4), PRINCE inverse (Table 3.6), and KLEIN (Table 3.8):
  **match exactly**, and all printed counts are reproduced.
* PRESENT's S-box (Table 3.1) and DDT (Table 3.2) are **inconsistent**:
  * Table 3.2 row `Δ = 1` is `{4,5,6,7,C,D,E,F}`;
  * the S-box in Table 3.1 gives `{3,7,9,D}`;
  * in total, 129 of the 256 DDT entries differ.

The `{3,7,9,D}` row is independently confirmed in the literature (e.g.,
Albrecht–Cid, “Algebraic Techniques in Differential Cryptanalysis,”
IACR ePrint 2008/177, which states that for input difference `1` the possible
output differences are `3, 7, 9, D`).

This affects the filtering arithmetic in Section 3.1.1:

| Source | impossible | − zero/nonzero | − low weight | residual |
| --- | ---: | ---: | ---: | ---: |
| thesis text | 159 | 30 | 11 | 118 |
| correct S-box | 159 | 30 | 16 | **113** |
| printed Table 3.2 | 159 | 30 | 14 | **115** |

The printed table would also imply branch number 2, not 3. The 118 figure is
not reproduced from either table. The PRESENT “15 inequalities” model should
therefore be re-run/verified against the correct DDT before the speed-up in
Table 3.9 is relied upon. PRINCE and KLEIN results are unaffected by this
particular issue.

The check is intentionally reported by `thesis-check` as a **data-consistency
finding**, not a solver error.

## Project layout

```text
milpcrypt/
├── pyproject.toml
├── src/milpcrypt/
│   ├── sbox.py       # DDT, possible/impossible paths, branch number, classes
│   ├── presets.py    # PRESENT, PRINCE, PRINCE inverse, KLEIN S-boxes
│   ├── report.py     # terminal tables, CSV/JSON export
│   ├── thesis.py     # printed tables + automated consistency checks
│   └── cli.py        # python -m milpcrypt
├── tests/
├── scripts/
│   └── validate_thesis.py
├── docs/
│   ├── thesis.pdf        # original thesis
│   └── thesis_text.txt   # text extraction of the PDF (reference only)
└── results/              # generated exports (git-ignored)
```

## Roadmap

- [x] Arbitrary S-box input, DDT, possible/impossible paths
- [x] Differential branch number and thesis impossible-path classification
- [x] CSV/JSON export of all differential paths
- [x] Automated thesis-table and count validation
- [ ] Convex hull of possible paths → inequality set `Hset`
- [ ] Boura et al. extension (candidate inequalities from k-sums)
- [ ] Sasaki et al. MILP reduction (Gurobi)
- [ ] Thesis-filtered reduction: reproduce 15 / 18 / 18 inequality counts on
      the **correct** DDTs, and verify every remaining impossible path is cut
- [ ] PRESENT / PRINCE / KLEIN round models and minimum active S-box bounds
- [ ] Linear (LAT-based) counterpart

## Requirements

* Python ≥ 3.10 (tested on 3.14)
* Core extraction: standard library only
* MILP stages (roadmap): `gurobipy` (already licensed locally; `gbTest.py`
  checks the installation)
* Convex-hull stages (roadmap): `scipy`/SageMath or another exact H-rep tool
