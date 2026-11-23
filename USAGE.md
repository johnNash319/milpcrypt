# milpcrypt — Usage Guide

**Last updated:** 2026-11-23  
**Version:** 0.1.0  
**Repository:** <https://github.com/johnNash319/milpcrypt> (private)

This guide explains how to install and use the `milpcrypt` toolkit. For the
project overview, thesis context, and the PRESENT DDT validation finding, see
[`README.md`](README.md).

> **Maintenance rule.** This file is part of the deliverable. Whenever a CLI
> command, option, preset, public API, export format, dependency, or roadmap
> item changes, update this guide in the same commit. A checklist is provided
> in [Keeping this guide current](#keeping-this-guide-current).

## Contents

1. [Installation](#1-installation)
2. [Core concepts](#2-core-concepts)
3. [Command-line reference](#3-command-line-reference)
4. [Common workflows](#4-common-workflows)
5. [Python API](#5-python-api)
6. [File formats](#6-file-formats)
7. [Built-in presets](#7-built-in-presets)
8. [Thesis validation](#8-thesis-validation)
9. [Troubleshooting](#9-troubleshooting)
10. [Development and maintenance](#10-development-and-maintenance)
11. [Roadmap](#11-roadmap)
12. [Change log](#12-change-log)

---

## 1. Installation

### Requirements

- Python **3.10 or newer** (tested on Python 3.14)
- Git
- The core extraction code uses **only the Python standard library**
- Optional for future stages: `gurobipy` (MILP reduction), `scipy` (convex hull)

### Clone and install

The repository is private. On a new device, Git will ask you to authenticate
with the GitHub account that owns it:

```powershell
git clone https://github.com/johnNash319/milpcrypt.git
cd milpcrypt
python -m pip install -e ".[dev]"
```

The editable install makes `milpcrypt` importable and installs `pytest`.
The console script `milpcrypt` may not be on `PATH` on Windows, so the
documentation uses the portable form:

```powershell
python -m milpcrypt --version
```

If you prefer the shell command, add the Python scripts directory to `PATH`
or invoke the installed `milpcrypt.exe` directly.

### Optional extras

```powershell
# For the future Gurobi-based MILP reduction stages
python -m pip install -e ".[milp]"

# For the future convex-hull stages
python -m pip install -e ".[hull]"
```

### Verify the installation

```powershell
python -m milpcrypt presets
python -m milpcrypt info present
python -m pytest
```

The test suite currently has 43 tests and should pass on a clean checkout.

---

## 2. Core concepts

### 2.1 S-box input formats

A `SPEC` accepted by the CLI can be any of the following:

| Form | Example | Notes |
| --- | --- | --- |
| Preset name | `present`, `prince`, `prince-inverse`, `klein` | Case-insensitive; a few aliases are accepted |
| Hex nibble string | `c56b90ad3ef84712` | One hex digit per S-box value; intended for ≤4-bit S-boxes |
| Comma-separated values | `12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2` | Decimal or `0x`-prefixed values; works for larger S-boxes |
| Text file | `.\my_sbox.txt` | File contains either of the two forms above |

Examples:

```powershell
python -m milpcrypt info present
python -m milpcrypt info c56b90ad3ef84712
python -m milpcrypt info "12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2"
python -m milpcrypt info .\my_sbox.txt
```

> **Hex strings are nibble-oriented.** A compact hex string is read as one
> value per hex digit. For an 8-bit S-box, use a comma-separated list of
> values (for example `0x63,0x7c,0x77,...`) rather than a 256-character hex
> string.

The S-box table length must be a power of two, and every value must be in
`0 .. size-1`. The current implementation supports up to 12-bit S-boxes;
building a DDT costs `O(2^(2n))`, so 8-bit is comfortable and 12-bit is
already large.

### 2.2 Difference distribution table (DDT)

For an `n`-bit S-box `S`, the DDT entry is

```text
DDT[Δin][Δout] = #{ x : S(x) XOR S(x XOR Δin) = Δout }
```

`SBox.ddt` is a `2^n × 2^n` tuple of tuples. Every row and column sums to
`2^n`.

### 2.3 Possible and impossible paths

A differential path is the pair `(Δin, Δout)`.

- **Possible**: `DDT[Δin][Δout] > 0`
- **Impossible**: `DDT[Δin][Δout] == 0`

The all-zero path `(0,0)` is possible. It is included in the counts reported
by `info` and `summary()` because the total is `2^n × 2^n` pairs.

The `differentials --kind possible` command excludes `(0,0)` by default;
add `--include-zero-path` to include it. `--kind all` always includes it.

### 2.4 Differential branch number

The project uses the S-box differential branch number

```text
B = min( wt(Δin) + wt(Δout) )
```

over all possible paths with `Δin ≠ 0`. Every nonzero path whose total
Hamming weight is below `B` is therefore impossible.

| S-box | Branch number |
| --- | ---: |
| PRESENT | 3 |
| PRINCE | 2 |
| PRINCE inverse | 2 |
| KLEIN | 2 |

### 2.5 Impossible-path classes

`SBox.classify_impossible()` partitions the impossible paths in the order
used by the thesis:

| CLI value | Meaning | Eliminated by |
| --- | --- | --- |
| `zero-nonzero` | `Δin = 0`, `Δout ≠ 0` | Sun et al. zero/nonzero constraints |
| `nonzero-zero` | `Δin ≠ 0`, `Δout = 0` | Sun et al. zero/nonzero constraints |
| `low-weight` | nonzero path with `wt < B` | differential branch-number constraints |
| `other` | remaining impossible paths | cutting-off inequalities |

Only the `other` class needs to be eliminated by the convex-hull
cutting-off inequality set.

---

## 3. Command-line reference

General form:

```powershell
python -m milpcrypt [--version] COMMAND [OPTIONS] [SPEC]
```

List all commands and options:

```powershell
python -m milpcrypt --help
python -m milpcrypt COMMAND --help
```

### 3.1 `presets`

List the built-in S-boxes with their source references.

```powershell
python -m milpcrypt presets
```

### 3.2 `info`

Show a summary: hex table, permutation status, differential uniformity,
branch number, possible/impossible counts, and impossible-path classes.

```powershell
python -m milpcrypt info present
python -m milpcrypt info prince --json
```

Options:

| Option | Meaning |
| --- | --- |
| `--json` | Emit a machine-readable JSON object instead of text |

Example output (PRESENT):

```text
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

### 3.3 `ddt`

Print a small DDT in the terminal, or write the full DDT to CSV.

```powershell
python -m milpcrypt ddt present
python -m milpcrypt ddt present --csv results/present_ddt.csv
```

Options:

| Option | Meaning |
| --- | --- |
| `--csv PATH` | Write the full DDT as CSV instead of printing it |
| `--max-bits N` | Largest DDT allowed in the terminal (default: 5) |

A DDT larger than `--max-bits` is refused in the terminal; use `--csv` for
8-bit or larger S-boxes.

### 3.4 `differentials`

List possible, impossible, or all differential paths. This is the main
command for feeding the next MILP stage.

```powershell
# All 256 pairs of a 4-bit S-box
python -m milpcrypt differentials present --kind all --limit 20

# Possible paths without (0,0) by default
python -m milpcrypt differentials present --kind possible --limit 20

# Possible paths including (0,0)
python -m milpcrypt differentials present --kind possible --include-zero-path

# All impossible paths
python -m milpcrypt differentials present --kind impossible --limit 20

# Only the paths that need cutting-off inequalities
python -m milpcrypt differentials present --kind impossible --class other --limit 20

# Export all 113 "other" impossible paths
python -m milpcrypt differentials present --kind impossible --class other `
  --csv results/present_other_impossible.csv `
  --json results/present_other_impossible.json
```

Options:

| Option | Meaning |
| --- | --- |
| `--kind {all,possible,impossible}` | Which paths to select (default: `all`) |
| `--class CLASS` | Filter impossible paths: `zero-nonzero`, `nonzero-zero`, `low-weight`, `other` |
| `--limit N` | Rows shown in the terminal; `0` means all (default: 60) |
| `--include-zero-path` | Include `(0,0)` when `--kind possible` |
| `--csv PATH` | Export **all** selected paths to CSV |
| `--json PATH` | Export **all** selected paths to JSON |

Notes:

- `--class` is only valid with `--kind impossible`.
- `--limit` affects only terminal display; CSV/JSON exports are not truncated.
- If an export path is supplied, the terminal table is skipped and only the
  export confirmation is printed. Run without `--csv`/`--json` to see the
  table.
- The terminal table includes the class column when listing impossible paths.

### 3.5 `thesis-check`

Compare computed values with the numbers and DDTs printed in the thesis.

```powershell
python -m milpcrypt thesis-check
python -m milpcrypt thesis-check --json
python -m milpcrypt thesis-check --strict
```

Options:

| Option | Meaning |
| --- | --- |
| `--strict` | Exit with status 1 if any consistency check fails |
| `--json` | Emit JSON with `passed`, `failed`, and per-check details |

Current state: **18 checks pass and 2 fail**. Both failures are the PRESENT
Table 3.2 inconsistency described in
[README.md](README.md#important-validation-finding-present-table-32). The
default command still exits `0`; use `--strict` in CI if failures should
block. `scripts/validate_thesis.py` always exits `1` when a check fails.

---

## 4. Common workflows

### 4.1 Analyze a built-in S-box

```powershell
python -m milpcrypt info present
python -m milpcrypt ddt present
python -m milpcrypt differentials present --kind impossible --class other --limit 20
```

### 4.2 Analyze a custom S-box

Create a text file containing either a hex nibble string or a comma-separated
value list:

```text
12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2
```

Then:

```powershell
python -m milpcrypt info .\my_sbox.txt
python -m milpcrypt differentials .\my_sbox.txt --kind impossible --class other
```

You can also pass the specification inline:

```powershell
python -m milpcrypt info "c56b90ad3ef84712"
```

### 4.3 Export the reduced impossible set for MILP work

The thesis models only need cutting-off inequalities for the `other` class:

```powershell
python -m milpcrypt differentials present --kind impossible --class other `
  --csv results/present_other_impossible.csv `
  --json results/present_other_impossible.json
```

The CSV contains one row per path with binary/hex differences, Hamming
weights, DDT count, possibility flag, and class. The JSON additionally
contains the S-box metadata and its summary.

### 4.4 Export a DDT

```powershell
python -m milpcrypt ddt present --csv results/present_ddt.csv
```

The CSV has a `delta_in` header column followed by output differences
`0..15`; each subsequent row is one input difference.

### 4.5 Script against the JSON output

```powershell
python -m milpcrypt info klein --json > results/klein_info.json
python -m milpcrypt differentials prince --kind impossible --json results/prince_impossible.json
```

Read it with Python:

```python
import json

with open("results/prince_impossible.json", encoding="utf-8") as handle:
    data = json.load(handle)

print(data["sbox"]["name"])
print(data["count"])
for path in data["differentials"][:5]:
    print(path["delta_in_hex"], path["delta_out_hex"], path["class"])
```

> On Windows PowerShell, prefer the CLI `--json PATH` option over shell
> redirection (`>`) to avoid encoding surprises. Both work, but `--json`
> writes UTF-8 explicitly.

### 4.6 Validate the thesis data

```powershell
python -m milpcrypt thesis-check
python scripts\validate_thesis.py
```

The script exits `1` on any failed check and is suitable for CI.

---

## 5. Python API

### 5.1 Imports

```python
from milpcrypt import (
    Differential,
    ImpossibleClass,
    SBox,
    SBoxSummary,
    get_preset,
    list_presets,
    resolve_sbox,
)
from milpcrypt.report import (
    format_summary,
    format_ddt,
    format_differentials,
    write_ddt_csv,
    write_differentials_csv,
    write_differentials_json,
)
```

### 5.2 Creating an S-box

```python
from milpcrypt import SBox, get_preset

present = get_preset("present")
custom_hex = SBox("c56b90ad3ef84712", name="my-cipher")
custom_values = SBox(
    [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD,
     0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2],
    name="my-cipher",
)
```

Both constructors accept a sequence of integers or a string in the formats
described in [S-box input formats](#21-s-box-input-formats). `SBox.from_hex`
and `SBox.from_values` are convenience aliases.

### 5.3 Properties and methods

| Member | Description |
| --- | --- |
| `table` | Tuple of S-box values |
| `name` | Display name |
| `bits` | Input/output bit width |
| `size` | Number of values (`2**bits`) |
| `is_permutation` | Whether the table is bijective |
| `to_hex` | Uppercase hex representation |
| `ddt` / `difference_distribution_table` | The full DDT |
| `inverse()` | Inverse S-box (requires a permutation) |
| `difference_count(din, dout)` | DDT entry |
| `is_possible(din, dout)` | Whether the path has nonzero probability |
| `differential(din, dout)` | Build a `Differential` object |
| `possible_differentials(include_zero_path=True)` | Tuple of possible paths |
| `impossible_differentials()` | Tuple of impossible paths |
| `iter_all_differentials()` | Iterate over all `2^n × 2^n` paths |
| `differential_uniformity()` | Maximum DDT entry outside the zero-input row |
| `branch_number()` | S-box differential branch number |
| `classify_impossible(threshold=None)` | Partition impossible paths into classes |
| `summary()` | Aggregate `SBoxSummary` |

Example:

```python
from milpcrypt import get_preset, ImpossibleClass

sbox = get_preset("present")

print(sbox.ddt[1])                    # DDT row for Δin = 1
print(sbox.differential_uniformity()) # 4
print(sbox.branch_number())           # 3

for path in sbox.impossible_differentials()[:5]:
    print(
        path.delta_in_hex,
        path.delta_out_hex,
        path.weight,
        path.count,
    )

classes = sbox.classify_impossible()
for category in ImpossibleClass:
    print(category.value, len(classes[category]))
```

### 5.4 `Differential` objects

Each path exposes:

| Member | Description |
| --- | --- |
| `delta_in`, `delta_out` | Integer differences |
| `count` | DDT count |
| `bits` | S-box bit width |
| `possible` | `count > 0` |
| `weight_in`, `weight_out`, `weight` | Hamming weights |
| `is_zero_path` | `delta_in == 0 and delta_out == 0` |
| `delta_in_hex`, `delta_out_hex` | Zero-padded hex strings |
| `delta_in_bin`, `delta_out_bin` | Zero-padded binary strings |
| `hex_width` | Hex width for the S-box size |

### 5.5 `SBoxSummary` fields

`summary()` returns a frozen dataclass with:

```text
name, bits, size, is_permutation,
differential_uniformity, branch_number,
possible, possible_nonzero, impossible,
zero_to_nonzero, nonzero_to_zero, low_weight, other
```

The last four sum to `impossible`.

### 5.6 Export functions

```python
from milpcrypt import get_preset, ImpossibleClass
from milpcrypt.report import (
    write_ddt_csv,
    write_differentials_csv,
    write_differentials_json,
)

sbox = get_preset("present")
classes = sbox.classify_impossible()
other = classes[ImpossibleClass.OTHER]

write_ddt_csv("results/present_ddt.csv", sbox)
write_differentials_csv(
    "results/present_other.csv", sbox, other, classes
)
write_differentials_json(
    "results/present_other.json",
    sbox,
    other,
    classes,
    kind="impossible:other",
)
```

All writer functions create parent directories and return the written
`Path`.

### 5.7 Resolving CLI-style specifications

```python
from milpcrypt import resolve_sbox

sbox = resolve_sbox("present")        # preset
sbox = resolve_sbox("c56b90ad3ef84712")  # inline hex
sbox = resolve_sbox("my_sbox.txt")    # file
```

`resolve_sbox` raises `ValueError` for an unknown preset or invalid table.

---

## 6. File formats

### 6.1 DDT CSV

Header:

```text
delta_in,0,1,2,3,...,15
```

Each following row starts with the input difference and contains the 16
output-difference counts (or `2^n` entries for a larger S-box).

### 6.2 Differential-path CSV

Columns:

```text
delta_in,delta_in_hex,delta_in_bin,wt_in,
delta_out,delta_out_hex,delta_out_bin,wt_out,wt_total,
count,possible,class
```

- `possible` is `1` for possible paths and `0` for impossible paths.
- `class` is filled only when the caller supplies a classification mapping
  (the CLI does this for `--kind impossible`); it is empty otherwise.

### 6.3 Differential-path JSON

Top-level shape:

```json
{
  "sbox": {
    "name": "PRESENT",
    "bits": 4,
    "hex": "C56B90AD3EF84712",
    "table": [12, 5, 6, 11]
  },
  "summary": {
    "possible": 97,
    "impossible": 159,
    "other": 113
  },
  "kind": "impossible:other",
  "count": 113,
  "differentials": [
    {
      "delta_in": 1,
      "delta_in_hex": "1",
      "delta_in_bin": "0001",
      "wt_in": 1,
      "delta_out": 5,
      "delta_out_hex": "5",
      "delta_out_bin": "0101",
      "wt_out": 2,
      "wt_total": 3,
      "count": 0,
      "possible": false,
      "class": "other"
    }
  ]
}
```

The `summary` object contains every `SBoxSummary` field, not just the
abbreviated fields shown above.

---

## 7. Built-in presets

| Key | Name | S-box hex | Bits | Possible | Impossible | Branch | Zero→nonzero | Nonzero→zero | Low weight | Other |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `present` | PRESENT | `C56B90AD3EF84712` | 4 | 97 | 159 | 3 | 15 | 15 | 16 | 113 |
| `prince` | PRINCE | `BF32AC916780E5D4` | 4 | 106 | 150 | 2 | 15 | 15 | 0 | 120 |
| `prince-inverse` | PRINCE inverse | `B732FD89A6405EC1` | 4 | 106 | 150 | 2 | 15 | 15 | 0 | 120 |
| `klein` | KLEIN | `74A91FB0C3268ED5` | 4 | 106 | 150 | 2 | 15 | 15 | 0 | 120 |

All four are permutations with differential uniformity 4. The `possible`
column includes the `(0,0)` path.

To inspect a preset from Python:

```python
from milpcrypt import list_presets, get_preset

for preset in list_presets():
    print(preset.key, preset.name, preset.source)
```

---

## 8. Thesis validation

The reference numbers come from:

> Can Türesin, *On Measuring Security Bounds of Some Ciphers Using Mixed
> Integer Linear Programming (MILP) Approach*, METU, September 2021.

Run:

```powershell
python -m milpcrypt thesis-check
```

What is checked:

- possible and impossible path counts for each S-box,
- differential branch numbers,
- the number of paths left after removing zero/nonzero conflicts and
  low-weight impossibles,
- every DDT printed in the thesis against the DDT recomputed from the
  corresponding S-box.

Current result: **18 passed, 2 failed**. The two failures are both PRESENT:

- Table 3.2 row `Δ = 1` is printed as `{4,5,6,7,C,D,E,F}`, while the
  S-box in Table 3.1 gives `{3,7,9,D}`; 129 of 256 entries differ.
- Consequently, the “118 remaining impossibles” figure is not reproduced:
  the correct S-box gives `159 − 30 − 16 = 113`, and the printed table
  gives 115 when branch number 3 is imposed.

PRINCE, PRINCE inverse, and KLEIN match their printed DDTs exactly. See the
[README section](README.md#important-validation-finding-present-table-32)
for the full discussion.

`python scripts\validate_thesis.py` prints the same report and exits `1`
when any check fails.

---

## 9. Troubleshooting

### `milpcrypt` is not recognized

Use the module form:

```powershell
python -m milpcrypt ...
```

Or add the Python scripts directory to `PATH`. The script is usually under
`%LOCALAPPDATA%\Programs\Python\Python3xx\Scripts` or the path printed by
`python -m site --user-base`.

### `No module named milpcrypt`

Run the editable install from the repository root:

```powershell
python -m pip install -e ".[dev]"
```

### The DDT is too large for the terminal

`ddt` refuses DDTs above 5 bits by default. Export instead:

```powershell
python -m milpcrypt ddt my_sbox.txt --csv results/my_ddt.csv
```

### “S-box table length must be a power of two”

The number of values must be `2, 4, 8, 16, 32, ...`. A hex string is read
one digit per value, so `abc` is three values and is invalid. For an 8-bit
S-box, use a comma-separated list of 256 values.

### `--class` can only be used with `--kind impossible`

Remove `--class` or change the selection:

```powershell
python -m milpcrypt differentials present --kind impossible --class other
```

### PowerShell shows a red error after a successful command

Some native tools write progress to stderr; PowerShell may render that as an
error even when the command succeeded. Check `$LASTEXITCODE` or the produced
file. For exports, prefer `--csv`/`--json` over shell redirection.

### Gurobi is not available

Gurobi is not needed for the current S-box extraction milestone. It will be
used by the future MILP reduction stage. The repository root contains
`gbTest.py`, which prints the installed Gurobi version:

```powershell
python gbTest.py
```

### Private-repository authentication on another device

GitHub will ask you to sign in when cloning the private repository. Use the
same account that owns `johnNash319/milpcrypt`; a personal access token or
Git Credential Manager/browser login is sufficient.

---

## 10. Development and maintenance

### Run the tests

```powershell
python -m pytest
```

Current suite: 43 tests.

### Add a new S-box preset

1. Add an entry to `PRESETS` in `src/milpcrypt/presets.py`.
2. Add it to the preset-related tests if the counts are known.
3. Add a row to the preset table in [section 7](#7-built-in-presets).
4. Add a thesis claim to `CLAIMS`/`PRINTED_DDTS` in `src/milpcrypt/thesis.py`
   if it comes from the thesis and should be validated.
5. Run `python -m pytest` and `python -m milpcrypt presets`.

### Add a CLI command or option

1. Update `build_parser()` and add a handler in `src/milpcrypt/cli.py`.
2. Add a CLI test in `tests/test_cli.py`.
3. Document the command/option in [section 3](#3-command-line-reference).
4. Add a workflow example if it is a common task.
5. Update the README quick-start table if the command is user-facing.

### Change the public Python API

1. Update the implementation and tests.
2. Update the API tables/examples in [section 5](#5-python-api).
3. Check that the README examples still work.

### Change an export format

1. Update `src/milpcrypt/report.py`.
2. Update the format description in [section 6](#6-file-formats).
3. Add or update a round-trip test.

### Keeping this guide current

Treat `USAGE.md` as part of the definition of done. In the same commit as a
feature, check:

- [ ] `Last updated` date and version at the top are current.
- [ ] Command reference reflects every new/removed option.
- [ ] Examples still produce the shown output.
- [ ] Python API signatures and tables are current.
- [ ] Preset/count tables are current.
- [ ] File-format examples are current.
- [ ] Installation/dependency instructions are current.
- [ ] Roadmap status is current.
- [ ] Change log has a new entry.
- [ ] `python -m pytest` passes.
- [ ] `python -m milpcrypt --help` and the changed command’s `--help` work.

Then commit and push:

```powershell
git add .
git commit -m "Update usage guide for <feature>"
git push
```

---

## 11. Roadmap

Current milestone: **S-box differential extraction and thesis validation**.

- [x] Arbitrary S-box input, DDT, possible/impossible paths
- [x] Differential branch number and thesis impossible-path classification
- [x] CSV/JSON export of all differential paths
- [x] Automated thesis-table and count validation
- [ ] Convex hull of possible paths → inequality set `Hset`
- [ ] Boura et al. extension (candidate inequalities from k-sums)
- [ ] Sasaki et al. MILP reduction with Gurobi
- [ ] Thesis-filtered reduction: reproduce 15 / 18 / 18 inequality counts on
      the correct DDTs and verify every remaining impossible path is cut
- [ ] PRESENT / PRINCE / KLEIN round models and minimum active S-box bounds
- [ ] Linear (LAT-based) counterpart

When a roadmap item is implemented, move it to the completed list, document
the new commands/API here, and add a change-log entry.

---

## 12. Change log

| Date | Version | Change |
| --- | --- | --- |
| 2026-11-23 | 0.1.0 | Initial usage guide for S-box extraction, CLI, API, exports, and thesis validation |
