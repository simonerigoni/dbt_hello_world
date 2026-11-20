"""Gold layer, a dbt Python model: monthly cohort retention of customers.

Customers are grouped by the month of their first completed order. For every following
month, the model counts how many of them placed an order and the retention rate.

dbt-duckdb runs it in the same DuckDB database. It reads the silver orders, computes the
cohorts in Python and returns a DuckDB relation, with no pandas. The model is
self-contained, because dbt Python models cannot import the package.
"""

from datetime import date


def month_start(value: date) -> date:
    """First day of the month of a date."""
    return date(value.year, value.month, 1)


def add_months(value: date, months: int) -> date:
    """Shift a month-start date by a number of months."""
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def months_between(start: date, end: date) -> int:
    """Number of calendar months from start to end, both month-start dates."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def as_date(value: date) -> date:
    """Normalize a DuckDB date or timestamp to a date."""
    return value.date() if hasattr(value, "date") else value


def empty_result(session):
    """A relation with the result columns and no rows, for the empty input case."""
    return session.sql(
        """
        select
            cast(null as date) as cohort_month,
            cast(null as integer) as month_number,
            cast(null as integer) as cohort_size,
            cast(null as integer) as active_customers,
            cast(null as double) as retention_rate
        where false
        """
    )


def model(dbt, session):
    dbt.config(materialized="table")
    orders = dbt.ref("silver_orders").project("customer_id, order_date").fetchall()

    first_month: dict = {}
    active_months: dict = {}
    for customer_id, order_date in orders:
        month = month_start(as_date(order_date))
        first_month[customer_id] = min(first_month.get(customer_id, month), month)
        active_months.setdefault(customer_id, set()).add(month)

    if not first_month:
        return empty_result(session)

    last_month = max(month for months in active_months.values() for month in months)
    cohorts: dict = {}
    for customer_id, cohort in first_month.items():
        cohorts.setdefault(cohort, []).append(customer_id)

    rows = []
    for cohort in sorted(cohorts):
        members = cohorts[cohort]
        size = len(members)
        for month_number in range(months_between(cohort, last_month) + 1):
            month = add_months(cohort, month_number)
            active = sum(1 for customer_id in members if month in active_months[customer_id])
            rows.append((cohort, month_number, size, active, round(active / size, 4)))

    session.execute(
        """
        create or replace temp table gold_customer_cohorts_result (
            cohort_month date,
            month_number integer,
            cohort_size integer,
            active_customers integer,
            retention_rate double
        )
        """
    )
    session.executemany(
        "insert into gold_customer_cohorts_result values (?, ?, ?, ?, ?)",
        rows,
    )
    return session.table("gold_customer_cohorts_result").order("cohort_month, month_number")
