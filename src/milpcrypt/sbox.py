"""S-box differential analysis.

The core object is :class:`SBox`, which computes the difference distribution
table (DDT) of an arbitrary bit-oriented S-box and exposes its possible and
impossible input/output difference pairs.  The classification of impossible
paths follows the contribution of the thesis:

    zero input -> nonzero output
    nonzero input -> zero output
    total Hamming weight below the S-box differential branch number
    other (the paths that cutting-off inequalities have to eliminate)

Only the Python standard library is required for this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Sequence

# Building a full DDT costs O(2^(2n)) operations.  Twelve bits is already
# 16.7M pairs; larger S-boxes should be handled by a different representation.
MAX_BITS = 12

_HEX_CHARS = frozenset("0123456789abcdefABCDEF")


class ImpossibleClass(str, Enum):
    """Categories of impossible S-box differential paths."""

    ZERO_TO_NONZERO = "zero-to-nonzero"
    NONZERO_TO_ZERO = "nonzero-to-zero"
    LOW_WEIGHT = "low-weight"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            ImpossibleClass.ZERO_TO_NONZERO: "zero input -> nonzero output",
            ImpossibleClass.NONZERO_TO_ZERO: "nonzero input -> zero output",
            ImpossibleClass.LOW_WEIGHT: "weight below branch number",
            ImpossibleClass.OTHER: "other (cutting-off target)",
        }[self]


@dataclass(frozen=True, slots=True)
class Differential:
    """One input/output difference pair of an S-box."""

    delta_in: int
    delta_out: int
    count: int
    bits: int

    @property
    def possible(self) -> bool:
        return self.count > 0

    @property
    def weight_in(self) -> int:
        return self.delta_in.bit_count()

    @property
    def weight_out(self) -> int:
        return self.delta_out.bit_count()

    @property
    def weight(self) -> int:
        """Total Hamming weight of the 2n-bit differential path."""
        return self.weight_in + self.weight_out

    @property
    def is_zero_path(self) -> bool:
        return self.delta_in == 0 and self.delta_out == 0

    @property
    def hex_width(self) -> int:
        return max(1, (self.bits + 3) // 4)

    @property
    def delta_in_hex(self) -> str:
        return f"{self.delta_in:0{self.hex_width}X}"

    @property
    def delta_out_hex(self) -> str:
        return f"{self.delta_out:0{self.hex_width}X}"

    @property
    def delta_in_bin(self) -> str:
        return f"{self.delta_in:0{self.bits}b}"

    @property
    def delta_out_bin(self) -> str:
        return f"{self.delta_out:0{self.bits}b}"


@dataclass(frozen=True, slots=True)
class SBoxSummary:
    """Aggregate differential statistics of an S-box."""

    name: str
    bits: int
    size: int
    is_permutation: bool
    differential_uniformity: int
    branch_number: int
    possible: int
    possible_nonzero: int
    impossible: int
    zero_to_nonzero: int
    nonzero_to_zero: int
    low_weight: int
    other: int


def _parse_int(token: str) -> int:
    try:
        return int(token, 0)
    except ValueError:
        # Accept zero-padded decimal values such as "08", which base 0
        # rejects as an invalid octal literal.
        return int(token, 10)


def _parse_table(table: Sequence[int] | str) -> tuple[int, ...]:
    """Parse an S-box from values, a hex nibble string, or a value list.

    Accepted forms:

    * ``"c56b90ad3ef84712"`` -- one hexadecimal digit per S-box value,
      whitespace/newlines are ignored, an optional leading ``0x`` is allowed.
    * ``"12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2"`` -- comma-separated values
      (decimal or ``0x`` prefixed).
    * a sequence of integers.
    """

    if isinstance(table, str):
        text = table.strip()
        if not text:
            raise ValueError("empty S-box table")

        if "," in text or ";" in text:
            tokens = [token for token in re.split(r"[\s,;]+", text) if token]
            try:
                values = [_parse_int(token) for token in tokens]
            except ValueError as exc:
                raise ValueError(
                    "value lists must contain decimal or 0x-prefixed integers"
                ) from exc
        else:
            compact = re.sub(r"\s+", "", text)
            if compact[:2].lower() == "0x":
                compact = compact[2:]
            if not compact or any(char not in _HEX_CHARS for char in compact):
                raise ValueError(
                    "expected a preset name, a hex nibble string, or a "
                    "comma-separated value list"
                )
            values = [int(char, 16) for char in compact]
    else:
        values = list(table)

    if len(values) < 2:
        raise ValueError("an S-box must have at least two values")

    size = len(values)
    if size & (size - 1):
        raise ValueError(
            f"S-box table length must be a power of two, got {size}"
        )

    bits = size.bit_length() - 1
    if bits > MAX_BITS:
        raise ValueError(
            f"{bits}-bit S-boxes are not supported (limit: {MAX_BITS} bits)"
        )

    for index, value in enumerate(values):
        if not isinstance(value, int):
            raise ValueError(f"S-box value at index {index} is not an integer")
        if not 0 <= value < size:
            raise ValueError(
                f"S-box value at index {index} is {value}, outside 0..{size - 1}"
            )

    return tuple(values)


class SBox:
    """A bit-oriented substitution box and its differential properties."""

    def __init__(self, table: Sequence[int] | str, name: str | None = None):
        self.table = _parse_table(table)
        self.name = name or "custom"
        self.bits = len(self.table).bit_length() - 1
        self._ddt = self._build_ddt()
        self._possible: tuple[Differential, ...] | None = None
        self._impossible: tuple[Differential, ...] | None = None

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_hex(cls, hex_string: str, name: str | None = None) -> "SBox":
        return cls(hex_string, name=name)

    @classmethod
    def from_values(
        cls, values: Sequence[int], name: str | None = None
    ) -> "SBox":
        return cls(values, name=name)

    def inverse(self) -> "SBox":
        if not self.is_permutation:
            raise ValueError("only a permutation S-box has an inverse")
        inverse = [0] * self.size
        for x, y in enumerate(self.table):
            inverse[y] = x
        return SBox(inverse, name=f"{self.name}^-1")

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------
    @property
    def size(self) -> int:
        return len(self.table)

    @property
    def is_permutation(self) -> bool:
        return len(set(self.table)) == self.size

    @property
    def to_hex(self) -> str:
        width = max(1, (self.bits + 3) // 4)
        return "".join(f"{value:0{width}X}" for value in self.table)

    @property
    def ddt(self) -> tuple[tuple[int, ...], ...]:
        return self._ddt

    @property
    def difference_distribution_table(self) -> tuple[tuple[int, ...], ...]:
        return self._ddt

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, index: int) -> int:
        return self.table[index]

    def __iter__(self) -> Iterator[int]:
        return iter(self.table)

    def __repr__(self) -> str:
        return (
            f"SBox(name={self.name!r}, bits={self.bits}, hex={self.to_hex})"
        )

    # ------------------------------------------------------------------
    # DDT and differential paths
    # ------------------------------------------------------------------
    def _build_ddt(self) -> tuple[tuple[int, ...], ...]:
        size = self.size
        table = self.table
        ddt = [[0] * size for _ in range(size)]
        for delta_in in range(size):
            row = ddt[delta_in]
            for x in range(size):
                row[table[x] ^ table[x ^ delta_in]] += 1
        return tuple(tuple(row) for row in ddt)

    def difference_count(self, delta_in: int, delta_out: int) -> int:
        """Number of x with S(x) xor S(x xor delta_in) = delta_out."""
        if not 0 <= delta_in < self.size:
            raise ValueError(f"delta_in out of range: {delta_in}")
        if not 0 <= delta_out < self.size:
            raise ValueError(f"delta_out out of range: {delta_out}")
        return self._ddt[delta_in][delta_out]

    def is_possible(self, delta_in: int, delta_out: int) -> bool:
        return self.difference_count(delta_in, delta_out) > 0

    def differential(self, delta_in: int, delta_out: int) -> Differential:
        return Differential(
            delta_in=delta_in,
            delta_out=delta_out,
            count=self.difference_count(delta_in, delta_out),
            bits=self.bits,
        )

    def possible_differentials(
        self, include_zero_path: bool = True
    ) -> tuple[Differential, ...]:
        """All differential paths with nonzero probability.

        The ``(0, 0)`` path is included by default because it is part of the
        usual 2^n x 2^n S-box differential pair count (and is the convention
        used in the thesis).  Set ``include_zero_path=False`` to drop it.
        """
        if self._possible is None:
            possible: list[Differential] = []
            for delta_in in range(self.size):
                row = self._ddt[delta_in]
                for delta_out, count in enumerate(row):
                    if count > 0:
                        possible.append(
                            Differential(
                                delta_in, delta_out, count, self.bits
                            )
                        )
            self._possible = tuple(possible)
        if include_zero_path:
            return self._possible
        return tuple(d for d in self._possible if not d.is_zero_path)

    def impossible_differentials(self) -> tuple[Differential, ...]:
        """All input/output difference pairs that occur with probability zero."""
        if self._impossible is None:
            impossible: list[Differential] = []
            for delta_in in range(self.size):
                row = self._ddt[delta_in]
                for delta_out, count in enumerate(row):
                    if count == 0:
                        impossible.append(
                            Differential(
                                delta_in, delta_out, 0, self.bits
                            )
                        )
            self._impossible = tuple(impossible)
        return self._impossible

    def iter_all_differentials(self) -> Iterator[Differential]:
        for delta_in in range(self.size):
            for delta_out in range(self.size):
                yield self.differential(delta_in, delta_out)

    def differential_uniformity(self) -> int:
        """Maximum DDT entry outside the zero-input row."""
        return max(
            self._ddt[delta_in][delta_out]
            for delta_in in range(1, self.size)
            for delta_out in range(self.size)
        )

    def branch_number(self) -> int:
        """Differential branch number of the S-box.

        ``min(wt(delta_in) + wt(delta_out))`` over all possible paths with a
        nonzero input difference.  Every nonzero path below this weight is
        therefore impossible.
        """
        weights = [
            differential.weight
            for differential in self.possible_differentials(
                include_zero_path=False
            )
        ]
        return min(weights) if weights else 0

    # ------------------------------------------------------------------
    # Thesis-specific impossible-path classification
    # ------------------------------------------------------------------
    def classify_impossible(
        self, threshold: int | None = None
    ) -> dict[ImpossibleClass, tuple[Differential, ...]]:
        """Split impossible paths into the classes used in the thesis.

        ``threshold`` defaults to the S-box differential branch number.  The
        first two classes are eliminated by Sun et al.'s zero/nonzero
        constraints, ``LOW_WEIGHT`` by the differential branch number model,
        and ``OTHER`` is what cutting-off inequalities must eliminate.
        """
        branch = self.branch_number() if threshold is None else threshold
        classes: dict[ImpossibleClass, list[Differential]] = {
            member: [] for member in ImpossibleClass
        }

        for differential in self.impossible_differentials():
            if differential.delta_in == 0:
                category = ImpossibleClass.ZERO_TO_NONZERO
            elif differential.delta_out == 0:
                category = ImpossibleClass.NONZERO_TO_ZERO
            elif differential.weight < branch:
                category = ImpossibleClass.LOW_WEIGHT
            else:
                category = ImpossibleClass.OTHER
            classes[category].append(differential)

        return {category: tuple(items) for category, items in classes.items()}

    def summary(self) -> SBoxSummary:
        classes = self.classify_impossible()
        possible = self.possible_differentials(include_zero_path=True)
        impossible = self.impossible_differentials()
        zero_path = 1 if self._ddt[0][0] > 0 else 0
        return SBoxSummary(
            name=self.name,
            bits=self.bits,
            size=self.size,
            is_permutation=self.is_permutation,
            differential_uniformity=self.differential_uniformity(),
            branch_number=self.branch_number(),
            possible=len(possible),
            possible_nonzero=len(possible) - zero_path,
            impossible=len(impossible),
            zero_to_nonzero=len(classes[ImpossibleClass.ZERO_TO_NONZERO]),
            nonzero_to_zero=len(classes[ImpossibleClass.NONZERO_TO_ZERO]),
            low_weight=len(classes[ImpossibleClass.LOW_WEIGHT]),
            other=len(classes[ImpossibleClass.OTHER]),
        )
