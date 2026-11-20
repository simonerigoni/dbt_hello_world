-- Bronze: raw orders as read from the source
select * from {{ source('raw', 'raw_orders') }}
