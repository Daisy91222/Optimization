-- Descriptive performance only: these associations are not causal lift estimates.
create or replace table mart_display_performance as
with perf as (
  select f.store_id, f.week, f.product_category as category,
         f.display_location, d.display_name, f.mailer_location,
         sum(f.sales_value) as actual_sales,
         sum(f.quantity) as units,
         sum(f.retail_discount) as retail_discount,
         sum(f.coupon_discount) as coupon_discount,
         count(distinct f.product_id) as product_count,
         count(*) as product_week_observations,
         count(distinct f.brand) as brand_count
  from fact_product_store_week f
  left join dim_display_location d using(display_location)
  where f.product_category is not null
  group by 1,2,3,4,5,6
), scored as (
  select *, actual_sales / nullif(product_count, 0) as sales_per_product,
         actual_sales / nullif(units, 0) as sales_per_unit
  from perf
)
select *,
       dense_rank() over (partition by store_id, week order by sales_per_product desc) as store_efficiency_rank,
       dense_rank() over (partition by week, category order by sales_per_product desc) as cross_store_category_rank,
       'descriptive_real_anonymized'::varchar as data_source
from scored;

-- Historical moving baseline excludes the current week; hierarchical fallback prevents leakage.
create or replace table mart_display_baseline as
with product_week as (
  select product_id, week, sum(sales_value) as product_week_sales
  from fact_product_store_week group by 1,2
), product_prior as (
  select product_id, week,
    avg(product_week_sales) over (
      partition by product_id order by week rows between 8 preceding and 1 preceding
    ) as product_prior_mean
  from product_week
), history as (
  select f.*,
    avg(sales_value) over (
      partition by store_id, product_id order by week
      rows between 8 preceding and 1 preceding
    ) as product_store_ma8,
    count(sales_value) over (
      partition by store_id, product_id order by week
      rows between 8 preceding and 1 preceding
    ) as product_store_history_n,
    avg(sales_value) over (
      partition by store_id, product_category order by week
      rows between 8 preceding and 1 preceding
    ) as category_store_ma8,
    pp.product_prior_mean
  from fact_product_store_week f left join product_prior pp using(product_id,week)
)
select *, coalesce(product_store_ma8, category_store_ma8, product_prior_mean, 0) as sql_expected_sales,
       sales_value - coalesce(product_store_ma8, category_store_ma8, product_prior_mean, 0)
         as sql_descriptive_residual,
       'moving_average_v1'::varchar as baseline_version,
       'model_estimate'::varchar as data_source
from history;

-- Feature wide table: all controls are timestamp-safe except static product taxonomy.
create or replace table mart_model_features as
select b.product_id, b.store_id, b.week, b.product_category as category,
       b.brand, b.display_location, b.mailer_location, b.sales_value,
       b.quantity, b.retail_discount, b.coupon_discount,
       coalesce(b.product_store_ma8, 0) as product_history_sales,
       coalesce(b.category_store_ma8, 0) as store_category_history_sales,
       coalesce(b.product_prior_mean, 0) as product_popularity,
       w.retail_quarter, w.holiday_period,
       b.product_store_history_n
from mart_display_baseline b join dim_week w using(week)
where b.product_category is not null;
