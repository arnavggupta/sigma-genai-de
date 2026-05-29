
  create or replace   view SIGMA_DE.PUBLIC.stg_transactions
  
  
  
  
  as (
    -- models/staging/stg_fact_transactions.sql

WITH raw_transactions AS (
    SELECT
        transaction_id,
        amount,
        status,
        merchant_id,
        customer_id,
        transaction_date,
        payment_method
    FROM
        source('sigma_analytics', 'fact_transactions')
    WHERE
        merchant_id NOT LIKE 'TEST_%'
),

cleaned_transactions AS (
    SELECT
        LOWER(transaction_id) AS transaction_id,
        CAST(amount AS DECIMAL(10,2)) AS amount,
        LOWER(status) AS status,
        LOWER(merchant_id) AS merchant_id,
        LOWER(customer_id) AS customer_id,
        CAST(transaction_date AS DATE) AS transaction_date,
        LOWER(payment_method) AS payment_method,
        CURRENT_TIMESTAMP AS loaded_at
    FROM
        raw_transactions
)

SELECT
    *
FROM
    cleaned_transactions;
  );

