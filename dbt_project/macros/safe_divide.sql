{% macro safe_divide(numerator, denominator, precision=2) %}
    -- Divide and round, returning null instead of failing when the denominator is 0
    round({{ numerator }} / nullif({{ denominator }}, 0), {{ precision }})
{% endmacro %}
