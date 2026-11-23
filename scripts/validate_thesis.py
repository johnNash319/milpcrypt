"""Run the thesis consistency checks from the command line.

Exit status is 1 when a check fails.  This is expected at the moment because
the PRESENT DDT printed in the thesis does not match its S-box; inspect the
notes instead of treating the exit code as a test-suite failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running the script from a fresh checkout without installing the
# package.  An editable install is still recommended.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from milpcrypt.thesis import format_checks, run_checks  # noqa: E402


def main() -> int:
    checks = run_checks()
    print(format_checks(checks))
    return 1 if any(not check.ok for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
