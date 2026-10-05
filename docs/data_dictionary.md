# 数据字典 / Data Dictionary

字段类型由构建后的 DuckDB 自动提取；来源口径见 `docs/data_sources_and_definitions.md`。

## `raw_transactions`

- **主键**：source_record_id
- **粒度**：receipt line
- **来源**：real_anonymized
- **质量规则**：unique record id; required keys; week range

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_record_id` | `VARCHAR` | Stable demo source-row identifier. |
| `household_id` | `VARCHAR` | Anonymous household identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `basket_id` | `VARCHAR` | Anonymous shopping occasion identifier. |
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `quantity` | `DOUBLE` | Purchased unit count. |
| `sales_value` | `DOUBLE` | Retailer sales amount in source currency. |
| `retail_disc` | `DOUBLE` | Retail loyalty discount. |
| `coupon_disc` | `DOUBLE` | Manufacturer coupon discount. |
| `coupon_match_disc` | `DOUBLE` | Retailer coupon-match discount. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `transaction_timestamp` | `TIMESTAMP` | Source purchase timestamp. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `raw_promotions`

- **主键**：none (source may duplicate product/store/week)
- **粒度**：source promotion row
- **来源**：real_anonymized
- **质量规则**：valid display/mailer codes; duplicate grain audited

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `display_location` | `VARCHAR` | Official display location code. |
| `mailer_location` | `VARCHAR` | Official mailer position code. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `raw_products`

- **主键**：product_id
- **粒度**：product
- **来源**：real_anonymized
- **质量规则**：product id required; duplicate id checked in dimension

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `manufacturer_id` | `VARCHAR` | Anonymous manufacturer identifier. |
| `department` | `VARCHAR` | Product department. |
| `brand` | `VARCHAR` | Private or national brand label in source. |
| `product_category` | `VARCHAR` | Product category. |
| `product_type` | `VARCHAR` | Lowest-level source product type. |
| `package_size` | `VARCHAR` | Source package-size text. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `dim_store`

- **主键**：store_id
- **粒度**：store
- **来源**：real_anonymized
- **质量规则**：unique, non-null store id

| 字段 | 类型 | 说明 |
|---|---|---|
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `dim_product`

- **主键**：product_id
- **粒度**：product
- **来源**：real_anonymized
- **质量规则**：unique product id; taxonomy null rate monitored

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `manufacturer_id` | `VARCHAR` | Anonymous manufacturer identifier. |
| `department` | `VARCHAR` | Product department. |
| `brand` | `VARCHAR` | Private or national brand label in source. |
| `product_category` | `VARCHAR` | Product category. |
| `product_type` | `VARCHAR` | Lowest-level source product type. |
| `package_size` | `VARCHAR` | Source package-size text. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `dim_display_location`

- **主键**：display_location
- **粒度**：display code
- **来源**：official code mapping
- **质量规则**：code uniqueness and allowed set

| 字段 | 类型 | 说明 |
|---|---|---|
| `display_location` | `VARCHAR` | Official display location code. |
| `display_name` | `VARCHAR` | Human-readable display name. |
| `display_group` | `VARCHAR` | Display grouping. |
| `is_special_display` | `BOOLEAN` | Whether code denotes an extra/special display. |

## `dim_week`

- **主键**：week
- **粒度**：retail week
- **来源**：derived
- **质量规则**：week 1-53

| 字段 | 类型 | 说明 |
|---|---|---|
| `week` | `BIGINT` | Source retail week, 1-53. |
| `week_in_quarter` | `BIGINT` | Derived week within quarter. |
| `retail_quarter` | `DOUBLE` | Derived 13-week quarter. |
| `holiday_period` | `BOOLEAN` | Derived late-year holiday flag. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `fact_transactions`

- **主键**：source_record_id
- **粒度**：receipt line enriched with product
- **来源**：real_anonymized
- **质量规则**：product referential integrity

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_record_id` | `VARCHAR` | Stable demo source-row identifier. |
| `household_id` | `VARCHAR` | Anonymous household identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `basket_id` | `VARCHAR` | Anonymous shopping occasion identifier. |
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `quantity` | `DOUBLE` | Purchased unit count. |
| `sales_value` | `DOUBLE` | Retailer sales amount in source currency. |
| `retail_disc` | `DOUBLE` | Retail loyalty discount. |
| `coupon_disc` | `DOUBLE` | Manufacturer coupon discount. |
| `coupon_match_disc` | `DOUBLE` | Retailer coupon-match discount. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `transaction_timestamp` | `TIMESTAMP` | Source purchase timestamp. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |
| `department` | `VARCHAR` | Product department. |
| `brand` | `VARCHAR` | Private or national brand label in source. |
| `product_category` | `VARCHAR` | Product category. |
| `product_type` | `VARCHAR` | Lowest-level source product type. |

