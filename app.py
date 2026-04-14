
import io, warnings
warnings.filterwarnings("ignore")
from types import SimpleNamespace

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Flow ERP",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.styles import apply_theme
from core.processor import load_file, smart_detect, preprocess, build_baskets
from core.inventory_engine import (
    build_monthly_grain, engineer_features, build_abc_xyz,
    train_quantile_models, predict_next_period,
    train_classifier, predict_stages,
    build_facts, assemble_master, build_category_view,
)
from core.finance_engine import (
    monthly_summary, branch_performance, category_contribution,
    basket_trend, cogs_trend, employee_performance,
    sku_velocity, sales_by_dow, sales_by_hour,
    top10_customers, retention_frequency,
)
from core.churn_engine import (
    build_customer_table, rfm_score, churn_risk,
    customer_retention_rate, new_vs_returning,
    pareto_customers, product_affinity, executive_summary,
)
import views.inventory_view as inv_view
import views.financial_view as fin_view
import views.customer_view  as cust_view

apply_theme()


@st.cache_data(show_spinner=False)
def run_pipeline(file_bytes: bytes, file_name: str, mapping_frozen: tuple, next_week: bool):
    buf    = io.BytesIO(file_bytes)
    df_raw = load_file(buf, file_name)
    df     = preprocess(df_raw, dict(mapping_frozen))
    baskets= build_baskets(df)
    snapshot = pd.Timestamp(df["date"].max()) + pd.Timedelta(days=1)
    df_pos = df[df["qty"] > 0].copy()

    # Inventory ─────────────────────────────────────────────────────────────
    monthly, le = build_monthly_grain(df)
    featured    = engineer_features(monthly)
    meta        = build_abc_xyz(monthly, df_pos)
    meta_le     = meta.copy()
    meta_le["cat_encoded"] = le.transform(
        meta_le["category"].fillna("unknown").apply(
            lambda x: x if x in le.classes_ else le.classes_[0]
        )
    )
    m25, m50, m75, feat_imp = train_quantile_models(featured)
    predictions = predict_next_period(featured, m25, m50, m75, next_week=next_week)
    clf, _      = train_classifier(featured, meta_le)
    stages      = predict_stages(clf, meta_le, featured)
    facts       = build_facts(monthly, df_pos)
    master      = assemble_master(predictions, meta, facts, stages, monthly)
    cat_view    = build_category_view(monthly)

    # Finance ───────────────────────────────────────────────────────────────
    monthly_fin = monthly_summary(df, baskets)
    branch_df   = branch_performance(df, baskets)
    cat_df      = category_contribution(df)
    bkt_trend   = basket_trend(baskets)
    cogs_df     = cogs_trend(df)
    emp_df      = employee_performance(df, baskets)
    sku_df      = sku_velocity(df)
    dow_df      = sales_by_dow(df)
    hour_df     = sales_by_hour(df)
    top_cust    = top10_customers(df)
    ret_info    = retention_frequency(df)

    # Customer ──────────────────────────────────────────────────────────────
    cust_base = build_customer_table(df, baskets, snapshot)
    crr_df    = customer_retention_rate(df)
    if cust_base is not None and not cust_base.empty:
        cust_rfm  = churn_risk(rfm_score(cust_base))
        new_ret   = new_vs_returning(df, baskets)
        pareto    = pareto_customers(cust_rfm)
        affinity  = product_affinity(df)
        exec_summ = executive_summary(cust_rfm, crr_df, snapshot)
    else:
        cust_rfm, new_ret, pareto, affinity, exec_summ = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}

    return SimpleNamespace(
        df=df, baskets=baskets,
        master=master, monthly_inv=monthly, featured=featured,
        cat_view=cat_view, feat_imp=feat_imp,
        monthly_fin=monthly_fin, branch=branch_df, cat=cat_df,
        bkt_trend=bkt_trend, cogs=cogs_df, employee=emp_df,
        sku=sku_df, dow=dow_df, hour=hour_df,
        top_cust=top_cust, ret_info=ret_info,
        cust_rfm=cust_rfm, crr=crr_df,
        new_ret=new_ret, pareto=pareto, affinity=affinity,
        exec_summ=exec_summ, snapshot=snapshot,
        next_week=next_week,
    )


# Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Flow ERP")
    st.caption("Inventory · Finance · Customer Intelligence")
    st.divider()

    uploaded = st.file_uploader("Upload sales file", type=["csv", "xlsx", "xls"])


# Welcome ───────────────────────────────────────────────────────────────────
if uploaded is None:
    st.markdown("## Flow ERP — Control Tower")
    st.markdown(
        "Upload a CSV or Excel sales export in the sidebar, map your columns, "
        "and click **Run Analysis** to activate all three modules."
    )
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="info-box">'
            '<b>📦 Inventory Intelligence</b><br>'
            'LightGBM quantile forecasting (25/50/75 percentile) · '
            'ABC×XYZ portfolio classification · Lifecycle staging</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="info-box">'
            '<b>💰 Financial Dashboard</b><br>'
            'P&amp;L · Gross margin · COGS trend · Branch benchmarking · '
            'Employee performance · Basket analytics</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="info-box">'
            '<b>👤 Customer Intelligence</b><br>'
            'RFM quintile scoring · LightGBM churn risk · '
            'Win-back priority list · Retention rate · Product affinity</div>',
            unsafe_allow_html=True,
        )
    st.stop()


