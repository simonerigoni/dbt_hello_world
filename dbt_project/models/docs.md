{% docs raw_source %}
Raw CSV files in the `data` folder at the root of the repository, read directly by DuckDB
through `external_location`, so there is no load step.

Every file has a `_loaded_at` column with the time the row was loaded, used by
`dbt source freshness`. The sample data was loaded in early 2026, so the freshness check warns
that it is stale.
{% enddocs %}

{% docs bronze_layer %}
Bronze layer, the raw rows exactly as they are in the CSV file, `_loaded_at` included.
It is a view, so it always shows the current content of the file.
{% enddocs %}

{% docs silver_orders %}
Silver layer, one row per **completed** order:

- the cancelled orders are filtered out
- `order_date` and `amount` are cast to proper types
- the customer name and country are joined from `bronze_customers`
- `_loaded_at` is dropped, it only matters for the raw data

It is an incremental model with `order_id` as unique key: after the first run it only processes
the orders from the latest loaded date onwards.
{% enddocs %}

{% docs gold_revenue_by_country %}
Gold layer, one row per country with the number of orders, the revenue and the average order
value, plus the country code and region from the `country_codes` seed.

It has an enforced contract, so the build fails if a column name or data type changes, and it is
used by the `revenue_dashboard` exposure.
{% enddocs %}

{% docs metricflow_time_spine %}
One row per day, the time spine that the dbt semantic layer (MetricFlow) needs to aggregate the
metrics over time. It covers 2026, the year of the sample data.
{% enddocs %}

{% docs gold_customer_segments %}
Gold layer, one row per customer with completed orders: number of orders, total revenue and a
segment, `high` from 200 euros, `medium` from 100 and `low` below.

It is a **dbt Python model**, `models/gold/gold_customer_segments.py`. With dbt-duckdb it runs
inside DuckDB, and `dbt.ref` returns a DuckDB relation, so it uses the relation methods
`aggregate` and `project` instead of pandas.
{% enddocs %}

{% docs gold_customer_cohorts %}
Gold layer, one row per cohort month and number of months since the first completed
order: the size of the cohort, how many of those customers still ordered in that month,
and the retention rate.

Customers are grouped by the month of their first completed order. Month 0 is that first
month, so the retention rate is 1. Later months include the ones with no orders, with a
retention rate of 0.

It is a **dbt Python model**, `models/gold/gold_customer_cohorts.py`. It reads the silver
orders, computes the cohorts in Python and returns a DuckDB relation, without pandas.
{% enddocs %}
