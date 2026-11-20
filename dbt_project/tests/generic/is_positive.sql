-- Generic test: every value of the column must be greater than 0, or at least 0 with
-- allow_zero: true. Like every data test, it fails when the query returns rows.
-- Null values are ignored, use not_null to check them.
{% test is_positive(model, column_name, allow_zero=false) %}

    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} {{ '<' if allow_zero else '<=' }} 0

{% endtest %}
