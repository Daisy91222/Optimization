-- Recommendation-to-execution traceability and exception review.
create or replace view review_recommendation_execution as
select r.recommendation_id, r.store_id, r.target_week, r.resource_position,
       r.recommended_category, a.observed_category, a.audit_date, a.photo_status,
       a.match_status, a.exception_reason,
       case when a.recommendation_id is null then 'missing_audit'
            when a.audit_date > a.planned_date + interval 3 day then 'late'
            when a.photo_status <> 'received' then 'missing_photo'
            when a.match_status <> 'matched' then 'mismatch'
            else 'executed' end as execution_status
from mart_allocation_recommendations r
left join mart_space_audit a using(recommendation_id);

create or replace view review_audit_quality as
select 'unknown_category' check_name, count(*) failures
from mart_space_audit a left join (select distinct product_category from dim_product) p
  on a.observed_category=p.product_category where p.product_category is null
union all
select 'duplicate_position_week', count(*) from (
 select 1 from mart_space_audit group by store_id,week,resource_position having count(*)>1
)
union all
select 'untraceable_recommendation', count(*) from mart_space_audit a
 left join mart_allocation_recommendations r using(recommendation_id)
 where r.recommendation_id is null;
