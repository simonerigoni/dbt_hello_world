# dbt Hello World

## Data

This folder contains the data used by the project.

The CSV files are made-up sample data and they are declared as dbt sources in `dbt_project/models/sources.yml`, so DuckDB reads them directly:

* **raw_customers.csv**: one row per customer, with `customer_id`, `customer_name` and `country`
* **raw_orders.csv**: one row per order, with `order_id`, `customer_id`, `order_date`, `amount` in euros and `status` (`completed` or `cancelled`)

The reference data is in the `country_codes` seed, `dbt_project/seeds/country_codes.csv`, with `country`, `country_code` and `region` for every country.
