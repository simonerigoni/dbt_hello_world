"""Shared constants of the dbt_hello_world package."""

from datetime import date
from pathlib import Path

# Paths. The package lives in src/dbt_hello_world, the repository root is two levels up.
ROOT = Path(__file__).resolve().parents[2]
DBT_PROJECT = ROOT / "dbt_project"
DATA = ROOT / "data"
IMAGES = ROOT / "images"
# Generated data goes to the ignored temp folder, so the committed samples in data are kept.
GENERATED = ROOT / "temp" / "data"

# File names
DATABASE_FILE = "dbt_hello_world.duckdb"
RAW_CUSTOMERS_FILE = "raw_customers.csv"
RAW_ORDERS_FILE = "raw_orders.csv"
LINEAGE_PNG = IMAGES / "dbt-dag.png"
LINEAGE_JSON = IMAGES / "dbt-dag.json"
# The single HTML file produced by `dbt docs generate --static`, also published by Pages.
TARGET_DIR = "target"
STATIC_DOCS_FILE = "static_index.html"

# Read by sources.yml and profiles.yml, with the defaults of a plain `dbt build`.
DATA_VARIABLE = "DBT_HELLO_WORLD_DATA"
DATABASE_VARIABLE = "DBT_HELLO_WORLD_DATABASE"

# Default sizes and seed of `generate` and of the CLI.
DEFAULT_CUSTOMERS = 10
DEFAULT_ORDERS = 50
DEFAULT_SEED = 42

# Gold tables printed by the CLI after a run.
GOLD_TABLES = ["gold_revenue_by_country", "gold_customer_segments", "gold_customer_cohorts"]

# Must match the country_codes seed, so every customer has a country code and a region.
COUNTRIES = ["Italy", "Netherlands", "Switzerland"]
# Must match the accepted_values test on raw_orders.status.
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUSES = [STATUS_COMPLETED, STATUS_CANCELLED]
CANCELLED_SHARE = 0.15
FIRST_NAMES = [
    "Alice", "Bob", "Carla", "David", "Elena", "Federico", "Giulia", "Hugo",
    "Irene", "Jan", "Katia", "Luca", "Marta", "Noah", "Olga", "Paolo",
]  # fmt: skip
# The orders are in 2026, the year covered by the metricflow_time_spine model.
FIRST_ORDER_DATE = date(2026, 1, 1)
DAYS = 365
MIN_AMOUNT = 5.0
MAX_AMOUNT = 300.0
FIRST_ORDER_ID = 101
CUSTOMER_COLUMNS = ["customer_id", "customer_name", "country", "_loaded_at"]
ORDER_COLUMNS = ["order_id", "customer_id", "order_date", "amount", "status", "_loaded_at"]
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Same colors as the dbt docs lineage graph.
COLORS = {
    "source": "#5fb825",
    "seed": "#8eb0d6",
    "model": "#0094b3",
    "snapshot": "#88447d",
    "semantic_model": "#ffa8c2",
    "metric": "#ff5688",
    "exposure": "#ff694b",
}
# Manifest sections that hold the nodes of the graph.
MANIFEST_SECTIONS = ["nodes", "sources", "semantic_models", "metrics", "exposures"]
