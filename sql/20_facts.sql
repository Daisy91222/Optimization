-- Receipt-line grain; product attributes are conformed once here.
create or replace table fact_transactions as
select t.*, p.department, p.brand, p.product_category, p.product_type
from raw_transactions t
left join dim_product p using (product_id);

-- Known upstream duplicates are retained in raw_promotions and resolved explicitly here.
-- Prefer a special display code and preserve the duplicate count for auditability.
create or replace table fact_product_display as
with ranked as (
    select *, count(*) over (partition by product_id, store_id, week) as raw_record_count,
           row_number() over (
             partition by product_id, store_id, week
             order by case when display_location = '0' then 1 else 0 end,
                      case when mailer_location = '0' then 1 else 0 end,
                      display_location, mailer_location
           ) as resolution_rank
    from raw_promotions
)
select product_id, store_id, week, display_location, mailer_location,
       raw_record_count, data_source
from ranked where resolution_rank = 1;

-- Product-store-week feature spine includes promoted products with zero observed sales.
create or replace table fact_product_store_week as
with tx as (
  select product_id, store_id, week,
         sum(sales_value) as sales_value, sum(quantity) as quantity,
         sum(abs(retail_disc)) as retail_discount,
         sum(abs(coupon_disc) + abs(coupon_match_disc)) as coupon_discount,
         count(distinct basket_id) as baskets
  from fact_transactions group by 1,2,3
), spine as (
  select product_id, store_id, week from tx
  union select product_id, store_id, week from fact_product_display
)
select s.product_id, s.store_id, s.week,
       coalesce(tx.sales_value, 0) as sales_value,
       coalesce(tx.quantity, 0) as quantity,
       coalesce(tx.retail_discount, 0) as retail_discount,
       coalesce(tx.coupon_discount, 0) as coupon_discount,
       coalesce(tx.baskets, 0) as baskets,
       coalesce(d.display_location, '0') as display_location,
       coalesce(d.mailer_location, '0') as mailer_location,
       p.department, p.brand, p.product_category, p.product_type,
       coalesce(d.data_source, 'real_anonymized') as data_source
from spine s
left join tx using(product_id, store_id, week)
left join fact_product_display d using(product_id, store_id, week)
left join dim_product p using(product_id);

create or replace table fact_store_week_category as
select store_id, week, product_category,
       sum(sales_value) as sales_value, sum(quantity) as quantity,
       sum(retail_discount) as retail_discount,
       sum(coupon_discount) as coupon_discount,
       sum(baskets) as product_basket_mentions,
       count(distinct product_id) as active_products,
       'real_anonymized'::varchar as data_source
from fact_product_store_week
where product_category is not null
group by 1,2,3;

