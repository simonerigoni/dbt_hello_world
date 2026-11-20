"""Generate random sample data with the same schema as the CSV files in the data folder."""

import csv
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

# Must match the country_codes seed, so every customer has a country code and a region
COUNTRIES = ["Italy", "Netherlands", "Switzerland"]
# Must match the accepted_values test on raw_orders.status
STATUSES = ["completed", "cancelled"]
CANCELLED_SHARE = 0.15
FIRST_NAMES = [
    "Alice", "Bob", "Carla", "David", "Elena", "Federico", "Giulia", "Hugo",
    "Irene", "Jan", "Katia", "Luca", "Marta", "Noah", "Olga", "Paolo",
]  # fmt: skip
# The orders are in 2026, the year covered by the metricflow_time_spine model
FIRST_ORDER_DATE = date(2026, 1, 1)
DAYS = 365
MIN_AMOUNT, MAX_AMOUNT = 5.0, 300.0
FIRST_ORDER_ID = 101
CUSTOMER_COLUMNS = ["customer_id", "customer_name", "country", "_loaded_at"]
ORDER_COLUMNS = ["order_id", "customer_id", "order_date", "amount", "status", "_loaded_at"]
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class SampleData:
    customers: list[dict[str, str]]
    orders: list[dict[str, str]]


def now() -> datetime:
    """Current UTC time without time zone and microseconds, like the timestamps in the CSV."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def generate(
    customers: int = 10, orders: int = 50, seed: int = 42, loaded_at: datetime | None = None
) -> SampleData:
    """Generate the customers and the orders.

    The same seed always gives the same data. Only `_loaded_at` changes, it is the current time
    unless loaded_at is given, so dbt source freshness passes on freshly generated data.
    """
    if customers < 1 or orders < 0:
        raise ValueError("at least 1 customer and 0 orders are needed")
    rng = random.Random(seed)
    stamp = (loaded_at or now()).strftime(TIMESTAMP_FORMAT)
    customer_rows = [
        {
            "customer_id": str(customer_id),
            "customer_name": rng.choice(FIRST_NAMES),
            "country": rng.choice(COUNTRIES),
            "_loaded_at": stamp,
        }
        for customer_id in range(1, customers + 1)
    ]
    order_dates = sorted(
        FIRST_ORDER_DATE + timedelta(days=rng.randrange(DAYS)) for _ in range(orders)
    )
    order_rows = [
        {
            "order_id": str(FIRST_ORDER_ID + index),
            "customer_id": str(rng.randint(1, customers)),
            "order_date": order_date.isoformat(),
            "amount": f"{rng.uniform(MIN_AMOUNT, MAX_AMOUNT):.2f}",
            "status": "cancelled" if rng.random() < CANCELLED_SHARE else "completed",
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
    customers_path = output / "raw_customers.csv"
    orders_path = output / "raw_orders.csv"
    write_csv(customers_path, CUSTOMER_COLUMNS, data.customers)
    write_csv(orders_path, ORDER_COLUMNS, data.orders)
    return [customers_path, orders_path]
