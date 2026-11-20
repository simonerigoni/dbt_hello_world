"""Allow `python -m dbt_hello_world`."""

from dbt_hello_world.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
