create or replace table dq_results as
with checks as (
 select 'raw_transactions_duplicate_record' check_name, 'critical' severity,
        count(*) - count(distinct source_record_id) failures,
        'source_record_id must be unique' rule_description from raw_transactions
 union all select 'raw_transactions_null_keys','critical', count(*),
        'store/product/week are required' from raw_transactions
        where store_id is null or product_id is null or week is null
 union all select 'raw_transactions_invalid_week','critical', count(*),
        'week must be between 1 and 53' from raw_transactions where week not between 1 and 53
 union all select 'raw_promotions_duplicate_grain','warning', count(*),
        'duplicate product-store-week is retained then deterministically resolved'
        from (select 1 from raw_promotions group by product_id,store_id,week having count(*)>1)
 union all select 'raw_promotions_invalid_display','critical', count(*),
        'display code must exist in documented code set' from raw_promotions
        where display_location not in ('0','1','2','3','4','5','6','7','9','A')
 union all select 'raw_promotions_invalid_mailer','critical', count(*),
        'mailer code must exist in documented code set' from raw_promotions
        where mailer_location not in ('0','A','C','D','F','H','J','L','P','X','Z')
 union all select 'transactions_missing_product','warning', count(*),
        'transaction product should join to product master' from raw_transactions t
        left join dim_product p using(product_id) where p.product_id is null
 union all select 'promotions_missing_product','warning', count(*),
        'promotion product should join to product master' from raw_promotions t
        left join dim_product p using(product_id) where p.product_id is null
 union all select 'negative_sales_outlier','warning', count(*),
        'negative sales retained as potential return/correction' from raw_transactions where sales_value < 0
)
select *, case when failures = 0 then 'PASS'
               when severity = 'warning' then 'WARN' else 'FAIL' end as status,
       current_timestamp as checked_at
from checks;
