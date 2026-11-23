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
    assert possible[0] == "(0,0,0,0,0,0,0,0)"
    assert possible[1] == "(0,0,0,1,0,0,1,1)"
    assert impossible[0] == "(0,0,0,0,0,0,0,1)"
    assert all(
        len(line) == 17
        and line.startswith("(")
        and line.endswith(")")
        and set(line[1:-1].split(",")) <= {"0", "1"}
        for line in possible + impossible
    )


def test_report_can_skip_zero_path(tmp_path):
    sbox = get_preset("present")
    path = write_differential_report(
        tmp_path / "present_nonzero.txt",
        sbox,
        include_zero_path=False,
    )
    possible, impossible = _read_sections(path)

    assert len(possible) == 96
    assert possible[0] == "(0,0,0,1,0,0,1,1)"
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
    assert line == "(0,0,0,1,0,0,1,1)"

    inverse_line = format_differential_line(sbox.differential(0xA, 5))
    assert inverse_line == "(1,0,1,0,0,1,0,1)"
