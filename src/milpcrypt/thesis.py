"""Automated consistency checks against the 2021 thesis.

The reference numbers come from:

    Can Turesin, "On Measuring Security Bounds of Some Ciphers Using Mixed
    Integer Linear Programming (MILP) Approach", METU, September 2021.

This module deliberately treats the printed DDT tables as data to be checked,
not as ground truth: the PRESENT table (Table 3.2) does not match the PRESENT
S-box (Table 3.1).  ``run_checks`` reports that discrepancy explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .presets import get_preset
from .sbox import SBox


@dataclass(frozen=True)
class ThesisClaim:
    key: str
    paper_name: str
    possible: int
    impossible: int
    branch_number: int
    residual: int
    ddt_table: str


CLAIMS: dict[str, ThesisClaim] = {
    "present": ThesisClaim(
        key="present",
        paper_name="PRESENT",
        possible=97,
        impossible=159,
        branch_number=3,
        residual=118,
        ddt_table="Table 3.2",
    ),
    "prince": ThesisClaim(
        key="prince",
        paper_name="PRINCE",
        possible=106,
        impossible=150,
        branch_number=2,
        residual=120,
        ddt_table="Table 3.4",
    ),
    "prince-inverse": ThesisClaim(
        key="prince-inverse",
        paper_name="PRINCE inverse",
        possible=106,
        impossible=150,
        branch_number=2,
        residual=120,
        ddt_table="Table 3.6",
    ),
    "klein": ThesisClaim(
        key="klein",
        paper_name="KLEIN",
        possible=106,
        impossible=150,
        branch_number=2,
        residual=120,
        ddt_table="Table 3.8",
    ),
}


def _parse_ddt_text(text: str) -> tuple[tuple[int, ...], ...]:
    rows = []
    for line in text.strip().splitlines():
        values = tuple(int(token) for token in line.split())
        if values:
            rows.append(values)
    return tuple(rows)


# The four DDTs exactly as printed in the thesis PDF.  Each row is one input
# difference, each column one output difference.
PRINTED_DDTS: dict[str, tuple[tuple[int, ...], ...]] = {
    "present": _parse_ddt_text(
        """
        16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 0 0 0 2 2 2 2 0 0 0 0 2 2 2 2
        0 2 0 2 0 0 0 4 0 2 2 0 0 0 2 2
        0 2 0 2 0 0 4 0 0 2 2 0 0 0 2 2
        0 0 0 0 0 0 0 0 0 0 4 4 2 2 2 2
        0 0 0 0 2 2 2 2 0 0 4 4 0 0 0 0
        0 2 0 2 0 4 0 0 0 2 2 0 2 2 0 0
        0 2 0 2 4 0 0 0 0 2 2 0 2 2 0 0
        0 0 0 0 0 0 0 0 0 0 0 0 4 4 4 4
        0 4 4 0 0 0 0 0 0 4 0 4 0 0 0 0
        0 0 2 2 2 0 0 2 4 0 0 0 0 2 0 2
        0 0 2 2 0 2 2 0 4 0 0 0 2 0 2 0
        0 4 4 0 2 2 2 2 0 0 0 0 0 0 0 0
        0 0 0 0 2 2 2 2 0 4 0 4 0 0 0 0
        0 0 2 2 0 2 2 0 4 0 0 0 0 2 0 2
        0 0 2 2 2 0 0 2 4 0 0 0 2 0 2 0
        """
    ),
    "prince": _parse_ddt_text(
        """
        16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 4 0 0 2 0 2 0 4 2 0 2 0 0 0 0
        0 2 0 4 0 0 0 2 2 0 0 0 0 4 2 0
        0 0 0 0 0 2 2 0 2 2 2 2 2 0 0 2
        0 2 2 4 2 2 0 0 2 0 2 0 0 0 0 0
        0 0 2 2 0 2 0 2 0 2 0 2 2 2 0 0
        0 0 2 2 0 2 2 0 0 2 0 2 0 0 4 0
        0 0 2 0 0 0 2 0 2 0 4 0 0 2 2 2
        0 0 2 0 4 2 0 0 2 2 0 2 0 2 0 0
        0 0 2 2 0 0 0 0 0 2 2 0 4 2 0 2
        0 0 0 2 2 4 0 4 2 0 0 0 0 0 0 2
        0 2 0 0 4 0 0 2 0 0 0 2 2 0 2 2
        0 4 0 0 0 2 2 0 0 0 2 2 2 0 2 0
        0 2 0 0 0 0 0 2 0 4 2 0 0 2 2 2
        0 0 2 0 0 0 4 2 0 0 0 2 2 2 0 2
        0 0 2 0 2 0 2 2 0 0 2 0 2 0 2 2
        """
    ),
    "prince-inverse": _parse_ddt_text(
        """
        16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 4 2 0 2 0 0 0 0 0 0 2 4 2 0 0
        0 0 0 0 2 2 2 2 2 2 0 0 0 0 2 2
        0 0 4 0 4 2 2 0 0 2 2 0 0 0 0 0
        0 2 0 0 2 0 0 0 4 0 2 4 0 0 0 2
        0 0 0 2 2 2 2 0 2 0 4 0 2 0 0 0
        0 2 0 2 0 0 2 2 0 0 0 0 2 0 4 2
        0 0 2 0 0 2 0 0 0 0 4 2 0 2 2 2
        0 4 2 2 2 0 0 2 2 0 2 0 0 0 0 0
        0 2 0 2 0 2 2 0 2 2 0 0 0 4 0 0
        0 0 0 2 2 0 0 4 0 2 0 0 2 2 0 2
        0 2 0 2 0 2 2 0 2 0 0 2 2 0 2 0
        0 0 0 2 0 2 0 0 0 4 0 2 2 0 2 2
        0 0 4 0 0 2 0 2 2 2 0 0 0 2 2 0
        0 0 2 0 0 0 4 2 0 0 0 2 2 2 0 2
        0 0 0 2 0 0 0 2 0 2 2 2 0 2 2 2
        """
    ),
    "klein": _parse_ddt_text(
        """
        16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 0 0 4 2 0 2 0 2 0 0 2 0 0 2 2
        0 0 0 0 0 4 0 0 0 0 2 2 0 4 2 2
        0 4 0 2 2 0 0 0 0 0 2 0 0 2 4 0
        0 2 0 2 2 0 2 0 0 2 0 2 0 2 0 2
        0 0 4 0 0 2 0 2 2 0 2 4 0 0 0 0
        0 2 0 0 2 0 4 0 2 0 2 2 2 0 0 0
        0 0 0 0 0 2 0 2 2 2 0 0 2 0 4 2
        0 2 0 0 0 2 2 2 2 2 0 2 0 0 0 2
        0 0 0 0 2 0 0 2 2 0 0 2 2 2 2 2
        0 0 2 2 0 2 2 0 0 0 4 0 2 0 2 0
        0 2 2 0 2 4 2 0 2 2 0 0 0 0 0 0
        0 0 0 0 0 0 2 2 0 2 2 0 4 2 0 2
        0 0 4 2 2 0 0 0 0 2 0 0 2 2 0 2
        0 2 2 4 0 0 0 4 0 2 2 0 0 0 0 0
        0 2 2 0 2 0 0 2 2 2 0 0 2 2 0 0
        """
    ),
}


@dataclass(frozen=True)
class ThesisCheck:
    group: str
    subject: str
    item: str
    thesis_value: str
    computed_value: str
    ok: bool
    note: str = ""


def _ddt_stats(
    ddt: tuple[tuple[int, ...], ...],
    branch_override: int | None = None,
) -> tuple[int, int, int, int, int, int]:
    """Return (possible, impossible, branch, conflicts, low_weight, residual).

    ``branch_override`` lets a caller apply the branch number claimed in the
    thesis even when the supplied DDT would imply a different one.
    """
    size = len(ddt)
    possible_nonzero = sum(
        1
        for delta_in in range(1, size)
        for delta_out in range(1, size)
        if ddt[delta_in][delta_out] > 0
    )
    zero_path = 1 if ddt[0][0] > 0 else 0
    possible = possible_nonzero + zero_path
    impossible = size * size - possible

    branch = min(
        delta_in.bit_count() + delta_out.bit_count()
        for delta_in in range(1, size)
        for delta_out in range(1, size)
        if ddt[delta_in][delta_out] > 0
    )
    threshold = branch if branch_override is None else branch_override
    conflicts = sum(
        1 for delta_out in range(1, size) if ddt[0][delta_out] == 0
    ) + sum(
        1 for delta_in in range(1, size) if ddt[delta_in][0] == 0
    )
    low_weight = sum(
        1
        for delta_in in range(1, size)
        for delta_out in range(1, size)
        if ddt[delta_in][delta_out] == 0
        and delta_in.bit_count() + delta_out.bit_count() < threshold
    )
    residual = impossible - conflicts - low_weight
    return possible, impossible, branch, conflicts, low_weight, residual


def _check(
    group: str,
    subject: str,
    item: str,
    thesis_value: object,
    computed_value: object,
    note: str = "",
) -> ThesisCheck:
    return ThesisCheck(
        group=group,
        subject=subject,
        item=item,
        thesis_value=str(thesis_value),
        computed_value=str(computed_value),
        ok=str(thesis_value) == str(computed_value),
        note=note,
    )


def run_checks() -> list[ThesisCheck]:
    checks: list[ThesisCheck] = []

    for key, claim in CLAIMS.items():
        sbox: SBox = get_preset(key)
        summary = sbox.summary()

        checks.append(
            _check(
                "Differential counts",
                claim.paper_name,
                "possible paths",
                claim.possible,
                summary.possible,
            )
        )
        checks.append(
            _check(
                "Differential counts",
                claim.paper_name,
                "impossible paths",
                claim.impossible,
                summary.impossible,
            )
        )
        checks.append(
            _check(
                "Differential counts",
                claim.paper_name,
                "differential branch number",
                claim.branch_number,
                summary.branch_number,
            )
        )
        residual_note = ""
        if key == "present":
            printed_stats = _ddt_stats(
                PRINTED_DDTS[key], branch_override=claim.branch_number
            )
            residual_note = (
                "Not reproduced with either table. Correct S-box: "
                f"{summary.impossible} impossible - 30 zero/nonzero - "
                f"{summary.low_weight} low-weight = {summary.other}. "
                f"The printed {claim.ddt_table} gives residual "
                f"{printed_stats[5]} when the claimed branch number "
                f"{claim.branch_number} is applied, also not {claim.residual}. "
                "Please re-check the PRESENT filtering step in Section 3.1.1."
            )
        checks.append(
            _check(
                "Filtered impossible set",
                claim.paper_name,
                "paths left for cutting-off inequalities",
                claim.residual,
                summary.other,
                residual_note,
            )
        )

        printed = PRINTED_DDTS[key]
        actual = sbox.ddt
        mismatches = [
            (delta_in, delta_out, printed[delta_in][delta_out], actual[delta_in][delta_out])
            for delta_in in range(sbox.size)
            for delta_out in range(sbox.size)
            if printed[delta_in][delta_out] != actual[delta_in][delta_out]
        ]
        if mismatches:
            printed_branch = _ddt_stats(printed)[2]
            printed_residual = _ddt_stats(
                printed, branch_override=claim.branch_number
            )[5]
            note = (
                f"{claim.ddt_table} differs from the S-box in "
                f"{len(mismatches)}/{sbox.size * sbox.size} entries. "
                f"First row {mismatches[0][0]:X}: printed output set "
                f"differs from computed. The printed table itself implies "
                f"branch number {printed_branch} and residual "
                f"{printed_residual} under the thesis's branch-number filter."
            )
        else:
            note = f"{claim.ddt_table} matches the S-box exactly."

        checks.append(
            ThesisCheck(
                group="Printed DDT",
                subject=claim.paper_name,
                item=f"{claim.ddt_table} vs S-box",
                thesis_value="matches",
                computed_value=(
                    "matches"
                    if not mismatches
                    else f"{len(mismatches)} mismatched entries"
                ),
                ok=not mismatches,
                note=note,
            )
        )

    return checks


def format_checks(checks: list[ThesisCheck]) -> str:
    lines = [
        "Thesis consistency check",
        "========================",
        "",
    ]
    current_group = None
    for check in checks:
        if check.group != current_group:
            current_group = check.group
            lines.append(f"[{current_group}]")
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"  [{status}] {check.subject} / {check.item}")
        lines.append(f"         thesis   : {check.thesis_value}")
        lines.append(f"         computed : {check.computed_value}")
        if check.note:
            lines.append(f"         note     : {check.note}")
        lines.append("")

    passed = sum(1 for check in checks if check.ok)
    failed = len(checks) - passed
    lines.append(f"Summary: {passed} passed, {failed} failed")
    if failed:
        lines.append(
            "Failures are data-consistency findings, not solver errors; "
            "inspect the notes before using the affected thesis numbers."
        )
    return "\n".join(lines)
