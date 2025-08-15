{{ config(materialized='table') }}

{% set start_date = "cast('2016-01-01' as date)" %}
{% set end_date = "cast('2023-12-31' as date)" %}

with date_spine as (
    {{ dbt_utils.date_spine(
        start_date=start_date,
        end_date=end_date,
        datepart="day"
    ) }}
),

dates as (
    select
        -- Date key in YYYYMMDD format
        cast(strftime(date_day, '%Y%m%d') as int) as date_key,
        date_day as calendar_date,

        -- Standard date parts
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(quarter from date_day) as quarter,
        extract(dayofweek from date_day) as day_of_week,
        extract(dayofyear from date_day) as day_of_year,

        -- Weekend indicator
        case
            when extract(dayofweek from date_day) in (0, 6) then true
            else false
        end as is_weekend,

        -- Holiday indicator (simplified for this exercise)
        case
            when (extract(month from date_day) = 1 and extract(day from date_day) = 26) then true  -- Republic Day
            when (extract(month from date_day) = 8 and extract(day from date_day) = 15) then true  -- Independence Day
            when (extract(month from date_day) = 10 and extract(day from date_day) = 2) then true  -- Gandhi Jayanti
            when (extract(month from date_day) = 1 and extract(day from date_day) = 1) then true   -- New Year's Day
            when (extract(month from date_day) = 10 and extract(day from date_day) = 24) then true -- Diwali (approximate)
            else false
        end as is_holiday,

        -- Festival season indicator
        case
            when extract(month from date_day) between 9 and 11 then true
            else false
        end as is_festival_season,

        -- Fiscal year (April-March)
        case
            when extract(month from date_day) >= 4 then extract(year from date_day)
            else extract(year from date_day) - 1
        end as fiscal_year,

        -- Fiscal quarter
        case
            when extract(month from date_day) between 4 and 6 then 1
            when extract(month from date_day) between 7 and 9 then 2
            when extract(month from date_day) between 10 and 12 then 3
            else 4
        end as fiscal_quarter,

        -- Season
        case
            when extract(month from date_day) between 3 and 5 then 'Spring'
            when extract(month from date_day) between 6 and 8 then 'Summer'
            when extract(month from date_day) = 9 then 'Monsoon'
            when extract(month from date_day) between 10 and 11 then 'Autumn'
            else 'Winter'
        end as season,

        -- Month name
        case
            when extract(month from date_day) = 1 then 'January'
            when extract(month from date_day) = 2 then 'February'
            when extract(month from date_day) = 3 then 'March'
            when extract(month from date_day) = 4 then 'April'
            when extract(month from date_day) = 5 then 'May'
            when extract(month from date_day) = 6 then 'June'
            when extract(month from date_day) = 7 then 'July'
            when extract(month from date_day) = 8 then 'August'
            when extract(month from date_day) = 9 then 'September'
            when extract(month from date_day) = 10 then 'October'
            when extract(month from date_day) = 11 then 'November'
            when extract(month from date_day) = 12 then 'December'
        end as month_name,

        -- Day name
        case
            when extract(dayofweek from date_day) = 0 then 'Sunday'
            when extract(dayofweek from date_day) = 1 then 'Monday'
            when extract(dayofweek from date_day) = 2 then 'Tuesday'
            when extract(dayofweek from date_day) = 3 then 'Wednesday'
            when extract(dayofweek from date_day) = 4 then 'Thursday'
            when extract(dayofweek from date_day) = 5 then 'Friday'
            when extract(dayofweek from date_day) = 6 then 'Saturday'
        end as day_name
    from date_spine
)

select * from dates