## `fact_product_display`

- **主键**：product_id, store_id, week
- **粒度**：product-store-week
- **来源**：real_anonymized + deterministic duplicate resolution
- **质量规则**：one row per grain; raw_record_count retained

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `display_location` | `VARCHAR` | Official display location code. |
| `mailer_location` | `VARCHAR` | Official mailer position code. |
| `raw_record_count` | `BIGINT` | Number of source promotion rows at resolved grain. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `fact_store_week_category`

- **主键**：store_id, week, product_category
- **粒度**：store-week-category
- **来源**：aggregated real_anonymized
- **质量规则**：additive measures; category required

| 字段 | 类型 | 说明 |
|---|---|---|
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `product_category` | `VARCHAR` | Product category. |
| `sales_value` | `DOUBLE` | Retailer sales amount in source currency. |
| `quantity` | `DOUBLE` | Purchased unit count. |
| `retail_discount` | `DOUBLE` | Retail discount. |
| `coupon_discount` | `DOUBLE` | Coupon discount. |
| `product_basket_mentions` | `HUGEINT` | Product basket mentions. |
| `active_products` | `BIGINT` | Active products. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `mart_display_performance`

- **主键**：store_id, week, category, display_location, mailer_location
- **粒度**：store-week-category-display-mailer
- **来源**：descriptive aggregation
- **质量规则**：ranks partition correctly; no causal label

| 字段 | 类型 | 说明 |
|---|---|---|
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `category` | `VARCHAR` | Candidate product category. |
| `display_location` | `VARCHAR` | Official display location code. |
| `display_name` | `VARCHAR` | Human-readable display name. |
| `mailer_location` | `VARCHAR` | Official mailer position code. |
| `actual_sales` | `DOUBLE` | Observed aggregated sales; descriptive. |
| `units` | `DOUBLE` | Observed aggregated quantity. |
| `retail_discount` | `DOUBLE` | Retail discount. |
| `coupon_discount` | `DOUBLE` | Coupon discount. |
| `product_count` | `BIGINT` | Distinct products in group. |
| `product_week_observations` | `BIGINT` | Product-week row count. |
| `brand_count` | `BIGINT` | Distinct observed brand labels. |
| `sales_per_product` | `DOUBLE` | Observed sales divided by distinct products. |
| `sales_per_unit` | `DOUBLE` | Observed sales divided by units. |
| `store_efficiency_rank` | `BIGINT` | Within-store/week descriptive efficiency rank. |
| `cross_store_category_rank` | `BIGINT` | Same-category cross-store rank. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `mart_display_baseline`

- **主键**：product_id, store_id, week
- **粒度**：product-store-week
- **来源**：model estimate
- **质量规则**：history windows exclude current row

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `VARCHAR` | Anonymous product identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `INTEGER` | Source retail week, 1-53. |
| `sales_value` | `DOUBLE` | Retailer sales amount in source currency. |
| `quantity` | `DOUBLE` | Purchased unit count. |
| `retail_discount` | `DOUBLE` | Retail discount. |
| `coupon_discount` | `DOUBLE` | Coupon discount. |
| `baskets` | `BIGINT` | Baskets. |
| `display_location` | `VARCHAR` | Official display location code. |
| `mailer_location` | `VARCHAR` | Official mailer position code. |
| `department` | `VARCHAR` | Product department. |
| `brand` | `VARCHAR` | Private or national brand label in source. |
| `product_category` | `VARCHAR` | Product category. |
| `product_type` | `VARCHAR` | Lowest-level source product type. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |
| `product_store_ma8` | `DOUBLE` | Product store ma8. |
| `product_store_history_n` | `BIGINT` | Product store history n. |
| `category_store_ma8` | `DOUBLE` | Category store ma8. |
| `product_prior_mean` | `DOUBLE` | Product prior mean. |
| `sql_expected_sales` | `DOUBLE` | Leakage-controlled historical moving baseline. |
| `sql_descriptive_residual` | `DOUBLE` | Actual minus SQL moving baseline. |
| `baseline_version` | `VARCHAR` | Baseline calculation version. |
| `data_source_1` | `VARCHAR` | Data source 1. |

## `mart_incremental_effect`

- **主键**：effect_id
- **粒度**：observed product-store-week effect estimate
- **来源**：model_estimate
- **质量规则**：confidence 0-1; model version required

