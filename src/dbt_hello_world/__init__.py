"""dbt Hello World: generate sample data, run the dbt project and draw its lineage graph."""

from pathlib import Path

# The package lives in src/dbt_hello_world, the repository root is two levels up
ROOT = Path(__file__).resolve().parents[2]
DBT_PROJECT = ROOT / "dbt_project"
DATA = ROOT / "data"
IMAGES = ROOT / "images"

__all__ = ["DATA", "DBT_PROJECT", "IMAGES", "ROOT"]
