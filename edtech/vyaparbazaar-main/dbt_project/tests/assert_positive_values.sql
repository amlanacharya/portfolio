{% test assert_positive_values(model, column_name) %}

with validation as (
    select
        {{ column_name }} as value_field
    from {{ model }}
),

validation_errors as (
    select
        value_field
    from validation
    where value_field <= 0 or value_field is null
)

select *
from validation_errors

{% endtest %}
