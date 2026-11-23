"""Unit tests of the shared constants module."""

import runpy

import pytest

from dbt_hello_world import config

# Printed by `python -m dbt_hello_world.config`, in definition order.
CONSTANTS = [
    "ROOT",
    "DBT_PROJECT",
    "DATA",
    "IMAGES",
    "GENERATED",
    "DATABASE_FILE",
    "RAW_CUSTOMERS_FILE",
    "RAW_ORDERS_FILE",
    "LINEAGE_PNG",
    "LINEAGE_JSON",
    "TARGET_DIR",
    "STATIC_DOCS_FILE",
    "DATA_VARIABLE",
    "DATABASE_VARIABLE",
    "DEFAULT_CUSTOMERS",
    "DEFAULT_ORDERS",
    "DEFAULT_SEED",
    "GOLD_TABLES",
    "COUNTRIES",
    "STATUS_COMPLETED",
    "STATUS_CANCELLED",
    "STATUSES",
    "CANCELLED_SHARE",
    "FIRST_NAMES",
    "FIRST_ORDER_DATE",
    "DAYS",
    "MIN_AMOUNT",
    "MAX_AMOUNT",
    "FIRST_ORDER_ID",
    "CUSTOMER_COLUMNS",
    "ORDER_COLUMNS",
    "TIMESTAMP_FORMAT",
    "COLORS",
    "MANIFEST_SECTIONS",
]


def test_python_dash_m_prints_constants(capsys: pytest.CaptureFixture[str]) -> None:
    """python -m dbt_hello_world.config prints each constant's name and value."""
    runpy.run_module("dbt_hello_world.config", run_name="__main__")
    lines = capsys.readouterr().out.splitlines()
    expected = [f"{name} = {getattr(config, name)!r}" for name in CONSTANTS]
    assert lines == expected
