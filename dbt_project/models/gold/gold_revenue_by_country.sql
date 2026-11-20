-- Gold: orders, revenue and average order value per country
select
    o.country,
    c.country_code,
    c.region,
    count(*) as number_of_orders,
    sum(o.amount) as revenue,
    {{ safe_divide('sum(o.amount)', 'count(*)') }} as average_order_value
from {{ ref('silver_orders') }} as o
left join {{ ref('country_codes') }} as c
    on o.country = c.country
group by o.country, c.country_code, c.region
order by revenue desc
