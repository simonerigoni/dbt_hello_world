"""Integration tests: build the dbt project end to end on a temporary copy.

They also check the SQL style, the lineage graph and the runner on generated data.
"""

import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from dbt_hello_world import config, generator, lineage, runner

IGNORED = shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb", ".user.yml")


@pytest.fixture(scope="module")
def project_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy dbt_project and data to a temporary folder and install the packages there.

    The build does not touch the repository and the local DuckDB file.
    """
    root = tmp_path_factory.mktemp("dbt")
    target = root / "dbt_project"
    shutil.copytree(config.DBT_PROJECT, target, ignore=IGNORED)
    # The sources read the CSV files from ../data, relative to the dbt_project folder
    shutil.copytree(config.DATA, root / "data")
    shutil.copy(config.ROOT / ".sqlfluff", root / ".sqlfluff")
    with runner.dbt_environment(target, root / "data", target / config.DATABASE_FILE):
        runner.invoke(["deps"])
    return target


@pytest.fixture
def in_project(project_dir: Path):
    """Like `uv run dbt ...` from the dbt_project folder, on the committed sample data."""
    with runner.dbt_environment(project_dir, project_dir.parent / "data", project_dir / "x.duckdb"):
        yield project_dir


def test_dbt_build(in_project: Path) -> None:
    """dbt build runs every seed, model, snapshot, data test and unit test."""
    runner.invoke(["build"])
    # A second build runs the incremental model and the snapshot again on existing tables
    runner.invoke(["build"])


def test_gold_customer_cohorts_on_sample_data(in_project: Path) -> None:
    """The sample orders produce a known retention table, including months with no orders."""
    runner.invoke(["build"])
    columns, rows = runner.read_table(in_project / "x.duckdb", "gold_customer_cohorts")
    assert columns == [
        "cohort_month",
        "month_number",
        "cohort_size",
        "active_customers",
        "retention_rate",
    ]
    assert rows == [
        (date(2026, 1, 1), 0, 2, 2, 1.0),
        (date(2026, 1, 1), 1, 2, 0, 0.0),
        (date(2026, 1, 1), 2, 2, 1, 0.5),
        (date(2026, 2, 1), 0, 1, 1, 1.0),
        (date(2026, 2, 1), 1, 1, 0, 0.0),
        (date(2026, 3, 1), 0, 1, 1, 1.0),
    ]


def test_dbt_source_freshness(in_project: Path) -> None:
    """The freshness check runs. The sample data is old, so it only warns and does not fail."""
    runner.invoke(["source", "freshness"])


def test_dbt_compile_and_docs(in_project: Path) -> None:
    """The analysis compiles and the static docs are generated."""
    runner.invoke(["compile"])
    assert any((in_project / "target" / "compiled").rglob("top_customers_by_revenue.sql"))
    runner.invoke(["docs", "generate", "--static"])
    assert (in_project / "target" / "static_index.html").exists()


def test_failing_dbt_command_raises(in_project: Path) -> None:
    with pytest.raises(runner.DbtError):
        runner.invoke(["run-operation", "does_not_exist"])


def test_run_on_generated_data(project_dir: Path, tmp_path: Path) -> None:
    """The runner builds the project on freshly generated data, which is not stale."""
    data_dir = tmp_path / "data"
    generator.write(generator.generate(40, 60, seed=config.DEFAULT_SEED), data_dir)
    database = runner.run(data_dir, project_dir, full_refresh=True)
    assert database == data_dir / config.DATABASE_FILE
    # A second run is incremental and the packages are already installed
    assert runner.run(data_dir, project_dir) == database
    columns, rows = runner.read_table(database, "gold_customer_segments")
    assert columns[-1] == "segment"
    assert {row[-1] for row in rows} == {"high", "medium", "low"}
    columns, rows = runner.read_table(database, "gold_revenue_by_country")
    assert {row[0] for row in rows} == set(config.COUNTRIES)
    table = runner.format_table(columns, rows)
    assert table.splitlines()[0].startswith("country")
    assert len(table.splitlines()) == len(rows) + 2
    columns, rows = runner.read_table(database, "gold_customer_cohorts")
    assert columns == [
        "cohort_month",
        "month_number",
        "cohort_size",
        "active_customers",
        "retention_rate",
    ]
    assert rows
    # Month 0 is the first month of each cohort, so every customer is active
    first_months = [row for row in rows if row[1] == 0]
    assert first_months
    assert all(row[3] == row[2] and row[4] == 1.0 for row in first_months)
    assert all(0.0 <= row[4] <= 1.0 for row in rows)


def test_default_data_uses_the_project_database(tmp_path: Path) -> None:
    assert runner.database_for(config.DATA, tmp_path) == tmp_path / config.DATABASE_FILE
    assert runner.database_for(tmp_path) == tmp_path / config.DATABASE_FILE


def test_sqlfluff(project_dir: Path) -> None:
    """The SQL files follow the style set in .sqlfluff."""
    result = subprocess.run(
        ["sqlfluff", "lint", "dbt_project/models", "dbt_project/tests", "dbt_project/analyses"],
        cwd=project_dir.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_lineage_graph_is_up_to_date(project_dir: Path) -> None:
    """images/dbt-dag.json matches the project, so images/dbt-dag.png is not stale.

    If this fails, run `uv run dbt-hello-world lineage` and commit both files.
    """
    description = lineage.describe(*lineage.load_graph(project_dir))
    committed = config.LINEAGE_JSON.read_text(encoding="utf-8")
    assert lineage.to_json(description) == committed


def test_lineage_main(project_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "dag.png"
    lineage.main(project_dir, output)
    assert output.exists()
    assert output.with_suffix(".json").read_text(encoding="utf-8") == config.LINEAGE_JSON.read_text(
        encoding="utf-8"
    )
