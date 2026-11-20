-- Silver: completed orders with proper types, enriched with the customer.
-- Incremental: after the first run, only orders newer than the latest one already loaded are processed
{{ config(materialized='incremental', unique_key='order_id') }}

select
    o.order_id,
    cast(o.order_date as date) as order_date,
    cast(o.amount as decimal(10, 2)) as amount,
    c.customer_id,
    c.customer_name,
    c.country
from {{ ref('bronze_orders') }} as o
inner join {{ ref('bronze_customers') }} as c
    on o.customer_id = c.customer_id
where o.status = 'completed'
{% if is_incremental() %}
    and cast(o.order_date as date) >= (select max(order_date) from {{ this }})
{% endif %}
