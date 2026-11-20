"""Generate random sample data with the same schema as the CSV files in the data folder."""

import csv
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dbt_hello_world import config


@dataclass(frozen=True)
class SampleData:
    customers: list[dict[str, str]]
    orders: list[dict[str, str]]


def now() -> datetime:
    """Current UTC time without time zone and microseconds, like the timestamps in the CSV."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def generate(
    customers: int = config.DEFAULT_CUSTOMERS,
    orders: int = config.DEFAULT_ORDERS,
    seed: int = config.DEFAULT_SEED,
    loaded_at: datetime | None = None,
) -> SampleData:
    """Generate the customers and the orders.

    The same seed always gives the same data. Only `_loaded_at` changes, it is the current time
    unless loaded_at is given, so dbt source freshness passes on freshly generated data.
    """
    if customers < 1 or orders < 0:
        raise ValueError("at least 1 customer and 0 orders are needed")
    rng = random.Random(seed)
    stamp = (loaded_at or now()).strftime(config.TIMESTAMP_FORMAT)
    customer_rows = [
        {
            "customer_id": str(customer_id),
            "customer_name": rng.choice(config.FIRST_NAMES),
            "country": rng.choice(config.COUNTRIES),
            "_loaded_at": stamp,
        }
        for customer_id in range(1, customers + 1)
    ]
    order_dates = sorted(
        config.FIRST_ORDER_DATE + timedelta(days=rng.randrange(config.DAYS)) for _ in range(orders)
    )
    order_rows = [
        {
            "order_id": str(config.FIRST_ORDER_ID + index),
            "customer_id": str(rng.randint(1, customers)),
            "order_date": order_date.isoformat(),
            "amount": f"{rng.uniform(config.MIN_AMOUNT, config.MAX_AMOUNT):.2f}",
            "status": (
                config.STATUS_CANCELLED
                if rng.random() < config.CANCELLED_SHARE
                else config.STATUS_COMPLETED
            ),
            "_loaded_at": stamp,
        }
        for index, order_date in enumerate(order_dates)
    ]
    return SampleData(customer_rows, order_rows)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write(data: SampleData, output: Path) -> list[Path]:
    """Write raw_customers.csv and raw_orders.csv into the output folder."""
    output.mkdir(parents=True, exist_ok=True)
    customers_path = output / config.RAW_CUSTOMERS_FILE
    orders_path = output / config.RAW_ORDERS_FILE
    write_csv(customers_path, config.CUSTOMER_COLUMNS, data.customers)
    write_csv(orders_path, config.ORDER_COLUMNS, data.orders)
    return [customers_path, orders_path]
