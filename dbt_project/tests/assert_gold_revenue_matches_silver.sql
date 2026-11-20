-- The total revenue in the gold layer must equal the sum of the silver order amounts.
-- A singular test fails when it returns rows.
with gold as (
    select sum(revenue) as revenue
    from {{ ref('gold_revenue_by_country') }}
),

silver as (
    select sum(amount) as revenue
    from {{ ref('silver_orders') }}
)

select
    gold.revenue as gold_revenue,
    silver.revenue as silver_revenue
from gold
cross join silver
where gold.revenue != silver.revenue
