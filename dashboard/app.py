from __future__ import annotations

import json
from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "warehouse" / "display_optimization.duckdb"

st.set_page_config(page_title="陈列资源决策台", page_icon="◈", layout="wide")
st.markdown(
    """
<style>
.stApp {background:#f5f2ec;color:#16332c}.block-container{padding-top:2rem;max-width:1400px}
[data-testid="stMetric"]{background:white;border:1px solid #e1ded7;padding:16px;border-radius:14px}
.eyebrow{font-size:.75rem;letter-spacing:.15em;text-transform:uppercase;color:#28705d;font-weight:700}
.source-note{background:#173c35;color:#eef9f5;padding:18px;border-radius:14px;margin:12px 0}
</style>""",
    unsafe_allow_html=True,
)

if not DB.exists():
    st.error("数据库尚未构建。请先运行 `make build`。")
    st.stop()

con = duckdb.connect(str(DB), read_only=True)
stores = con.execute("select store_id from dim_store order by store_id").df()["store_id"].tolist()
weeks = (
    con.execute("select distinct week from mart_display_performance order by week")
    .df()["week"]
    .tolist()
)
with st.sidebar:
    st.header("决策范围")
    store = st.selectbox("门店", stores)
    week = st.selectbox("周次", weeks, index=len(weeks) - 1)
    st.caption("演示容量与位置编号不代表真实门店平面图。")

st.markdown('<div class="eyebrow">MULTI-STORE DISPLAY INTELLIGENCE</div>', unsafe_allow_html=True)
st.title("陈列资源效率与配置决策台")
st.markdown(
    '<div class="source-note"><b>来源分层</b>　交易/商品/促销 = 真实匿名样本；增量/置信度 = 模型估计；容量/位置/审计 = 模拟配置。所有收益仅为模型预测。</div>',
    unsafe_allow_html=True,
)

perf = con.execute(
    "select * from mart_display_performance where store_id=? and week=?", [store, week]
).df()
recs = con.execute(
    "select * from mart_allocation_recommendations where store_id=? order by resource_type,resource_position",
    [store],
).df()
dq = con.execute("select * from dq_results").df()
audit = con.execute("select * from review_recommendation_execution where store_id=?", [store]).df()
scenario = con.execute("select * from mart_scenario_comparison where store_id=?", [store]).df()

c1, c2, c3, c4 = st.columns(4)
c1.metric("观察销售额", f"${perf.actual_sales.sum():,.0f}")
c2.metric("推荐位置数", f"{len(recs)}")
c3.metric("模型预测增量", f"${recs.predicted_incremental_sales.sum():,.1f}")
c4.metric("质量告警", f"{(dq.status != 'PASS').sum()}")

tab1, tab2, tab3, tab4 = st.tabs(["效率诊断", "方案与推荐", "执行审计", "口径与假设"])
with tab1:
    left, right = st.columns([1.25, 1])
    with left:
        fig = px.bar(
            perf.sort_values("sales_per_product"),
            x="sales_per_product",
            y="display_name",
            color="actual_sales",
            orientation="h",
            title="资源位效率（观察性描述）",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        rank = perf.sort_values("store_efficiency_rank")[
            [
                "category",
                "display_name",
                "sales_per_product",
                "store_efficiency_rank",
                "cross_store_category_rank",
            ]
        ]
        st.subheader("门店 / 品类排名")
        st.dataframe(rank, width="stretch", hide_index=True)
with tab2:
    fig = px.bar(
        scenario,
        x="scenario",
        y="predicted_incremental_sales",
        color="constraint_violations",
        title="当前、贪心与 OR-Tools 方案（模型预测）",
    )
    st.plotly_chart(fig, width="stretch")
    display = recs[
        [
            "resource_position",
            "resource_type",
            "current_category",
            "recommended_category",
            "predicted_incremental_sales",
            "confidence",
            "change_cost",
            "reason_code",
            "solver_status",
        ]
    ]
    st.dataframe(display, width="stretch", hide_index=True)
with tab3:
    if len(audit):
        fig = px.histogram(
            audit, x="execution_status", color="execution_status", title="模拟审计异常"
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(audit, width="stretch", hide_index=True)
with tab4:
    st.subheader("数据质量状态")
    st.dataframe(
        dq[["check_name", "severity", "failures", "status", "rule_description"]],
        width="stretch",
        hide_index=True,
    )
    metrics = json.loads((ROOT / "outputs" / "model_metrics.json").read_text())
    st.subheader("模型验证与边界")
    st.json(metrics)
    st.markdown("""
    - 基线控制商品历史销售、门店、周次/季节、品类、零售折扣、优惠券、mailer 和商品先验畅销度。
    - 展示位分配并非随机，可能存在选品、库存、价格与门店执行等未观测混杂；结果不能解释为因果提升。
    - 资源容量、位置编号、适配、成本与审计为模拟字段，仅用于展示完整业务闭环。
    """)
con.close()