# Column mapping ─────────────────────────────────────────────────────────────
with st.sidebar:
    uploaded.seek(0)
    try:
        df_peek = load_file(io.BytesIO(uploaded.read()), uploaded.name)
    except Exception as e:
        st.error(str(e)); st.stop()

    st.success(f"✓ {len(df_peek):,} rows · {df_peek.shape[1]} cols")
    sug      = smart_detect(df_peek)
    all_cols = ["(none)"] + list(df_peek.columns)

    st.markdown("**Column Mapping**")

    def _col(label, key, req=False):
        default = sug.get(key)
        idx = all_cols.index(default) if default in all_cols else 0
        return st.selectbox(f"{label}{' *' if req else ''}", all_cols, index=idx, key=f"col_{key}")

    col_id   = _col("Product ID",          "id",       req=True)
    col_name = _col("Product Name",         "name",     req=True)
    col_cat  = _col("Category",             "category", req=True)
    col_qty  = _col("Qty",                  "qty",      req=True)
    col_date = _col("Date / Time",          "date",     req=True)
    col_sid  = _col("Sale / Transaction ID","sale_id",  req=True)

    with st.expander("Financial columns"):
        col_sub  = _col("Subtotal / Revenue", "subtotal")
        col_cost = _col("Cost (COGS)",         "cost")
        col_pft  = _col("Profit",             "profit")
        col_sp   = _col("Selling Price",      "selling_price")

    with st.expander("Operations & Customer"):
        col_br   = _col("Branch",             "branch")
        col_emp  = _col("Employee",           "employee")
        col_cust = _col("Customer Name",      "customer")
        col_cid  = _col("Customer ID",        "customer_id")

    mapping = {k:v for k,v in [
        ("id",col_id),("name",col_name),("category",col_cat),
        ("qty",col_qty),("date",col_date),("sale_id",col_sid),
        ("subtotal",col_sub),("cost",col_cost),("profit",col_pft),
        ("branch",col_br),("employee",col_emp),("selling_price",col_sp),
        ("customer",col_cust),("customer_id",col_cid),
    ] if v != "(none)"}

    missing = [k for k in ["id","name","category","qty","date","sale_id"] if k not in mapping]
    if missing:
        st.error(f"Map required columns: {', '.join(missing)}")
        st.stop()

    st.divider()
    st.markdown("**Forecast Horizon**")
    horizon   = st.radio(
        "Predict for",
        ["Next Month", "Next Week"],
        help="Next Week scales the monthly model by 1/4.33 (proportional disaggregation).",
    )
    next_week = horizon == "Next Week"

    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)


# Run pipeline ──────────────────────────────────────────────────────────────
if not run_btn and "R" not in st.session_state:
    st.info("Map your columns in the sidebar, then click **Run Analysis**.")
    st.stop()

if run_btn or "R" not in st.session_state:
    uploaded.seek(0)
    with st.spinner("Running analysis…"):
        try:
            R = run_pipeline(
                uploaded.read(), uploaded.name,
                tuple(sorted(mapping.items())), next_week,
            )
            st.session_state["R"] = R
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            import traceback; st.code(traceback.format_exc())
            st.stop()

R = st.session_state["R"]
horizon_label = "Next Week" if R.next_week else "Next Month"

# Tabs ──────────────────────────────────────────────────────────────────────
tab_inv, tab_fin, tab_cust = st.tabs([
    "📦  Inventory Intelligence",
    "💰  Financial Dashboard",
    "👤  Customer Intelligence",
])

with tab_inv:
    inv_view.render(
        master=R.master, monthly=R.monthly_inv,
        cat_view=R.cat_view, feat_imp=R.feat_imp,
        horizon_label=horizon_label,
    )

with tab_fin:
    fin_view.render(
        df=R.df, baskets=R.baskets,
        monthly=R.monthly_fin,
        branch_df=R.branch, cat_df=R.cat,
        sku_df=R.sku, employee_df=R.employee,
        top_cust=R.top_cust,
        basket_trend_df=R.bkt_trend,
        cogs_df=R.cogs, payment_df=None,
        dow_df=R.dow, hour_df=R.hour,
        retention_info=R.ret_info,
    )

with tab_cust:
    cust_view.render(
        df=R.df, baskets=R.baskets,
        cust_rfm=R.cust_rfm, crr_df=R.crr,
        new_ret_df=R.new_ret, pareto_df=R.pareto,
        affinity_df=R.affinity, summary=R.exec_summ,
    )
