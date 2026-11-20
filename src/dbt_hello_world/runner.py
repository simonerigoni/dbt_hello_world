"""Run the dbt project with dbtRunner and read the gold layer from DuckDB."""

import contextlib
import os
from collections.abc import Iterator, Sequence
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

from dbt_hello_world import config


class DbtError(RuntimeError):
    """A dbt command failed."""


def database_for(data_dir: Path, project_dir: Path = config.DBT_PROJECT) -> Path:
    """The default sample data uses the DuckDB file in dbt_project, like a plain `dbt build`.

    Any other data folder gets its own DuckDB file inside it, so different data sets never mix
    in the incremental model and in the snapshot.
    """
    if data_dir.resolve() == config.DATA.resolve():
        return project_dir / config.DATABASE_FILE
    return data_dir / config.DATABASE_FILE


@contextlib.contextmanager
def dbt_environment(project_dir: Path, data_dir: Path, database: Path) -> Iterator[None]:
    """Run from the dbt project folder with the sources and the database set to absolute paths."""
    previous = {
        name: os.environ.get(name) for name in (config.DATA_VARIABLE, config.DATABASE_VARIABLE)
    }
    os.environ[config.DATA_VARIABLE] = str(data_dir.resolve())
    os.environ[config.DATABASE_VARIABLE] = str(database.resolve())
    try:
        with contextlib.chdir(project_dir):
            yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def invoke(args: Sequence[str]) -> None:
    """Run one dbt command, like `dbt <args>` on the command line."""
    result = dbtRunner().invoke(list(args))
    if not result.success:
        raise DbtError(f"dbt {' '.join(args)} failed: {result.exception or 'see the log above'}")


def run(
    data_dir: Path = config.DATA,
    project_dir: Path = config.DBT_PROJECT,
    database: Path | None = None,
    full_refresh: bool = False,
) -> Path:
    """Install the packages if needed, build the project and check the freshness of the data.

    Returns the DuckDB file with the result.
    """
    database = database or database_for(data_dir, project_dir)
    database.parent.mkdir(parents=True, exist_ok=True)
    with dbt_environment(project_dir, data_dir, database):
        if not (project_dir / "dbt_packages").exists():
            invoke(["deps"])
        invoke(["build", "--full-refresh"] if full_refresh else ["build"])
        # It only warns on old data, like the committed samples, and never fails
        invoke(["source", "freshness"])
    return database


def docs(
    data_dir: Path = config.DATA,
    project_dir: Path = config.DBT_PROJECT,
    database: Path | None = None,
) -> Path:
    """Generate the static docs, the same single HTML file the Pages workflow publishes.

    Returns the path of `target/static_index.html`.
    """
    database = database or database_for(data_dir, project_dir)
    database.parent.mkdir(parents=True, exist_ok=True)
    output = project_dir / config.TARGET_DIR / config.STATIC_DOCS_FILE
    with dbt_environment(project_dir, data_dir, database):
        if not (project_dir / "dbt_packages").exists():
            invoke(["deps"])
        invoke(["docs", "generate", "--static"])
    return output


def read_table(database: Path, table: str) -> tuple[list[str], list[tuple]]:
    """Return the column names and the rows of a table, reading DuckDB directly."""
    with duckdb.connect(str(database)) as connection:
        relation = connection.table(table)
        return relation.columns, relation.fetchall()


def format_table(columns: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Format rows as a plain text table."""
    cells = [
        list(columns),
        *[["" if value is None else str(value) for value in row] for row in rows],
    ]
    widths = [max(len(row[index]) for row in cells) for index in range(len(columns))]
    lines = [
        "  ".join(value.ljust(width) for value, width in zip(row, widths, strict=True))
        for row in cells
    ]
    lines.insert(1, "  ".join("-" * width for width in widths))
    return "\n".join(line.rstrip() for line in lines)
