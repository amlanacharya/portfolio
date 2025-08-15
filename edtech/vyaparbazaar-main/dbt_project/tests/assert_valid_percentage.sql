{% test assert_valid_percentage(model, column_name) %}

with validation as (
    select
        {{ column_name }} as percentage_field
    from {{ model }}
),

validation_errors as (
    select
        percentage_field
    from validation
    where percentage_field < 0 or percentage_field > 100 or percentage_field is null
)

select *
from validation_errors

{% endtest %}
