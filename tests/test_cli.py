import json

from milpcrypt.cli import main
from milpcrypt.presets import get_preset


def test_cli_info(capsys):
    assert main(["info", "present"]) == 0
    output = capsys.readouterr().out
    assert "PRESENT" in output
    assert "possible            : 97" in output
    assert "other               : 113" in output


def test_cli_info_json(capsys):
    assert main(["info", "klein", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sbox"]["bits"] == 4
    assert payload["summary"]["impossible"] == 150


def test_cli_differentials_csv(tmp_path, capsys):
    path = tmp_path / "present_impossible.csv"
    code = main(
        [
            "differentials",
            "present",
            "--kind",
            "impossible",
            "--csv",
            str(path),
        ]
    )
    assert code == 0
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 160
    assert "159 impossible" in capsys.readouterr().out


def test_cli_differentials_class_filter(tmp_path):
    path = tmp_path / "present_other.json"
    code = main(
        [
            "differentials",
            "present",
            "--kind",
            "impossible",
            "--class",
            "other",
            "--json",
            str(path),
        ]
    )
    assert code == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["count"] == 113
    assert all(item["class"] == "other" for item in payload["differentials"])


def test_cli_ddt_csv(tmp_path):
    path = tmp_path / "present_ddt.csv"
    assert main(["ddt", "present", "--csv", str(path)]) == 0
    assert len(path.read_text(encoding="utf-8").splitlines()) == 17


def test_cli_rejects_class_for_possible(capsys):
    code = main(
        [
            "differentials",
            "present",
            "--kind",
            "possible",
            "--class",
            "other",
        ]
    )
    assert code == 2
    assert "--class" in capsys.readouterr().err


def test_cli_thesis_check_exit_codes(capsys):
    assert main(["thesis-check"]) == 0
    assert "[FAIL]" in capsys.readouterr().out
    assert main(["thesis-check", "--strict"]) == 1


def test_cli_presets(capsys):
    assert main(["presets"]) == 0
    output = capsys.readouterr().out
    for key in ("present", "prince", "prince-inverse", "klein"):
        assert key in output


def test_cli_bad_sbox(capsys):
    assert main(["info", "not-a-cipher"]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_ddt_print_smoke(capsys):
    assert main(["ddt", "present"]) == 0
    output = capsys.readouterr().out
    assert "in\\out" in output
    assert "16" in output


def test_api_summary_is_consistent():
    summary = get_preset("present").summary()
    assert (
        summary.zero_to_nonzero
        + summary.nonzero_to_zero
        + summary.low_weight
        + summary.other
        == summary.impossible
    )
