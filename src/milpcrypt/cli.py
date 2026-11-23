"""Command-line interface for milpcrypt."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from . import __version__
from .presets import get_preset, list_presets, resolve_sbox
from .report import (
    format_ddt,
    format_differentials,
    format_summary,
    write_ddt_csv,
    write_differentials_csv,
    write_differentials_json,
)
from .sbox import ImpossibleClass
from .thesis import format_checks, run_checks

_CLASS_CHOICES = {
    "zero-nonzero": ImpossibleClass.ZERO_TO_NONZERO,
    "nonzero-zero": ImpossibleClass.NONZERO_TO_ZERO,
    "low-weight": ImpossibleClass.LOW_WEIGHT,
    "other": ImpossibleClass.OTHER,
}


def _add_sbox_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "spec",
        help=(
            "S-box preset name (present, prince, prince-inverse, klein), "
            "a file path, a hex nibble string, or a comma-separated "
            "value list"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="milpcrypt",
        description=(
            "MILP cryptanalysis toolkit: extract possible and impossible "
            "S-box differential paths."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    presets = subparsers.add_parser(
        "presets", help="list built-in S-box presets"
    )
    presets.set_defaults(handler=_cmd_presets)

    info = subparsers.add_parser(
        "info", help="show DDT summary and impossible-path classes"
    )
    _add_sbox_argument(info)
    info.add_argument("--json", action="store_true", help="emit JSON")
    info.set_defaults(handler=_cmd_info)

    ddt = subparsers.add_parser("ddt", help="print or export the DDT")
    _add_sbox_argument(ddt)
    ddt.add_argument(
        "--csv", metavar="PATH", help="write the full DDT to a CSV file"
    )
    ddt.add_argument(
        "--max-bits",
        type=int,
        default=5,
        help="largest DDT allowed in the terminal (default: 5)",
    )
    ddt.set_defaults(handler=_cmd_ddt)

    diff = subparsers.add_parser(
        "differentials", help="list possible or impossible differential paths"
    )
    _add_sbox_argument(diff)
    diff.add_argument(
        "--kind",
        choices=("all", "possible", "impossible"),
        default="all",
        help="which paths to list (default: all)",
    )
    diff.add_argument(
        "--class",
        dest="category",
        choices=tuple(_CLASS_CHOICES),
        help="filter impossible paths by thesis class",
    )
    diff.add_argument(
        "--limit",
        type=int,
        default=60,
        help="terminal rows to show; 0 means all (default: 60)",
    )
    diff.add_argument(
        "--include-zero-path",
        action="store_true",
        help="include the (0,0) path when listing possible paths",
    )
    diff.add_argument(
        "--csv", metavar="PATH", help="write matching paths to CSV"
    )
    diff.add_argument(
        "--json", metavar="PATH", help="write matching paths to JSON"
    )
    diff.set_defaults(handler=_cmd_differentials)

    thesis = subparsers.add_parser(
        "thesis-check",
        help="compare computed values with the numbers printed in the thesis",
    )
    thesis.add_argument(
        "--strict",
        action="store_true",
        help="exit with status 1 if any consistency check fails",
    )
    thesis.add_argument("--json", action="store_true", help="emit JSON")
    thesis.set_defaults(handler=_cmd_thesis_check)

    return parser


def _cmd_presets(args: argparse.Namespace) -> int:
    print(
        f"{'key':<16} {'name':<16} {'bits':>4}  {'S-box':<20} source"
    )
    print("-" * 100)
    for preset in list_presets():
        sbox = get_preset(preset.key)
        print(
            f"{preset.key:<16} {preset.name:<16} {sbox.bits:>4}  "
            f"{preset.table_hex:<20} {preset.source}"
        )
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    sbox = resolve_sbox(args.spec)
    summary = sbox.summary()
    if args.json:
        payload = {
            "sbox": {
                "name": sbox.name,
                "bits": sbox.bits,
                "hex": sbox.to_hex,
                "table": list(sbox.table),
            },
            "summary": asdict(summary),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_summary(sbox, summary))
    return 0


def _cmd_ddt(args: argparse.Namespace) -> int:
    sbox = resolve_sbox(args.spec)
    if args.csv:
        path = write_ddt_csv(args.csv, sbox)
        print(
            f"Wrote {sbox.size}x{sbox.size} DDT for {sbox.name} to {path}"
        )
        return 0
    print(format_ddt(sbox, max_bits=args.max_bits))
    return 0


def _cmd_differentials(args: argparse.Namespace) -> int:
    if args.limit < 0:
        raise ValueError("--limit must be nonnegative")
    if args.category and args.kind != "impossible":
        raise ValueError("--class can only be used with --kind impossible")

    sbox = resolve_sbox(args.spec)
    classes = sbox.classify_impossible()

    if args.kind == "possible":
        differentials = list(
            sbox.possible_differentials(
                include_zero_path=args.include_zero_path
            )
        )
        display_classes = None
        label = "possible"
    elif args.kind == "impossible":
        if args.category:
            category = _CLASS_CHOICES[args.category]
            differentials = list(classes[category])
            label = f"impossible ({category.value})"
        else:
            differentials = list(sbox.impossible_differentials())
            label = "impossible"
        display_classes = classes
    else:
        differentials = list(sbox.iter_all_differentials())
        display_classes = None
        label = "all"

    differentials.sort(key=lambda d: (d.delta_in, d.delta_out))

    exports: list[str] = []
    json_kind = label.replace(" ", ":")
    if args.csv:
        path = write_differentials_csv(
            args.csv,
            sbox,
            differentials,
            classes if args.kind == "impossible" else None,
        )
        exports.append(str(path))
    if args.json:
        path = write_differentials_json(
            args.json,
            sbox,
            differentials,
            classes if args.kind == "impossible" else None,
            kind=json_kind,
        )
        exports.append(str(path))

    if args.kind == "impossible":
        zero_path_text = "n/a"
    else:
        zero_path_included = args.kind == "all" or args.include_zero_path
        zero_path_text = "yes" if zero_path_included else "no"
    print(
        f"{sbox.name}: {len(differentials)} {label} differential paths "
        f"(zero path included: {zero_path_text})"
    )
    if exports:
        print("Wrote: " + ", ".join(exports))
        return 0

    limit = None if args.limit == 0 else args.limit
    print(
        format_differentials(
            sbox,
            differentials,
            limit=limit,
            classes=display_classes,
        )
    )
    return 0


def _cmd_thesis_check(args: argparse.Namespace) -> int:
    checks = run_checks()
    passed = sum(1 for check in checks if check.ok)
    failed = len(checks) - passed

    if args.json:
        payload = {
            "passed": passed,
            "failed": failed,
            "checks": [asdict(check) for check in checks],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_checks(checks))

    if args.strict and failed:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
