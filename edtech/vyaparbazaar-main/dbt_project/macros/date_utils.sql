{% macro date_diff_in_days(start_date, end_date) %}
    datediff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

{% macro is_recent_date(date_column, days=30) %}
    {{ date_diff_in_days(date_column, current_date()) }} <= {{ days }}
{% endmacro %}

{% macro is_within_date_range(date_column, start_days_ago, end_days_ago) %}
    {{ date_diff_in_days(date_column, current_date()) }} BETWEEN {{ end_days_ago }} AND {{ start_days_ago }}
{% endmacro %}

{% macro get_fiscal_year(date_column) %}
    CASE
        WHEN MONTH({{ date_column }}) >= 4 THEN YEAR({{ date_column }})
        ELSE YEAR({{ date_column }}) - 1
    END
{% endmacro %}

{% macro get_fiscal_quarter(date_column) %}
    CASE
        WHEN MONTH({{ date_column }}) BETWEEN 4 AND 6 THEN 'Q1'
        WHEN MONTH({{ date_column }}) BETWEEN 7 AND 9 THEN 'Q2'
        WHEN MONTH({{ date_column }}) BETWEEN 10 AND 12 THEN 'Q3'
        ELSE 'Q4'
    END
{% endmacro %}

{% macro get_season(date_column) %}
    CASE
        WHEN MONTH({{ date_column }}) BETWEEN 3 AND 5 THEN 'Spring'
        WHEN MONTH({{ date_column }}) BETWEEN 6 AND 8 THEN 'Summer'
        WHEN MONTH({{ date_column }}) BETWEEN 9 AND 11 THEN 'Fall'
        ELSE 'Winter'
    END
{% endmacro %}

{% macro is_weekend(date_column) %}
    EXTRACT(DOW FROM {{ date_column }}) IN (0, 6)
{% endmacro %}

{% macro is_festival_season(date_column) %}
    -- Simplified festival season check for India (Diwali, Dussehra, etc.)
    -- Typically October-November
    MONTH({{ date_column }}) IN (10, 11)
{% endmacro %}
