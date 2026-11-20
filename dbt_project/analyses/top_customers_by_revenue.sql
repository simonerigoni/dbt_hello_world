-- Top 3 customers by revenue. An analysis is compiled by dbt compile but never built,
-- run the compiled SQL in target/compiled to see the result
select
    customer_id,
    customer_name,
    country,
    count(*) as number_of_orders,
    sum(amount) as revenue
from {{ ref('silver_orders') }}
group by customer_id, customer_name, country
order by revenue desc
limit 3
