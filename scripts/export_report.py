#!/usr/bin/env python3
from __future__ import annotations

import html
import json

import plotly.express as px

from display_optimizer.config import OUTPUTS
from display_optimizer.db import connect


def table_html(df, max_rows=20):
    return df.head(max_rows).to_html(index=False, classes="data-table", border=0)


def main() -> None:
    con = connect(read_only=True)
    performance = con.execute(
        """select display_name, sum(actual_sales) actual_sales, sum(units) units,
                  avg(sales_per_product) avg_sales_per_product
           from mart_display_performance group by 1 order by actual_sales desc"""
    ).df()
    scenarios = con.execute(
        """select scenario, sum(predicted_incremental_sales) predicted_incremental_sales,
                  sum(change_count) change_count, sum(change_cost) change_cost,
                  avg(category_coverage_rate) category_coverage_rate,
                  avg(brand_concentration) brand_concentration,
                  avg(low_confidence_share) low_confidence_share,
                  sum(constraint_violations) constraint_violations
           from mart_scenario_comparison group by 1 order by 1"""
    ).df()
    dq = con.execute(
        "select check_name,severity,failures,status,rule_description from dq_results"
    ).df()
    recs = con.execute(
        """select store_id,resource_type,recommended_category,current_category,
                  predicted_incremental_sales,confidence,change_cost,reason_code
           from mart_allocation_recommendations order by store_id,resource_type"""
    ).df()
    audits = con.execute(
        "select execution_status,count(*) count from review_recommendation_execution group by 1"
    ).df()
    con.close()
    metrics = json.loads((OUTPUTS / "model_metrics.json").read_text())

    fig_perf = px.bar(
        performance,
        x="display_name",
        y="avg_sales_per_product",
        color="actual_sales",
        title="Observed display performance (descriptive)",
    )
    fig_scenario = px.bar(
        scenarios,
        x="scenario",
        y="predicted_incremental_sales",
        color="constraint_violations",
        title="Scenario comparison — model predicted",
    )
    fig_audit = px.pie(
        audits,
        names="execution_status",
        values="count",
        hole=0.55,
        title="Simulated execution audit",
    )
    charts = "".join(
        f.to_html(full_html=False, include_plotlyjs="inline" if i == 0 else False)
        for i, f in enumerate([fig_perf, fig_scenario, fig_audit])
    )
    report = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>陈列资源优化报告</title>
<style>body{{font-family:Inter,-apple-system,sans-serif;margin:0;background:#f4f1eb;color:#17221f}}
main{{max-width:1180px;margin:auto;padding:36px}} .hero{{background:#173c35;color:white;padding:34px;border-radius:22px}}
.tag{{color:#bce4d6;text-transform:uppercase;letter-spacing:.12em}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.card{{background:white;padding:22px;border-radius:16px;margin-top:18px;box-shadow:0 8px 24px #183b3320}}
.data-table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}
.note{{border-left:4px solid #dc8f3c;padding-left:14px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style></head>
<body><main><section class='hero'><div class='tag'>Portfolio MVP · Demo</div><h1>多门店陈列资源位效率评估与约束优化</h1>
<p>真实匿名交易/商品/促销样本 + 模型估计 + 明确标记的模拟运营配置</p></section>
<section class='card note'><b>解释边界：</b>展示位表现是观察性关联；增量与方案收益均为模型预测或情景模拟，不是已实现商业提升。</section>
<div class='grid'><section class='card'><h2>模型验证</h2><pre>{html.escape(json.dumps(metrics, ensure_ascii=False, indent=2))}</pre></section>
<section class='card'><h2>数据质量</h2>{table_html(dq)}</section></div>
<section class='card'>{charts}</section><section class='card'><h2>方案对比</h2>{table_html(scenarios)}</section>
<section class='card'><h2>推荐明细</h2>{table_html(recs, 40)}</section>
<section class='card'><h2>方法说明</h2><p>Ridge 固定效应基线控制商品历史、门店、周次/季节、品类、折扣、优惠券、邮寄广告与商品畅销度；CP-SAT 同时处理容量、上下限、适配、集中度、调整数、战略保留与低置信度约束。</p></section>
</main></body></html>"""
    target = OUTPUTS / "portfolio_report.html"
    target.write_text(report, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
