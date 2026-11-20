-- Time spine for the semantic layer: one row per day of 2026
select cast(range as date) as date_day
from range(date '2026-01-01', date '2027-01-01', interval 1 day)
