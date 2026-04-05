from __future__ import annotations

from cognito.models import RunReport


def test_exit_code_zero_without_errors():
    report = RunReport(command="encode", project_root="/tmp", dry_run=False)

    assert report.exit_code == 0


def test_exit_code_one_with_errors():
    report = RunReport(
        command="encode",
        project_root="/tmp",
        dry_run=False,
        errors=["something went wrong"],
    )

    assert report.exit_code == 1


def test_warnings_do_not_affect_exit_code():
    report = RunReport(
        command="encode",
        project_root="/tmp",
        dry_run=False,
        warnings=["heads up"],
    )

    assert report.exit_code == 0
