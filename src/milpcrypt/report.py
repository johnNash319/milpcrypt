"""Formatting and export helpers for S-box differential data."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping, Sequence

from .sbox import (
    Differential,
    ImpossibleClass,
    SBox,
    SBoxSummary,
)


def _hex_width(bits: int) -> int:
    return max(1, (bits + 3) // 4)


def _class_lookup(
    classes: Mapping[ImpossibleClass, Sequence[Differential]] | None,
) -> dict[tuple[int, int], ImpossibleClass]:
    if not classes:
        return {}
    return {
        (differential.delta_in, differential.delta_out): category
        for category, items in classes.items()
        for differential in items
    }


def format_summary(sbox: SBox, summary: SBoxSummary | None = None) -> str:
    summary = summary or sbox.summary()
    lines = [
        f"S-box: {summary.name}",
        f"  hex                 : {sbox.to_hex}",
        f"  size                : {summary.bits}-bit, {summary.size} values",
        f"  permutation         : {'yes' if summary.is_permutation else 'no'}",
        f"  differential unif.  : {summary.differential_uniformity}",
        f"  branch number       : {summary.branch_number}",
        "",
        "Differential pairs (2^n x 2^n, including the zero path):",
        f"  possible            : {summary.possible}",
        f"    of which nonzero  : {summary.possible_nonzero}",
        f"  impossible          : {summary.impossible}",
        "",
        "Impossible-path classes (thesis Chapter 3):",
        f"  zero -> nonzero     : {summary.zero_to_nonzero}",
        f"  nonzero -> zero     : {summary.nonzero_to_zero}",
        (
            f"  weight < branch ({summary.branch_number}) : "
            f"{summary.low_weight}"
        ),
        f"  other               : {summary.other}",
        f"  {'-' * 30}",
        f"  sum                 : "
        f"{summary.zero_to_nonzero + summary.nonzero_to_zero + summary.low_weight + summary.other}",
        "",
        (
            "Cutting-off inequalities only need to eliminate the "
            f"{summary.other} 'other' paths; the remaining "
            f"{summary.impossible - summary.other} are handled by standard "
            "zero/branch-number constraints."
        ),
    ]
    return "\n".join(lines)


def format_ddt(sbox: SBox, max_bits: int = 5) -> str:
    """Render a DDT as a terminal table.

    Large DDTs (more than 5-bit S-boxes by default) are rejected because a
    257-column terminal table is unreadable; use :func:`write_ddt_csv`.
    """
    if sbox.bits > max_bits:
        raise ValueError(
            f"refusing to print a {sbox.bits}-bit DDT in the terminal; "
            "use --csv instead"
        )

    size = sbox.size
    hex_width = _hex_width(sbox.bits)
    value_width = max(2, len(str(size)))
    label_width = max(len("in\\out"), hex_width)

    header = (
        f"{'in\\out':>{label_width}} | "
        + " ".join(
            f"{value:0{hex_width}X}".rjust(value_width)
            for value in range(size)
        )
    )
    separator = (
        "-" * label_width
        + "-+-"
        + "-" * (size * (value_width + 1) - 1)
    )
    lines = [header, separator]

    for delta_in in range(size):
        row_label = f"{delta_in:0{hex_width}X}".rjust(label_width)
        values = " ".join(
            f"{count:>{value_width}}" for count in sbox.ddt[delta_in]
        )
        lines.append(f"{row_label} | {values}")

    lines.append("")
    lines.append(
        "Rows: input differences; columns: output differences; "
        "entries: number of x values."
    )
    return "\n".join(lines)


def format_differentials(
    sbox: SBox,
    differentials: Sequence[Differential],
    limit: int | None = None,
    classes: Mapping[ImpossibleClass, Sequence[Differential]] | None = None,
) -> str:
    if not differentials:
        return "No differential paths match the selected filters."

    lookup = _class_lookup(classes)
    hex_width = _hex_width(sbox.bits)
    count_width = max(len("count"), len(str(sbox.size)))
    in_width = max(hex_width, len("in"))
    out_width = max(hex_width, len("out"))
    wt_width = max(
        len("wt(in)"), len("wt(out)"), len("wt"), len(str(sbox.bits))
    )

    header = (
        f"{'in':>{in_width}}  {'out':>{out_width}}  "
        f"{'wt(in)':>{wt_width}}  {'wt(out)':>{wt_width}}  "
        f"{'wt':>{wt_width}}  {'count':>{count_width}}"
    )
    if lookup:
        header += "  class"
    separator = "-" * len(header)
    lines = [header, separator]

    shown = differentials if limit is None else differentials[:limit]
    for differential in shown:
        line = (
            f"{differential.delta_in:0{hex_width}X}".rjust(in_width)
            + "  "
            + f"{differential.delta_out:0{hex_width}X}".rjust(out_width)
            + f"  {differential.weight_in:>{wt_width}}"
            + f"  {differential.weight_out:>{wt_width}}"
            + f"  {differential.weight:>{wt_width}}"
            + f"  {differential.count:>{count_width}}"
        )
        category = lookup.get(
            (differential.delta_in, differential.delta_out)
        )
        if lookup:
            line += f"  {category.value if category else ''}"
        lines.append(line)

    if limit is not None and len(differentials) > limit:
        lines.append(
            f"... {len(differentials) - limit} more "
            f"(use --limit 0 to show all)"
        )
    return "\n".join(lines)


def format_differential_line(differential: Differential) -> str:
    """One bit-vector line of the Possibles/Impossibles report.

    The first ``n`` bits are the input difference and the next ``n`` bits
    are the output difference, e.g. ``(0,0,0,1,0,0,1,1)`` for the 4-bit
    path ``Δin = 0001`` and ``Δout = 0011``.
    """
    return "(" + ",".join(
        differential.delta_in_bin + differential.delta_out_bin
    ) + ")"


def write_differential_report(
    path: str | Path,
    sbox: SBox,
    *,
    include_zero_path: bool = True,
) -> Path:
    """Write all possible and impossible paths in two labelled sections.

    The output has the form::

        Possibles:

        (0,0,0,1,0,0,1,1)
        ...

        Impossibles:

        (0,0,1,0,0,0,0,0)
        ...

    Each line is a ``2n``-bit vector: the first ``n`` bits encode the input
    difference and the next ``n`` bits encode the output difference.

    ``include_zero_path`` controls whether the trivial ``(0,0)`` path is
    listed in the possible section (it is included by default, matching the
    thesis's 2^n x 2^n counting convention).
    """
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    possible = sorted(
        sbox.possible_differentials(include_zero_path=include_zero_path),
        key=lambda differential: (
            differential.delta_in,
            differential.delta_out,
        ),
    )
    impossible = sorted(
        sbox.impossible_differentials(),
        key=lambda differential: (
            differential.delta_in,
            differential.delta_out,
        ),
    )

    lines = ["Possibles:", ""]
    lines.extend(format_differential_line(d) for d in possible)
    lines.extend(["", "Impossibles:", ""])
    lines.extend(format_differential_line(d) for d in impossible)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_ddt_csv(path: str | Path, sbox: SBox) -> Path:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["delta_in"] + list(range(sbox.size)))
        for delta_in, row in enumerate(sbox.ddt):
            writer.writerow([delta_in] + list(row))
    return path


def write_differentials_csv(
    path: str | Path,
    sbox: SBox,
    differentials: Sequence[Differential],
    classes: Mapping[ImpossibleClass, Sequence[Differential]] | None = None,
) -> Path:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    lookup = _class_lookup(classes)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "delta_in",
                "delta_in_hex",
                "delta_in_bin",
                "wt_in",
                "delta_out",
                "delta_out_hex",
                "delta_out_bin",
                "wt_out",
                "wt_total",
                "count",
                "possible",
                "class",
            ]
        )
        for differential in differentials:
            category = lookup.get(
                (differential.delta_in, differential.delta_out)
            )
            writer.writerow(
                [
                    differential.delta_in,
                    differential.delta_in_hex,
                    differential.delta_in_bin,
                    differential.weight_in,
                    differential.delta_out,
                    differential.delta_out_hex,
                    differential.delta_out_bin,
                    differential.weight_out,
                    differential.weight,
                    differential.count,
                    int(differential.possible),
                    category.value if category else "",
                ]
            )
    return path


def differential_to_dict(
    differential: Differential,
    category: ImpossibleClass | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "delta_in": differential.delta_in,
        "delta_in_hex": differential.delta_in_hex,
        "delta_in_bin": differential.delta_in_bin,
        "wt_in": differential.weight_in,
        "delta_out": differential.delta_out,
        "delta_out_hex": differential.delta_out_hex,
        "delta_out_bin": differential.delta_out_bin,
        "wt_out": differential.weight_out,
        "wt_total": differential.weight,
        "count": differential.count,
        "possible": differential.possible,
    }
    if category is not None:
        payload["class"] = category.value
    return payload


def write_differentials_json(
    path: str | Path,
    sbox: SBox,
    differentials: Sequence[Differential],
    classes: Mapping[ImpossibleClass, Sequence[Differential]] | None = None,
    kind: str | None = None,
) -> Path:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    lookup = _class_lookup(classes)
    payload = {
        "sbox": {
            "name": sbox.name,
            "bits": sbox.bits,
            "hex": sbox.to_hex,
            "table": list(sbox.table),
        },
        "summary": asdict(sbox.summary()),
        "kind": kind,
        "count": len(differentials),
        "differentials": [
            differential_to_dict(
                differential,
                lookup.get(
                    (differential.delta_in, differential.delta_out)
                ),
            )
            for differential in differentials
        ],
    }
    path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return path
