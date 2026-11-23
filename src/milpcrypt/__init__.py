"""milpcrypt: MILP cryptanalysis toolkit.

The project accompanies the thesis "On Measuring Security Bounds of Some
Ciphers Using Mixed Integer Linear Programming (MILP) Approach".

Current milestone: exact S-box differential-path extraction and the
impossible-path classification used by the thesis's cutting-off-inequality
reduction.
"""

from __future__ import annotations

from .presets import PRESETS, get_preset, list_presets, resolve_sbox
from .report import write_differential_report
from .sbox import (
    Differential,
    ImpossibleClass,
    SBox,
    SBoxSummary,
)

__version__ = "0.2.0"

__all__ = [
    "Differential",
    "ImpossibleClass",
    "PRESETS",
    "SBox",
    "SBoxSummary",
    "get_preset",
    "list_presets",
    "resolve_sbox",
    "write_differential_report",
]
