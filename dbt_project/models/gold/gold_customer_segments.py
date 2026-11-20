"""Gold layer, a dbt Python model: total revenue and segment of each customer.

dbt-duckdb runs it in the same DuckDB database and dbt.ref returns a DuckDB relation, so it
needs no pandas.
"""

HIGH_REVENUE = 200
MEDIUM_REVENUE = 100


def model(dbt, session):
    dbt.config(materialized="table")
    orders = dbt.ref("silver_orders")
    customers = orders.aggregate(
        "customer_id, customer_name, country, count(*) as number_of_orders, sum(amount) as revenue",
        "customer_id, customer_name, country",
    )
    return customers.project(
        "customer_id, customer_name, country, number_of_orders, revenue, "
        f"case when revenue >= {HIGH_REVENUE} then 'high' "
        f"when revenue >= {MEDIUM_REVENUE} then 'medium' else 'low' end as segment"
    ).order("revenue desc")
