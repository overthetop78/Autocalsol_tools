from __future__ import annotations

from autocalsol_tools.duplicates import DuplicateOptions, analyze_duplicates, export_duplicates


def test_internal_and_external_duplicates_with_options(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("email;code\n Test@Example.com ;0\ntest@example.com;A\n", encoding="utf-8")
    second.write_text("email;code\nTEST@example.com;B\n", encoding="utf-8")

    result = analyze_duplicates(
        [first, second],
        DuplicateOptions(selected_columns=("email",), trim_values=True, lowercase_values=True),
    )

    assert result.summary.group_count == 1
    assert result.summary.external_count == 1
    assert result.summary.internal_count == 0
    assert result.summary.occurrence_count == 3
    assert all(item.duplicate_type == "EXTERNE" for item in result.occurrences)

    output = export_duplicates(result, tmp_path / "report.csv")
    assert output.exists()
    assert "Ligne complète" in output.read_text(encoding="utf-8-sig").splitlines()[0]
