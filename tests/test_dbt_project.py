"""Build the dbt project end to end and check the lineage graph and the SQL style."""

import shutil
import subprocess
from pathlib import Path

import pytest
from dbt.cli.main import dbtRunner

import generate_lineage

IGNORED = shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb", ".user.yml")


@pytest.fixture(scope="module")
def project_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy dbt_project and data to a temporary folder and install the packages there.

    The build does not touch the repository and the local DuckDB file.
    """
    root = tmp_path_factory.mktemp("dbt")
    target = root / "dbt_project"
    shutil.copytree(generate_lineage.DBT_PROJECT, target, ignore=IGNORED)
    # The sources read the CSV files from ../data, relative to the dbt_project folder
    shutil.copytree(generate_lineage.ROOT / "data", root / "data")
    shutil.copy(generate_lineage.ROOT / ".sqlfluff", root / ".sqlfluff")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.chdir(target)
        run_dbt("deps")
    return target


@pytest.fixture
def in_project(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Like `uv run dbt ...` from the dbt_project folder: the CSV paths and the DuckDB file
    in the project are relative to the working directory."""
    monkeypatch.chdir(project_dir)
    return project_dir


def run_dbt(*args: str) -> None:
    result = dbtRunner().invoke(list(args))
    assert result.success, f"dbt {' '.join(args)} failed: {result.exception}"


def test_dbt_build(in_project: Path) -> None:
    """dbt build runs every seed, model, snapshot, data test and unit test."""
    run_dbt("build")
    # A second build runs the incremental model and the snapshot again on existing tables
    run_dbt("build")


def test_dbt_source_freshness(in_project: Path) -> None:
    """The freshness check runs. The sample data is old, so it only warns and does not fail."""
    run_dbt("source", "freshness")


def test_dbt_compile_and_docs(in_project: Path) -> None:
    """The analysis compiles and the static docs are generated."""
    run_dbt("compile")
    assert any((in_project / "target" / "compiled").rglob("top_customers_by_revenue.sql"))
    run_dbt("docs", "generate", "--static")
    assert (in_project / "target" / "static_index.html").exists()


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

    If this fails, run `uv run generate_lineage.py` and commit both files.
    """
    description = generate_lineage.describe(*generate_lineage.load_graph(project_dir))
    committed = generate_lineage.DESCRIPTION.read_text(encoding="utf-8")
    assert generate_lineage.to_json(description) == committed


def test_assign_columns() -> None:
    """Each node goes one column after its furthest parent, sources right before their child."""
    nodes = {name: {"name": name, "type": "model"} for name in ["src", "seed", "a", "b", "c"]}
    edges = [("src", "a"), ("a", "b"), ("b", "c"), ("seed", "c"), ("a", "c")]
    column = generate_lineage.assign_columns(nodes, edges)
    assert column == {"src": 0, "seed": 2, "a": 1, "b": 2, "c": 3}


def test_assign_rows() -> None:
    """Nodes sit close to their parents, so the child of the top parent goes on top."""
    nodes = {name: {"name": name, "type": "model"} for name in ["p1", "p2", "a", "z"]}
    edges = [("p1", "z"), ("p2", "a")]
    column = {"p1": 0, "p2": 0, "a": 1, "z": 1}
    assert generate_lineage.assign_rows(nodes, edges, column) == {"p1": 0, "p2": 1, "z": 0, "a": 1}
