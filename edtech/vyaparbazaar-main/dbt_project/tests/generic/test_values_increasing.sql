{% test values_increasing(model, column_name, partition_by, order_by) %}

with windowed as (
    select
        {{ column_name }},
        lag({{ column_name }}) over (
            partition by {{ partition_by }}
            order by {{ order_by }}
        ) as prev_value
    from {{ model }}
)

select
    *
from windowed
where {{ column_name }} < prev_value
  and prev_value is not null

{% endtest %}
