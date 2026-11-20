-- Bronze: raw customers as read from the source
select * from {{ source('raw', 'raw_customers') }}
