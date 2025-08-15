{% macro clean_string(column_name) %}
    TRIM(LOWER({{ column_name }}))
{% endmacro %}

{% macro standardize_state_code(state_column) %}
    CASE
        WHEN UPPER({{ state_column }}) = 'MAHARASHTRA' THEN 'MH'
        WHEN UPPER({{ state_column }}) = 'KARNATAKA' THEN 'KA'
        WHEN UPPER({{ state_column }}) = 'TAMIL NADU' THEN 'TN'
        WHEN UPPER({{ state_column }}) = 'DELHI' THEN 'DL'
        WHEN UPPER({{ state_column }}) = 'UTTAR PRADESH' THEN 'UP'
        WHEN UPPER({{ state_column }}) = 'GUJARAT' THEN 'GJ'
        WHEN UPPER({{ state_column }}) = 'TELANGANA' THEN 'TG'
        WHEN UPPER({{ state_column }}) = 'WEST BENGAL' THEN 'WB'
        WHEN UPPER({{ state_column }}) = 'RAJASTHAN' THEN 'RJ'
        WHEN UPPER({{ state_column }}) = 'KERALA' THEN 'KL'
        WHEN UPPER({{ state_column }}) = 'PUNJAB' THEN 'PB'
        WHEN UPPER({{ state_column }}) = 'HARYANA' THEN 'HR'
        WHEN UPPER({{ state_column }}) = 'MADHYA PRADESH' THEN 'MP'
        WHEN UPPER({{ state_column }}) = 'BIHAR' THEN 'BR'
        WHEN UPPER({{ state_column }}) = 'ANDHRA PRADESH' THEN 'AP'
        WHEN UPPER({{ state_column }}) = 'ODISHA' THEN 'OD'
        WHEN UPPER({{ state_column }}) = 'ASSAM' THEN 'AS'
        WHEN UPPER({{ state_column }}) = 'JHARKHAND' THEN 'JH'
        WHEN UPPER({{ state_column }}) = 'UTTARAKHAND' THEN 'UK'
        WHEN UPPER({{ state_column }}) = 'HIMACHAL PRADESH' THEN 'HP'
        WHEN UPPER({{ state_column }}) = 'GOA' THEN 'GA'
        ELSE UPPER({{ state_column }})
    END
{% endmacro %}

{% macro extract_domain_from_email(email_column) %}
    SUBSTRING({{ email_column }} FROM POSITION('@' IN {{ email_column }}) + 1)
{% endmacro %}

{% macro categorize_email_domain(email_column) %}
    CASE
        WHEN {{ extract_domain_from_email(email_column) }} IN ('gmail.com', 'googlemail.com') THEN 'Gmail'
        WHEN {{ extract_domain_from_email(email_column) }} IN ('yahoo.com', 'yahoo.co.in') THEN 'Yahoo'
        WHEN {{ extract_domain_from_email(email_column) }} IN ('hotmail.com', 'outlook.com', 'live.com', 'msn.com') THEN 'Microsoft'
        WHEN {{ extract_domain_from_email(email_column) }} IN ('rediffmail.com') THEN 'Rediff'
        WHEN {{ extract_domain_from_email(email_column) }} LIKE '%.edu%' THEN 'Education'
        WHEN {{ extract_domain_from_email(email_column) }} LIKE '%.gov%' THEN 'Government'
        WHEN {{ extract_domain_from_email(email_column) }} LIKE '%.co.in' THEN 'Indian Business'
        WHEN {{ extract_domain_from_email(email_column) }} LIKE '%.org%' THEN 'Organization'
        ELSE 'Other'
    END
{% endmacro %}

{% macro format_phone_number(phone_column) %}
    CASE
        WHEN LENGTH({{ phone_column }}) = 10 THEN 
            '+91 ' || SUBSTRING({{ phone_column }} FROM 1 FOR 5) || ' ' || SUBSTRING({{ phone_column }} FROM 6)
        ELSE {{ phone_column }}
    END
{% endmacro %}

{% macro get_payment_method_category(payment_method_column) %}
    CASE
        WHEN LOWER({{ payment_method_column }}) IN ('credit_card', 'debit_card') THEN 'Card'
        WHEN LOWER({{ payment_method_column }}) IN ('upi', 'netbanking', 'wallet') THEN 'Digital'
        WHEN LOWER({{ payment_method_column }}) = 'cod' THEN 'Cash on Delivery'
        WHEN LOWER({{ payment_method_column }}) = 'emi' THEN 'EMI'
        ELSE 'Other'
    END
{% endmacro %}
