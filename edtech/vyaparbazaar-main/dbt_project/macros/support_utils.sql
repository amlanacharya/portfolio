{% macro calculate_resolution_time(created_at, resolved_at, unit='hour') %}
    case
        when {{ resolved_at }} is null then null
        when {{ unit }} = 'minute' then datediff('minute', {{ created_at }}, {{ resolved_at }})
        when {{ unit }} = 'hour' then datediff('hour', {{ created_at }}, {{ resolved_at }})
        when {{ unit }} = 'day' then datediff('day', {{ created_at }}, {{ resolved_at }})
        else datediff('hour', {{ created_at }}, {{ resolved_at }})
    end
{% endmacro %}

{% macro categorize_resolution_time(resolution_time_hours) %}
    case
        when {{ resolution_time_hours }} is null then 'Unresolved'
        when {{ resolution_time_hours }} <= 1 then 'Under 1 hour'
        when {{ resolution_time_hours }} <= 4 then '1-4 hours'
        when {{ resolution_time_hours }} <= 24 then '4-24 hours'
        when {{ resolution_time_hours }} <= 72 then '1-3 days'
        else 'Over 3 days'
    end
{% endmacro %}

{% macro calculate_satisfaction_score(satisfaction_rating) %}
    case
        when {{ satisfaction_rating }} is null then null
        when {{ satisfaction_rating }} >= 4 then 'High'
        when {{ satisfaction_rating }} >= 3 then 'Medium'
        else 'Low'
    end
{% endmacro %}

{% macro categorize_support_priority(priority) %}
    case
        when lower({{ priority }}) = 'urgent' then 4
        when lower({{ priority }}) = 'high' then 3
        when lower({{ priority }}) = 'medium' then 2
        when lower({{ priority }}) = 'low' then 1
        else 0
    end
{% endmacro %}
