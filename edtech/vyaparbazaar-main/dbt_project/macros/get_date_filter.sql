{% macro get_date_filter(date_column, period) %}
    {% if period == 'last_30_days' %}
        {{ date_column }} >= dateadd('day', -30, current_date())
    {% elif period == 'last_90_days' %}
        {{ date_column }} >= dateadd('day', -90, current_date())
    {% elif period == 'last_year' %}
        {{ date_column }} >= dateadd('year', -1, current_date())
    {% elif period == 'ytd' %}
        {{ date_column }} >= date_trunc('year', current_date())
    {% elif period == 'last_month' %}
        {{ date_column }} >= date_trunc('month', dateadd('month', -1, current_date())) and
        {{ date_column }} < date_trunc('month', current_date())
    {% else %}
        1=1
    {% endif %}
{% endmacro %}
