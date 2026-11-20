"""Unit tests of the sample data generator."""

import csv
from datetime import datetime
from pathlib import Path

import pytest

from dbt_hello_world import config, generator

LOADED_AT = datetime(2026, 3, 1, 8, 0, 0)


def test_same_seed_gives_same_data() -> None:
    first = generator.generate(5, 20, seed=7, loaded_at=LOADED_AT)
    second = generator.generate(5, 20, seed=7, loaded_at=LOADED_AT)
    assert first == second


def test_different_seed_gives_different_data() -> None:
    first = generator.generate(5, 20, seed=1, loaded_at=LOADED_AT)
    second = generator.generate(5, 20, seed=2, loaded_at=LOADED_AT)
    assert first != second


def test_only_loaded_at_depends_on_the_time() -> None:
    first = generator.generate(3, 10, seed=7, loaded_at=LOADED_AT)
    second = generator.generate(3, 10, seed=7)

    def without_stamp(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        return [{k: v for k, v in row.items() if k != "_loaded_at"} for row in rows]

    assert without_stamp(first.orders) == without_stamp(second.orders)
    assert without_stamp(first.customers) == without_stamp(second.customers)
    stamp = datetime.strptime(second.orders[0]["_loaded_at"], config.TIMESTAMP_FORMAT)
    assert abs((generator.now() - stamp).total_seconds()) < 60


def test_values_pass_the_dbt_tests() -> None:
    """Countries, statuses, amounts, dates and keys are valid for the dbt sources and models."""
    data = generator.generate(10, 200, seed=42, loaded_at=LOADED_AT)
    customer_ids = [row["customer_id"] for row in data.customers]
    order_ids = [row["order_id"] for row in data.orders]
    assert len(set(customer_ids)) == 10
    assert len(set(order_ids)) == 200
    assert {row["country"] for row in data.customers} <= set(config.COUNTRIES)
    assert {row["status"] for row in data.orders} == set(config.STATUSES)
    assert all(row["customer_id"] in customer_ids for row in data.orders)
    assert all(float(row["amount"]) > 0 for row in data.orders)
    assert all(row["order_date"].startswith("2026-") for row in data.orders)
    assert all(row["_loaded_at"] == "2026-03-01 08:00:00" for row in data.orders)


def test_countries_match_the_seed() -> None:
    path = config.DBT_PROJECT / "seeds" / "country_codes.csv"
    with path.open(encoding="utf-8") as file:
        countries = {row["country"] for row in csv.DictReader(file)}
    assert set(config.COUNTRIES) == countries


def test_invalid_sizes() -> None:
    with pytest.raises(ValueError):
        generator.generate(0, 10)


def test_write_uses_the_schema_of_the_samples(tmp_path: Path) -> None:
    """The generated files have the same header as the committed samples."""
    paths = generator.write(generator.generate(3, 5, loaded_at=LOADED_AT), tmp_path / "out")
    for path in paths:
        sample = (config.DATA / path.name).read_text(encoding="utf-8").splitlines()[0]
        generated = path.read_text(encoding="utf-8").splitlines()
        assert generated[0] == sample
    assert len((tmp_path / "out" / config.RAW_ORDERS_FILE).read_text().splitlines()) == 6
