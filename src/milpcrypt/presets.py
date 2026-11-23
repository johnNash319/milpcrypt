"""Built-in S-box presets used in the thesis.

The three ciphers studied in Chapter 3 are PRESENT, PRINCE (including its
inverse S-box for the second half of the cipher), and KLEIN.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .sbox import SBox


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    table_hex: str
    source: str
    note: str = ""


PRESETS: dict[str, Preset] = {
    "present": Preset(
        key="present",
        name="PRESENT",
        table_hex="c56b90ad3ef84712",
        source="Thesis Table 3.1; Bogdanov et al., PRESENT (2007)",
        note="4-bit S-box of the 31-round SPN block cipher",
    ),
    "prince": Preset(
        key="prince",
        name="PRINCE",
        table_hex="bf32ac916780e5d4",
        source="Thesis Table 3.3; Borghoff et al., PRINCE (2012)",
        note="4-bit S-box used in rounds 1-6",
    ),
    "prince-inverse": Preset(
        key="prince-inverse",
        name="PRINCE inverse",
        table_hex="b732fd89a6405ec1",
        source="Thesis Table 3.5; inverse of the PRINCE S-box",
        note="4-bit inverse S-box used in the second half of PRINCE",
    ),
    "klein": Preset(
        key="klein",
        name="KLEIN",
        table_hex="74a91fb0c3268ed5",
        source="Thesis Table 3.7; Gong et al., KLEIN (2011)",
        note="4-bit S-box of the KLEIN family of block ciphers",
    ),
}

_ALIASES = {
    "present-sbox": "present",
    "prince-inv": "prince-inverse",
    "princeinverse": "prince-inverse",
    "prince_inverse": "prince-inverse",
    "klein-sbox": "klein",
}


def _normalise(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def list_presets() -> tuple[Preset, ...]:
    return tuple(PRESETS.values())


def get_preset(key: str) -> SBox:
    normalised = _normalise(key)
    normalised = _ALIASES.get(normalised, normalised)
    try:
        preset = PRESETS[normalised]
    except KeyError as exc:
        available = ", ".join(PRESETS)
        raise ValueError(
            f"unknown S-box preset {key!r} (available: {available})"
        ) from exc
    return SBox.from_hex(preset.table_hex, name=preset.name)


def resolve_sbox(spec: str) -> SBox:
    """Resolve a preset name, file path, or inline S-box specification."""

    normalised = _normalise(spec)
    normalised = _ALIASES.get(normalised, normalised)
    if normalised in PRESETS:
        return get_preset(normalised)

    try:
        path = Path(spec).expanduser()
        is_file = path.is_file()
    except OSError:
        is_file = False
    if is_file:
        return SBox(path.read_text(encoding="utf-8"), name=path.stem)

    return SBox(spec, name="custom")
