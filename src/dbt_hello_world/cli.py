"""Command line interface: uv run dbt-hello-world <command>."""

import argparse
import webbrowser
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from dbt_hello_world import config, generator, lineage, runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dbt-hello-world",
        description="Generate sample data, run the dbt project, draw its lineage graph and open the docs.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="write random raw_customers and raw_orders")
    add_generate_arguments(generate)

    run = commands.add_parser("run", help="run dbt deps and build, then print the gold layer")
    add_run_arguments(run, default_data=config.DATA)

    commands.add_parser("lineage", help="draw images/dbt-dag.png and images/dbt-dag.json")

    docs = commands.add_parser("docs", help="generate the static docs and open them in the browser")
    add_docs_arguments(docs, default_data=config.DATA)

    all_ = commands.add_parser("all", help="generate new data, then run the project on it")
    add_generate_arguments(all_)
    return parser


def add_generate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--customers",
        type=positive,
        default=config.DEFAULT_CUSTOMERS,
        help=f"default: {config.DEFAULT_CUSTOMERS}",
    )
    parser.add_argument(
        "--orders",
        type=positive,
        default=config.DEFAULT_ORDERS,
        help=f"default: {config.DEFAULT_ORDERS}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=config.DEFAULT_SEED,
        help=f"random seed, default: {config.DEFAULT_SEED}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=config.GENERATED,
        help="folder of the CSV files, default: temp/data",
    )
    parser.add_argument(
        "--loaded-at",
        type=datetime.fromisoformat,
        help="value of _loaded_at, for example 2026-03-01T08:00:00, default: now in UTC",
    )


def add_run_arguments(parser: argparse.ArgumentParser, default_data: Path) -> None:
    parser.add_argument(
        "--data",
        type=Path,
        default=default_data,
        help="folder with the raw CSV files, default: data, the committed samples",
    )
    parser.add_argument(
        "--full-refresh", action="store_true", help="rebuild the incremental model from scratch"
    )


def add_docs_arguments(parser: argparse.ArgumentParser, default_data: Path) -> None:
    parser.add_argument(
        "--data",
        type=Path,
        default=default_data,
        help="folder with the raw CSV files, default: data, the committed samples",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="write the HTML file without opening it in the browser",
    )


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return number


def generate(args: argparse.Namespace) -> Path:
    data = generator.generate(args.customers, args.orders, args.seed, args.loaded_at)
    for path in generator.write(data, args.output):
        print(f"Written {path}")
    return args.output


def run(data_dir: Path, full_refresh: bool) -> None:
    database = runner.run(data_dir, full_refresh=full_refresh)
    for table in config.GOLD_TABLES:
        print(f"\n{table}\n")
        print(runner.format_table(*runner.read_table(database, table)))


def docs(data_dir: Path, open_browser: bool) -> None:
    path = runner.docs(data_dir)
    print(f"Static docs written to {path}")
    if open_browser:
        webbrowser.open(path.resolve().as_uri())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate":
            generate(args)
        elif args.command == "run":
            run(args.data, args.full_refresh)
        elif args.command == "lineage":
            lineage.main()
        elif args.command == "docs":
            docs(args.data, open_browser=not args.no_open)
        else:
            # New data replaces the old one, so rebuild the incremental model from scratch
            run(generate(args), full_refresh=True)
    except runner.DbtError as error:
        print(error)
        return 1
    return 0
