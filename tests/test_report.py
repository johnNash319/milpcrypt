from milpcrypt import get_preset, write_differential_report
from milpcrypt.report import format_differential_line


def _read_sections(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("Possibles:\n\n")
    possible_text, impossible_text = text.split("\nImpossibles:\n\n", 1)
    possible = [line for line in possible_text.splitlines()[2:] if line]
    impossible = [line for line in impossible_text.splitlines() if line]
    return possible, impossible


def test_report_format_and_counts(tmp_path):
    sbox = get_preset("present")
    path = write_differential_report(tmp_path / "present.txt", sbox)
    possible, impossible = _read_sections(path)

    assert len(possible) == 97
    assert len(impossible) == 159
    assert possible[0] == "0x0 -> 0x0  wt=0  count=16"
    assert possible[1] == "0x1 -> 0x3  wt=3  count=4"
    assert impossible[0] == "0x0 -> 0x1  wt=1  count=0"
    assert all("count=0" in line for line in impossible)
    assert all("wt=" in line and "count=" in line for line in possible)


def test_report_can_skip_zero_path(tmp_path):
    sbox = get_preset("present")
    path = write_differential_report(
        tmp_path / "present_nonzero.txt",
        sbox,
        include_zero_path=False,
    )
    possible, impossible = _read_sections(path)

    assert len(possible) == 96
    assert possible[0] == "0x1 -> 0x3  wt=3  count=4"
    assert len(impossible) == 159


def test_sbox_method_writes_report(tmp_path):
    sbox = get_preset("klein")
    path = sbox.write_differential_report(tmp_path / "klein.txt")
    possible, impossible = _read_sections(path)
    assert len(possible) == 106
    assert len(impossible) == 150


def test_differential_line_format():
    sbox = get_preset("present")
    line = format_differential_line(sbox.differential(1, 3))
    assert line == "0x1 -> 0x3  wt=3  count=4"
