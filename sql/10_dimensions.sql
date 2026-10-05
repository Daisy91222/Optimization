create or replace table dim_store as
select distinct store_id, 'real_anonymized'::varchar as data_source
from (
    select store_id from raw_transactions
    union select store_id from raw_promotions
) s where store_id is not null;

create or replace table dim_product as
select product_id, manufacturer_id, department, brand, product_category,
       product_type, package_size, data_source
from raw_products
qualify row_number() over (partition by product_id order by product_id) = 1;

create or replace table dim_display_location as
select * from (values
 ('0','No extra display','Regular placement / counterfactual reference',false),
 ('1','Store Front','Special display',true),
 ('2','Store Rear','Special display',true),
 ('3','Front End Cap','Special display',true),
 ('4','Mid-Aisle End Cap','Special display',true),
 ('5','Rear End Cap','Special display',true),
 ('6','Side-Aisle End Cap','Special display',true),
 ('7','In-Aisle','Special display',true),
 ('9','Secondary Location Display','Special display',true),
 ('A','In-Shelf','In-shelf coded promotion',true)
) t(display_location, display_name, display_group, is_special_display);

create or replace table dim_week as
select week,
       ((week - 1) % 13) + 1 as week_in_quarter,
       floor((week - 1) / 13) + 1 as retail_quarter,
       case when week in (47,48,49,50,51,52,53) then true else false end as holiday_period,
       'derived_from_real_week'::varchar as data_source
from generate_series(1, 53) t(week);

