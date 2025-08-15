{% set status_values = ['open', 'in_progress', 'resolved', 'closed', 'cancelled'] %}

with support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

ticket_summary as (
    select
        category,
        count(*) as total_tickets,
        {% for status in status_values %}
        sum(case when status = '{{ status }}' then 1 else 0 end) as {{ status }}_tickets,
        {% endfor %}
        avg(case when resolved_at is not null 
            then datediff('hour', created_at, resolved_at) 
            else null end) as avg_resolution_time_hours
    from support_tickets
    group by 1
)

select * from ticket_summary
