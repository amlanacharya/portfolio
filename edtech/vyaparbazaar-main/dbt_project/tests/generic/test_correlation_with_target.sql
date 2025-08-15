{% test correlation_with_target(model, column_name, target_column, min_correlation=0.05, absolute=true) %}

/*
    This test checks if a feature has a minimum correlation with a target variable.
    
    Parameters:
        model: The model to test
        column_name: The feature column to test
        target_column: The target variable column
        min_correlation: The minimum correlation threshold (default: 0.05)
        absolute: Whether to use absolute correlation value (default: true)
    
    Returns:
        Rows where the correlation is below the threshold
*/

with feature_data as (
    select
        {{ column_name }} as feature_value,
        {{ target_column }} as target_value
    from {{ model }}
    where {{ column_name }} is not null
),

correlation_calc as (
    select
        (avg(feature_value * target_value) - (avg(feature_value) * avg(target_value))) / 
        (stddev(feature_value) * stddev(target_value)) as correlation
    from feature_data
)

select *
from correlation_calc
where 
{% if absolute %}
    abs(correlation) < {{ min_correlation }}
{% else %}
    correlation < {{ min_correlation }}
{% endif %}

{% endtest %}
