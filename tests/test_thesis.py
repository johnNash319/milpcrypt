from milpcrypt.thesis import PRINTED_DDTS, format_checks, run_checks


def test_checks_flag_present_ddt_only():
    checks = run_checks()
    ddt_checks = {
        check.subject: check
        for check in checks
        if check.group == "Printed DDT"
    }
    assert not ddt_checks["PRESENT"].ok
    assert "mismatched" in ddt_checks["PRESENT"].computed_value
    assert ddt_checks["PRINCE"].ok
    assert ddt_checks["PRINCE inverse"].ok
    assert ddt_checks["KLEIN"].ok


def test_present_residual_is_not_reproduced():
    checks = run_checks()
    residual = next(
        check
        for check in checks
        if check.subject == "PRESENT"
        and check.item == "paths left for cutting-off inequalities"
    )
    assert not residual.ok
    assert residual.thesis_value == "118"
    assert residual.computed_value == "113"
    assert "115" in residual.note


def test_other_residuals_match_thesis():
    checks = run_checks()
    for subject in ("PRINCE", "PRINCE inverse", "KLEIN"):
        residual = next(
            check
            for check in checks
            if check.subject == subject
            and check.item == "paths left for cutting-off inequalities"
        )
        assert residual.ok
        assert residual.computed_value == "120"


def test_printed_ddts_are_internally_consistent():
    for key, ddt in PRINTED_DDTS.items():
        assert len(ddt) == 16, key
        assert all(len(row) == 16 for row in ddt), key
        assert all(sum(row) == 16 for row in ddt), key
        assert all(
            sum(ddt[row][column] for row in range(16)) == 16
            for column in range(16)
        ), key


def test_format_checks_reports_failures():
    text = format_checks(run_checks())
    assert "[FAIL]" in text
    assert "Summary:" in text
    assert "PRESENT" in text
