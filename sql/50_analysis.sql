-- Same-category cross-store comparison with both rank and percentile.
create or replace view analysis_cross_store_category as
select store_id, week, category, display_location, actual_sales, sales_per_product,
       cross_store_category_rank,
       percent_rank() over (partition by week, category order by sales_per_product) as efficiency_percentile
from mart_display_performance;

-- Promotion before/after comparison is descriptive and not a causal estimator.
create or replace view analysis_promotion_pre_post as
with weekly as (
 select product_id, store_id, week, sales_value, display_location,
        lag(sales_value) over(partition by product_id,store_id order by week) as prior_week_sales,
        lead(sales_value) over(partition by product_id,store_id order by week) as next_week_sales
 from fact_product_store_week
)
select *, sales_value - prior_week_sales as change_from_prior,
          next_week_sales - sales_value as change_to_next,
          'descriptive_not_causal'::varchar as interpretation
from weekly where display_location <> '0';

-- Mailer, retail discount and display stacking view.
create or replace view analysis_promotion_stack as
select display_location <> '0' as has_display,
       mailer_location <> '0' as has_mailer,
       retail_discount > 0 as has_retail_discount,
       count(*) as observations, avg(sales_value) as avg_sales,
       avg(quantity) as avg_units
from fact_product_store_week group by 1,2,3;

-- Concentration is measured on observed sales share, not inferred physical space.
create or replace view analysis_brand_concentration as
with brand_sales as (
 select store_id, week, display_location, brand, sum(sales_value) sales
 from fact_product_store_week where display_location <> '0'
 group by 1,2,3,4
), shares as (
 select *, sales/nullif(sum(sales) over(partition by store_id,week,display_location),0) brand_share
 from brand_sales
)
select store_id,week,display_location,sum(brand_share*brand_share) as brand_hhi,max(brand_share) as max_brand_share
from shares group by 1,2,3;

-- Category dependence on special display is a descriptive sales-share signal.
create or replace view analysis_category_display_dependency as
select category,
       sum(case when display_location <> '0' then actual_sales else 0 end)
         / nullif(sum(actual_sales), 0) as special_display_sales_share,
       sum(case when display_location <> '0' then units else 0 end)
         / nullif(sum(units), 0) as special_display_unit_share,
       count(distinct case when display_location <> '0' then display_location end)
         as special_display_types_used,
       'descriptive_not_causal'::varchar as interpretation
from mart_display_performance group by 1;

-- Flag below-median categories within display types whose observed average value is high.
create or replace view analysis_high_value_low_efficiency as
with location_value as (
  select display_location, avg(sales_per_product) as location_avg_efficiency,
         ntile(3) over(order by avg(sales_per_product)) as location_value_tertile
  from mart_display_performance where display_location <> '0' group by 1
), category_perf as (
  select store_id, week, category, display_location, sales_per_product,
         median(sales_per_product) over(partition by display_location) as location_median_efficiency
  from mart_display_performance where display_location <> '0'
)
select c.*, l.location_avg_efficiency,
       'observed_low_efficiency_on_high_value_type'::varchar as reason_code
from category_perf c join location_value l using(display_location)
where l.location_value_tertile = 3 and c.sales_per_product < c.location_median_efficiency;
