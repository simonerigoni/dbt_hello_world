"""Unit tests of the command line interface."""

import runpy
import sys
from pathlib import Path

import pytest

from dbt_hello_world import DATA, cli, lineage, runner


def test_generate_arguments() -> None:
    args = cli.build_parser().parse_args(
        ["generate", "--customers", "3", "--orders", "7", "--seed", "1", "--output", "x"]
    )
    assert (args.customers, args.orders, args.seed, args.output) == (3, 7, 1, Path("x"))
    assert args.loaded_at is None


def test_defaults() -> None:
    args = cli.build_parser().parse_args(["generate", "--loaded-at", "2026-03-01T08:00:00"])
    assert (args.customers, args.orders, args.seed, args.output) == (10, 50, 42, cli.GENERATED)
    assert args.loaded_at.isoformat() == "2026-03-01T08:00:00"
    args = cli.build_parser().parse_args(["run"])
    assert (args.data, args.full_refresh) == (DATA, False)


@pytest.mark.parametrize("argv", [[], ["unknown"], ["generate", "--orders", "0"]])
def test_invalid_arguments(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(argv)


def test_generated_data_does_not_overwrite_the_samples() -> None:
    assert cli.GENERATED.resolve() != DATA.resolve()
    assert cli.GENERATED.parts[-2:] == ("temp", "data")


def test_generate_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        cli.main(["generate", "--customers", "2", "--orders", "3", "--output", str(tmp_path)]) == 0
    )
    assert (tmp_path / "raw_customers.csv").exists()
    assert (tmp_path / "raw_orders.csv").exists()
    assert "raw_orders.csv" in capsys.readouterr().out


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[tuple[Path, bool]]:
    """Replace dbt and DuckDB with fakes and record the calls."""
    calls: list[tuple[Path, bool]] = []

    def run(data_dir: Path, full_refresh: bool = False) -> Path:
        calls.append((data_dir, full_refresh))
        return tmp_path / "db.duckdb"

    monkeypatch.setattr(runner, "run", run)
    monkeypatch.setattr(runner, "read_table", lambda database, table: (["name"], [(table,)]))
    return calls


def test_run_command(fake_run: list, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["run", "--data", "some/folder", "--full-refresh"]) == 0
    assert fake_run == [(Path("some/folder"), True)]
    out = capsys.readouterr().out
    assert all(table in out for table in cli.GOLD_TABLES)


def test_all_command(fake_run: list, tmp_path: Path) -> None:
    """all generates the data and runs the project on it, rebuilding from scratch."""
    assert cli.main(["all", "--orders", "5", "--output", str(tmp_path / "data")]) == 0
    assert fake_run == [(tmp_path / "data", True)]
    assert (tmp_path / "data" / "raw_orders.csv").exists()


def test_lineage_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(lineage, "main", lambda: calls.append("lineage"))
    assert cli.main(["lineage"]) == 0
    assert calls == ["lineage"]


def test_dbt_error_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(data_dir: Path, full_refresh: bool = False) -> Path:
        raise runner.DbtError("dbt build failed")

    monkeypatch.setattr(runner, "run", fail)
    assert cli.main(["run"]) == 1


def test_python_dash_m(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """python -m dbt_hello_world runs the same CLI."""
    monkeypatch.setattr(sys, "argv", ["dbt_hello_world", "generate", "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("dbt_hello_world", run_name="__main__")
    assert exit_info.value.code == 0
