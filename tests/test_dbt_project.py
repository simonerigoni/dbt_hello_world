"""Build the dbt project end to end and check the lineage graph helpers."""

import shutil
from pathlib import Path

import pytest
from dbt.cli.main import dbtRunner

import generate_lineage

IGNORED = shutil.ignore_patterns("target", "logs", "dbt_packages", "*.duckdb", ".user.yml")


@pytest.fixture(scope="module")
def project_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy dbt_project to a temporary folder so the build does not touch the repository."""
    target = tmp_path_factory.mktemp("dbt") / "dbt_project"
    shutil.copytree(generate_lineage.DBT_PROJECT, target, ignore=IGNORED)
    return target


def run_dbt(*args: str) -> None:
    result = dbtRunner().invoke(list(args))
    assert result.success, f"dbt {' '.join(args)} failed: {result.exception}"


def test_dbt_build(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """dbt deps and dbt build run every seed, model, snapshot, data test and unit test."""
    # Like `uv run dbt build` from the dbt_project folder: the CSV paths and the DuckDB file
    # in the project are relative to the working directory
    monkeypatch.chdir(project_dir)
    run_dbt("deps")
    run_dbt("build")
    # A second build runs the incremental model and the snapshot again on existing tables
    run_dbt("build")


def test_assign_columns() -> None:
    """Each node goes one column after its furthest parent, sources right before their child."""
    nodes = {name: {"name": name, "type": "model"} for name in ["src", "seed", "a", "b", "c"]}
    edges = [("src", "a"), ("a", "b"), ("b", "c"), ("seed", "c"), ("a", "c")]
    column = generate_lineage.assign_columns(nodes, edges)
    assert column == {"src": 0, "seed": 2, "a": 1, "b": 2, "c": 3}
