-- Raw layer: values are preserved from the official anonymous package sample.
create or replace table raw_transactions as
select
    cast(source_record_id as varchar) as source_record_id,
    cast(household_id as varchar) as household_id,
    cast(store_id as varchar) as store_id,
    cast(basket_id as varchar) as basket_id,
    cast(product_id as varchar) as product_id,
    cast(quantity as double) as quantity,
    cast(sales_value as double) as sales_value,
    cast(retail_disc as double) as retail_disc,
    cast(coupon_disc as double) as coupon_disc,
    cast(coupon_match_disc as double) as coupon_match_disc,
    cast(week as integer) as week,
    cast(transaction_timestamp as timestamp) as transaction_timestamp,
    cast(data_source as varchar) as data_source
from read_parquet('data/demo/transactions.parquet');

create or replace table raw_promotions as
select
    cast(product_id as varchar) as product_id,
    cast(store_id as varchar) as store_id,
    cast(display_location as varchar) as display_location,
    cast(mailer_location as varchar) as mailer_location,
    cast(week as integer) as week,
    cast(data_source as varchar) as data_source
from read_parquet('data/demo/promotions.parquet');

create or replace table raw_products as
select
    cast(product_id as varchar) as product_id,
    cast(manufacturer_id as varchar) as manufacturer_id,
    cast(department as varchar) as department,
    cast(brand as varchar) as brand,
    cast(product_category as varchar) as product_category,
    cast(product_type as varchar) as product_type,
    cast(package_size as varchar) as package_size,
    cast(data_source as varchar) as data_source
from read_parquet('data/demo/products.parquet');

