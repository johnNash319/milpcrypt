import csv

import pytest

from milpcrypt.presets import get_preset
from milpcrypt.sbox import ImpossibleClass, SBox


def test_present_ddt_row_one():
    sbox = get_preset("present")
    outputs = [b for b in range(16) if sbox.ddt[1][b] > 0]
    assert outputs == [3, 7, 9, 13]


def test_prince_ddt_row_one():
    sbox = get_preset("prince")
    outputs = [b for b in range(16) if sbox.ddt[1][b] > 0]
    assert outputs == [1, 4, 6, 8, 9, 11]


def test_prince_inverse_ddt_row_one():
    sbox = get_preset("prince-inverse")
    outputs = [b for b in range(16) if sbox.ddt[1][b] > 0]
    assert outputs == [1, 2, 4, 11, 12, 13]


def test_klein_ddt_row_one():
    sbox = get_preset("klein")
    outputs = [b for b in range(16) if sbox.ddt[1][b] > 0]
    assert outputs == [3, 4, 6, 8, 11, 14, 15]


@pytest.mark.parametrize(
    "key",
    ["present", "prince", "prince-inverse", "klein"],
)
def test_ddt_rows_and_columns_sum_to_size(key):
    sbox = get_preset(key)
    assert all(sum(row) == sbox.size for row in sbox.ddt)
    assert all(
        sum(sbox.ddt[row][column] for row in range(sbox.size))
        == sbox.size
        for column in range(sbox.size)
    )
    assert sbox.ddt[0] == (sbox.size,) + (0,) * (sbox.size - 1)


@pytest.mark.parametrize(
    ("key", "possible", "impossible", "branch", "low_weight", "other"),
    [
        ("present", 97, 159, 3, 16, 113),
        ("prince", 106, 150, 2, 0, 120),
        ("prince-inverse", 106, 150, 2, 0, 120),
        ("klein", 106, 150, 2, 0, 120),
    ],
)
def test_summary_counts(key, possible, impossible, branch, low_weight, other):
    summary = get_preset(key).summary()
    assert summary.possible == possible
    assert summary.impossible == impossible
    assert summary.branch_number == branch
    assert summary.low_weight == low_weight
    assert summary.other == other
    assert summary.is_permutation


@pytest.mark.parametrize(
    "key",
    ["present", "prince", "prince-inverse", "klein"],
)
def test_classification_partitions_impossible_paths(key):
    sbox = get_preset(key)
    classes = sbox.classify_impossible()
    total = sum(len(items) for items in classes.values())
    assert total == len(sbox.impossible_differentials())
    assert len(classes[ImpossibleClass.ZERO_TO_NONZERO]) == 15
    assert len(classes[ImpossibleClass.NONZERO_TO_ZERO]) == 15
    assert all(
        d.weight < sbox.branch_number()
        for d in classes[ImpossibleClass.LOW_WEIGHT]
    )
    assert all(
        d.weight >= sbox.branch_number()
        for d in classes[ImpossibleClass.OTHER]
    )


def test_zero_path_included_by_default():
    sbox = get_preset("present")
    assert sbox.possible_differentials()[0].is_zero_path
    without = sbox.possible_differentials(include_zero_path=False)
    assert all(not d.is_zero_path for d in without)
    assert len(without) == len(sbox.possible_differentials()) - 1


def test_inverse_ddt_is_transpose():
    sbox = get_preset("prince")
    inverse = sbox.inverse()
    assert inverse.is_permutation
    assert inverse.to_hex == "B732FD89A6405EC1"
    for delta_in in range(16):
        for delta_out in range(16):
            assert (
                inverse.ddt[delta_out][delta_in]
                == sbox.ddt[delta_in][delta_out]
            )


def test_parse_hex_and_value_list():
    assert SBox("c56b90ad3ef84712").table == get_preset("present").table
    assert (
        SBox("12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2").table
        == get_preset("present").table
    )
    assert (
        SBox("c5 6b 90 ad 3e f8 47 12").table
        == get_preset("present").table
    )
    assert (
        SBox("12,05,06,11,09,00,10,13,03,14,15,08,04,07,01,02").table
        == get_preset("present").table
    )
    assert SBox("0xc56b90ad3ef84712").table == get_preset("present").table


def test_invalid_tables():
    with pytest.raises(ValueError, match="power of two"):
        SBox("abc")
    with pytest.raises(ValueError, match="outside"):
        SBox("1,2")
    with pytest.raises(ValueError, match="at least two"):
        SBox("a")
    with pytest.raises(ValueError, match="empty"):
        SBox("   ")


def test_non_permutation_is_detected_and_has_no_inverse():
    sbox = SBox("0,0,0,0", name="constant")
    assert not sbox.is_permutation
    summary = sbox.summary()
    assert summary.possible == 4
    assert summary.possible_nonzero == 3
    assert summary.branch_number == 1
    with pytest.raises(ValueError, match="permutation"):
        sbox.inverse()


def test_csv_writer_counts(tmp_path):
    from milpcrypt.report import write_differentials_csv

    sbox = get_preset("present")
    path = write_differentials_csv(
        tmp_path / "impossible.csv",
        sbox,
        sbox.impossible_differentials(),
        sbox.classify_impossible(),
    )
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 159
    assert {row["possible"] for row in rows} == {"0"}
    assert {row["class"] for row in rows} == {
        "zero-to-nonzero",
        "nonzero-to-zero",
        "low-weight",
        "other",
    }
