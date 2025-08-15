{% test feature_variance(model, column_name, min_variance=0.01) %}

/*
    This test checks if a feature has sufficient variance to be useful.
    Features with near-zero variance provide little predictive power.
    
    Parameters:
        model: The model to test
        column_name: The feature column to test
        min_variance: The minimum variance threshold (default: 0.01)
    
    Returns:
        Rows where the variance is below the threshold
*/

with feature_stats as (
    select
        var_pop({{ column_name }}) as feature_variance
    from {{ model }}
    where {{ column_name }} is not null
)

select *
from feature_stats
where feature_variance < {{ min_variance }}

{% endtest %}