| 字段 | 类型 | 说明 |
|---|---|---|
| `effect_id` | `VARCHAR` | Unique effect estimate identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `VARCHAR` | Source retail week, 1-53. |
| `category` | `VARCHAR` | Candidate product category. |
| `display_location` | `VARCHAR` | Official display location code. |
| `actual_sales` | `DOUBLE` | Observed aggregated sales; descriptive. |
| `expected_sales_without_special_display` | `DOUBLE` | Model counterfactual prediction with display set to code 0. |
| `predicted_sales_with_observed_display` | `DOUBLE` | Model prediction with observed display feature. |
| `predicted_incremental_sales` | `DOUBLE` | Model-predicted difference, never actual realized lift. |
| `confidence` | `DOUBLE` | Support-based model confidence score from 0 to 1. |
| `model_version` | `VARCHAR` | Model lineage version. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `mart_allocation_candidates`

- **主键**：candidate_id
- **粒度**：store-target week-position-category
- **来源**：model estimate + simulated configuration
- **质量规则**：compatibility explicit; source/version required

| 字段 | 类型 | 说明 |
|---|---|---|
| `candidate_id` | `VARCHAR` | Unique allocation candidate identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `target_week` | `BIGINT` | Simulated planning week. |
| `resource_position` | `VARCHAR` | Simulated position identifier; not a physical floor-plan coordinate. |
| `resource_type` | `VARCHAR` | Display resource type/code. |
| `category` | `VARCHAR` | Candidate product category. |
| `current_category` | `VARCHAR` | Simulated current allocation. |
| `predicted_incremental_sales` | `DOUBLE` | Model-predicted difference, never actual realized lift. |
| `confidence` | `DOUBLE` | Support-based model confidence score from 0 to 1. |
| `change_cost` | `DOUBLE` | Simulated adjustment cost. |
| `dominant_brand` | `VARCHAR` | Modal source brand label for category. |
| `min_facings_per_store` | `BIGINT` | Simulated minimum allocation policy. |
| `max_facings_per_store` | `BIGINT` | Simulated maximum allocation / category-concentration policy. |
| `strategic_weight` | `DOUBLE` | Simulated headquarters strategic objective weight. |
| `is_headquarters_strategic` | `BOOLEAN` | Simulated headquarters retention flag. |
| `is_change` | `BOOLEAN` | Whether candidate differs from current simulation. |
| `support_n` | `BIGINT` | Number of effect rows supporting category-location estimate. |
| `is_compatible` | `BOOLEAN` | Simulated category-resource fit rule. |
| `model_version` | `VARCHAR` | Model lineage version. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `mart_allocation_recommendations`

- **主键**：recommendation_id
- **粒度**：store-target week-resource position
- **来源**：scenario simulation
- **质量规则**：one assignment per position; solver status required

| 字段 | 类型 | 说明 |
|---|---|---|
| `recommendation_id` | `VARCHAR` | Unique recommendation identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `target_week` | `BIGINT` | Simulated planning week. |
| `resource_position` | `VARCHAR` | Simulated position identifier; not a physical floor-plan coordinate. |
| `resource_type` | `VARCHAR` | Display resource type/code. |
| `recommended_category` | `VARCHAR` | Solver-selected category. |
| `current_category` | `VARCHAR` | Simulated current allocation. |
| `predicted_incremental_sales` | `DOUBLE` | Model-predicted difference, never actual realized lift. |
| `confidence` | `DOUBLE` | Support-based model confidence score from 0 to 1. |
| `change_cost` | `DOUBLE` | Simulated adjustment cost. |
| `reason_code` | `VARCHAR` | Auditable recommendation reason. |
| `solver_status` | `VARCHAR` | CP-SAT or fallback status. |
| `model_version` | `VARCHAR` | Model lineage version. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

## `mart_space_audit`

- **主键**：audit_id
- **粒度**：audit event
- **来源**：simulated
- **质量规则**：recommendation traceability; duplicate position check

| 字段 | 类型 | 说明 |
|---|---|---|
| `audit_id` | `VARCHAR` | Unique simulated audit identifier. |
| `store_id` | `VARCHAR` | Anonymous store identifier. |
| `week` | `BIGINT` | Source retail week, 1-53. |
| `resource_position` | `VARCHAR` | Simulated position identifier; not a physical floor-plan coordinate. |
| `planned_category` | `VARCHAR` | Recommended/planned category. |
| `observed_category` | `VARCHAR` | Simulated field observation. |
| `planned_date` | `DATE` | Simulated planned execution date. |
| `audit_date` | `DATE` | Simulated audit date. |
| `photo_status` | `VARCHAR` | Simulated photo evidence status. |
| `match_status` | `VARCHAR` | Plan/observation match result. |
| `exception_reason` | `VARCHAR` | Simulated exception reason. |
| `recommendation_id` | `VARCHAR` | Unique recommendation identifier. |
| `data_source` | `VARCHAR` | Provenance label separating real, estimated, derived, and simulated data. |

