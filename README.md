# dbt Hello World

[![CI](https://github.com/simonerigoni/dbt_hello_world/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/simonerigoni/dbt_hello_world/actions/workflows/ci.yml?query=branch%3Amain) [![Docs](https://github.com/simonerigoni/dbt_hello_world/actions/workflows/docs.yml/badge.svg?branch=main)](https://simonerigoni.github.io/dbt_hello_world/) [![License](https://img.shields.io/github/license/simonerigoni/dbt_hello_world)](LICENSE.md) [![Python](https://img.shields.io/badge/python-3.15-blue)](pyproject.toml) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit) [![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://renovatebot.com)

## Introduction

A simple [dbt](https://www.getdbt.com/) Hello World that uses a local [DuckDB](https://duckdb.org/) database, so no server is needed. The raw data comes from two CSV files in the `data` folder at the root of the repository, declared as dbt sources and read directly by DuckDB. A small `country_codes` seed adds reference data. The data goes through three layers:

- **Bronze**: `bronze_customers` and `bronze_orders` are views over the raw sources, unchanged.
- **Silver**: `silver_orders` keeps only the completed orders, casts the types and adds the customer details. It is an incremental model, so after the first run it only processes the new orders instead of rebuilding the whole table.
- **Gold**: `gold_revenue_by_country` is a table with the number of orders, the revenue and the average order value per country, plus the country code and region from the seed.

The project also shows:

- **Tests**: `unique`, `not_null`, `relationships` (every order has an existing customer) and `accepted_values` (an order is either completed or cancelled).
- **Singular test**: `tests/assert_gold_revenue_matches_silver.sql` is a custom SQL test that fails if the total revenue in the gold layer is different from the sum of the silver order amounts.
- **Unit test**: `models/silver/unit_tests.yml` gives `silver_orders` a few made-up orders and customers, one of them cancelled, and checks that only the completed orders come out with the customer details.
- **Snapshot**: `customers_snapshot` in `snapshots/customers_snapshot.yml` keeps the history of the customers. When a customer changes, the old version is closed and a new one is added (slowly changing dimension type 2).
- **Incremental model**: `silver_orders` uses `order_id` as unique key and, with `is_incremental()`, only reads the orders from the latest loaded date onwards.
- **Package**: `packages.yml` installs [dbt_utils](https://hub.getdbt.com/dbt-labs/dbt_utils/latest/), and its `accepted_range` test checks that every order amount is greater than 0.
- **Contract**: `gold_revenue_by_country` has an enforced contract, so the build fails if a column name or data type changes.
- **Source freshness**: every raw CSV file has a `_loaded_at` column and `sources.yml` sets `loaded_at_field` and a `freshness` block, so `dbt source freshness` checks how old the data is. It only has a `warn_after` of 1 day and no `error_after`: the sample data was loaded in early 2026 and never changes, so the check always warns that it is stale but never fails. The bronze views keep `_loaded_at`, the silver model drops it.
- **Exposure**: `models/exposures.yml` declares `revenue_dashboard`, a made-up dashboard that uses the gold layer, so the lineage graph ends in a consumer of the data.
- **Semantic layer**: `models/semantic_models.yml` defines the `orders` semantic model on `silver_orders`, with the `total_revenue` and `number_of_orders` metrics. `metricflow_time_spine` is the small time spine, one row per day of 2026, that the semantic layer needs.
- **Descriptions**: every source, seed, model and column is described in the YAML files, so they show up in the dbt docs. The longer ones are `{% docs %}` blocks in `models/docs.md`, used in the YAML files with `doc('...')`.
- **Analysis**: `analyses/top_customers_by_revenue.sql` lists the top 3 customers by revenue. `dbt compile` writes its SQL to `target/compiled`, but it is never built in the database.
- **Macro**: `safe_divide` in `macros/safe_divide.sql` divides and rounds, returning null instead of failing when the denominator is 0. The gold model uses it for the average order value.

## Software and libraries

This project uses Python 3.15, [uv](https://docs.astral.sh/uv/), `dbt-core` and `dbt-duckdb`. For development it also uses `matplotlib` for the lineage graph and `sqlfluff` with `sqlfluff-templater-dbt` to lint the SQL.

## Data

Have a look at the `data` folder and its [DATA.md](data/DATA.md) file.

## Local configuration

To set up a local environment and install all dependencies, run `uv sync` from the project folder.

Then run the checks with:

```bash
uv run pre-commit run --all-files
uv run pytest
```

## Code Quality

Code quality is maintained through automated checks and linting using pre-commit.

Pre-commit is a framework for managing and maintaining multi-language pre-commit hooks. A pre-commit hook is a script that runs before a commit operation in a version control system. This allows to shift left code quality checks and remediations. You can change the hooks by updating the file `.pre-commit-config.yaml`.

To trigger the pre-commit hooks without an actual commit you can run `uv run pre-commit run --all-files -v`.

It is also possible to run manually the individual tools:

- `uv run ruff check --fix`
- `uv run ruff format .`
- `uv run pyright .`
- `uv run sqlfluff lint dbt_project`
- `uv run sqlfluff fix dbt_project`

The SQL files are linted with [SQLFluff](https://sqlfluff.com/) and its dbt templater, so the Jinja is rendered by dbt before the SQL is checked. The settings are in `.sqlfluff`: DuckDB dialect, the core rules, lowercase keywords and a line length of 100. The dbt templater compiles the project, so run `uv run dbt deps` in `dbt_project` first.

## Testing

Tests are implemented using `pytest` and coverage is tracked with `pytest-cov`. `tests/test_dbt_project.py` copies `dbt_project` and `data` to a temporary folder and runs `dbt deps` there, so nothing touches the local DuckDB file. Then it:

- runs `dbt build` twice, so all the data tests, unit tests and the singular test run, also on the incremental model and the snapshot
- runs `dbt source freshness`, which warns because the sample data is old, but does not fail
- runs `dbt compile` and `dbt docs generate --static`
- lints the SQL files with SQLFluff, so the CI checks them too
- checks that the lineage graph is up to date: it parses the project, describes the graph like `generate_lineage.py` does and compares it to the committed `images/dbt-dag.json`. The PNG bytes depend on the matplotlib version and the OS, so the test compares the description instead of the image. If it fails, run `uv run generate_lineage.py` and commit both files
- checks how `generate_lineage.py` places the nodes in columns and rows The detailed coverage report is generated by the pre-commit hook and it is available in [COVERAGE.md](COVERAGE.md) file.

It is also possible to run manually the individual tests:

- `uv run pytest`
- `uv run pytest tests/test_dbt_project.py::test_dbt_build`

## Running the code

All the dbt files are in the `dbt_project` folder. From the `dbt_project` folder, first run `uv run dbt deps` to install the `dbt_utils` package, then `uv run dbt build` to load the seed, build the models and the snapshot and run the tests. The data ends up in the local `dbt_hello_world.duckdb` file.

To see the gold layer, run `uv run dbt show --select gold_revenue_by_country`. To check the freshness of the raw data, run `uv run dbt source freshness`: it warns that the sample data is stale, which is expected.

The metrics are parsed and validated by dbt, but querying them needs [MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow) or dbt Cloud. MetricFlow is not a dependency of the project, but it can be run on the fly with uv, for example after a `dbt build`:

```bash
uv run --with dbt-metricflow mf query --metrics total_revenue,number_of_orders --group-by order__country
uv run --with dbt-metricflow mf query --metrics total_revenue --group-by metric_time__month
```

## Basic dbt commands

Run them from the `dbt_project` folder, prefixed with `uv run`.

| Command | What it does |
| --- | --- |
| `dbt parse` | Parses the project and writes `target/manifest.json`, a quick check of the YAML and Jinja |
| `dbt debug` | Checks the installation, `profiles.yml` and the database connection |
| `dbt deps` | Installs the packages listed in `packages.yml` |
| `dbt seed` | Loads the CSV files in `seeds` into the database |
| `dbt run` | Builds the models |
| `dbt run --full-refresh` | Rebuilds the incremental models from scratch |
| `dbt snapshot` | Runs the snapshots |
| `dbt test` | Runs the data tests and the unit tests |
| `dbt test --select test_type:unit` | Runs only the unit tests |
| `dbt test --select test_type:singular` | Runs only the singular tests in `tests` |
| `dbt source freshness` | Checks how old the raw data is, using `_loaded_at` |
| `dbt build` | Runs seeds, models, snapshots and tests in dependency order |
| `dbt run --select silver_orders+` | Builds `silver_orders` and everything downstream of it |
| `dbt show --select gold_revenue_by_country` | Previews the rows of a model |
| `dbt compile` | Writes the compiled SQL of the models, tests and analyses to `target` without running it |
| `dbt ls` | Lists the resources in the project |
| `dbt docs generate` | Generates the documentation and the lineage graph |
| `dbt docs generate --static` | Generates the documentation as a single `target/static_index.html` file |
| `dbt docs serve` | Serves the documentation in the browser |
| `dbt clean` | Deletes the `target` and `dbt_packages` folders |

## Lineage graph

This is the lineage graph of the project, with the same colors as in the dbt docs, from the sources to the exposure and the metrics. It is generated by `generate_lineage.py`, which parses the project and draws `images/dbt-dag.png` with matplotlib. It also writes `images/dbt-dag.json`, a text description of the nodes, edges and layout of the graph. After changing the project, run `uv run generate_lineage.py` from the root of the repository to update both files.

![dbt lineage graph](images/dbt-dag.png)

The dbt docs, with the interactive lineage graph, are published on GitHub Pages at [simonerigoni.github.io/dbt_hello_world](https://simonerigoni.github.io/dbt_hello_world/). The `Docs` workflow in `.github/workflows/docs.yml` builds the project, generates the static docs and deploys them on every push to `main`.

To browse the interactive docs locally, from the `dbt_project` folder run `uv run dbt docs generate` and then `uv run dbt docs serve`. To get a single HTML file that opens without a server, run `uv run dbt docs generate --static` and open `target/static_index.html`.

For comparison, this is the same lineage graph exported by hand from the static docs, as `images/dbt-dag-static.png`. Unlike `dbt-dag.png`, it is not regenerated by the script, so it has to be exported again after changing the project.

![dbt lineage graph exported from the static docs](images/dbt-dag-static.png)

## List of activities

In the [TODO.md](TODO.md) file you can find the list of tasks and on going activities.

## Licensing and acknowledgements

Have a look at [LICENSE.md](LICENSE.md).

## Outro

I hope this repository was interesting and thank you for taking the time to check it out. Let me know if you have any question and if you like the content that I create feel free to [buy me a coffee](https://www.buymeacoffee.com/simonerigoni).
