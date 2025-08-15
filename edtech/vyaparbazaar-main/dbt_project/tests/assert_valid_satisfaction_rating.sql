{% test assert_valid_satisfaction_rating(model, column_name) %}

with validation as (
    select
        {{ column_name }} as rating
    from {{ model }}
),

validation_errors as (
    select
        rating
    from validation
    where rating is not null and (rating < 1 or rating > 5)
)

select *
from validation_errors

{% endtest %}
