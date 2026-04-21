import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.styles import PLOTLY, C, STAGE_COLORS, ABCXYZ_COLORS, kpi, sec_hdr, module_header, tbl_wrap, empty_state, stage_badge, abc_badge, xyz_badge, badge


# ── Plotly helper ─────────────────────────────────────────────────────────────
def _L(**kw):
    d = dict(**PLOTLY)
    d.update(kw)
    return d


def render(master, monthly, cat_view, feat_imp, horizon_label):
    module_header("📦", "Inventory Intelligence", "AI-powered demand forecasting & portfolio classification")

    if master.empty:
        empty_state("No inventory data available.", "📭")
        return

    has_rev = "pred_revenue_mid" in master.columns and master["pred_revenue_mid"].notna().any()

    # ── Forecast Banner ───────────────────────────────────────────────────────
    n_lgb = (master["model_used"] == "LightGBM").sum() if "model_used" in master.columns else 0
    n_avg = len(master) - n_lgb
    st.markdown(
        f'<div class="forecast-banner">'
        f'<span>🔮</span>'
        f'<span><b>Horizon:</b> {horizon_label}</span>'
        f'<span class="fb-sep">|</span>'
        f'<span><b>{len(master):,}</b> products</span>'
        f'<span class="fb-sep">|</span>'
        f'<span>LightGBM quantile regression &nbsp;<span class="badge b-blue">{n_lgb} SKUs</span></span>'
        f'<span class="fb-sep">|</span>'
        f'<span>Avg fallback &nbsp;<span class="badge b-gray">{n_avg} SKUs</span></span>'
        f'<div class="fb-note">All columns labelled <b>Pred</b> are model forecasts — not actuals.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi("Products Tracked", f"{len(master):,}", accent="blue")
    with c2:
        kpi("Pred Units (mid)", f"{int(master['pred_qty_mid'].sum()):,}",
            sub=f"Next {horizon_label}", accent="blue")
    with c3:
        kpi("A-Class Products", f"{(master['abc']=='A').sum()}",
            sub=f"B-Class: {(master['abc']=='B').sum()}", accent="blue")
    with c4:
        trending = (master['stage'] == 'trending').sum()
        fast     = (master['stage'] == 'fast_mover').sum()
        kpi("Trending Now", f"{trending}",
            sub=f"Fast movers: {fast}", accent="green")
    with c5:
        dead_a = master[(master["stage"] == "dead") & (master["abc"] == "A")].shape[0]
        kpi("Dead A-Class", f"{dead_a}",
            sub="Urgent review needed" if dead_a > 0 else "All A-class healthy",
            accent="red" if dead_a > 0 else "green")

    # ── Alerts ────────────────────────────────────────────────────────────────
    dead_ab = master[(master["stage"] == "dead") & (master["abc"].isin(["A", "B"]))]
    slow_ab = master[(master["stage"] == "slow_mover") & (master["abc"].isin(["A", "B"]))]
    trend   = master[master["stage"] == "trending"]

    if not dead_ab.empty:
        names = ", ".join(dead_ab["name"].head(3).str.title().tolist())
        st.markdown(
            f'<div class="alert-box">🚨 <b>Dead A/B products ({len(dead_ab)}):</b> {names}'
            + (f' <i>+{len(dead_ab)-3} more</i>' if len(dead_ab) > 3 else '') +
            f'</div>',
            unsafe_allow_html=True,
        )
    if not slow_ab.empty:
        st.markdown(
            f'<div class="warn-box">⚠️ <b>Slow movers in A/B class:</b> {len(slow_ab)} products — consider promotions or clearance</div>',
            unsafe_allow_html=True,
        )
    if not trend.empty:
        names = ", ".join(trend["name"].head(3).str.title().tolist())
        st.markdown(
            f'<div class="success-box">✅ <b>Trending ({len(trend)}):</b> {names} — ensure stock coverage</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Sub-Tabs ──────────────────────────────────────────────────────────────
    tab_master, tab_queue, tab_cat, tab_model = st.tabs([
        "All Products", "Action Queue", "Category Analysis", "Summary",
    ])
    with tab_master:
        _tab_master(master, has_rev, horizon_label)
    with tab_queue:
        _tab_action_queue(master, horizon_label)
    with tab_cat:
        _tab_category(cat_view, monthly)
    with tab_model:
        _tab_model(master, monthly, feat_imp)


# ── TAB A: ALL PRODUCTS ───────────────────────────────────────────────────────
def _tab_master(master, has_rev, horizon_label):
    sec_hdr("Master Inventory Intelligence Table", "🗂")

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        abc_f = st.multiselect("ABC Class", ["A", "B", "C"], default=["A", "B", "C"], key="inv_abc")
    with fc2:
        all_stages = sorted(master["stage"].dropna().unique().tolist())
        stage_f = st.multiselect("Lifecycle Stage", all_stages, default=all_stages, key="inv_stage")
    with fc3:
        cats = sorted(master["category"].dropna().unique().tolist())
        cat_f = st.multiselect("Category", cats, default=cats[:8] if len(cats) > 8 else cats, key="inv_cat")
    with fc4:
        search = st.text_input("Search product", key="inv_search", placeholder="Name or ID…")

    view = master[
        master["abc"].isin(abc_f) &
        master["stage"].isin(stage_f) &
        master["category"].isin(cat_f)
    ].copy()
    if search:
        mask = (view["name"].str.contains(search, case=False, na=False) |
                view["base_id"].astype(str).str.contains(search, case=False, na=False))
        view = view[mask]

    st.markdown(
        f'<div class="stat-row">'
        f'<span class="stat-pill">Showing <b>{len(view):,}</b> of <b>{len(master):,}</b> products</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if len(view) == 0:
        empty_state("No products match the current filters.", "🔍")
        return

    # ── Forecast Range Chart ──────────────────────────────────────────────────
    top20 = view.nlargest(20, "pred_qty_mid").copy()
    top20["short"] = top20["name"].str.title().str[:35]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top20["short"], x=top20["pred_qty_mid"],
        name="Prediction (mid)", orientation="h",
        marker_color=C["blue"], opacity=0.85,
        error_x=dict(
            type="data", symmetric=False,
            array=(top20["pred_qty_high"] - top20["pred_qty_mid"]).clip(lower=0),
            arrayminus=(top20["pred_qty_mid"] - top20["pred_qty_low"]).clip(lower=0),
            color=C["faint"], thickness=1.5, width=5,
        ),
        hovertemplate="<b>%{y}</b><br>Predicted: %{x:.0f} units<extra></extra>",
    ))
    fig.update_layout(**_L(
        title=f"[Forecast] Next {horizon_label} — Predicted Units · Top 20 SKUs with 25/75 quantile range",
        height=520,
        yaxis=dict(autorange="reversed", **PLOTLY["yaxis"]),
        xaxis_title="Predicted Units",
        yaxis_title="Product",
    ))
    st.plotly_chart(fig, use_container_width=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    dcols = ["base_id", "name", "category", "abc", "xyz", "stage",
             "last_month_qty", "true_avg_6m", "wtd_avg_6m",
             "pred_qty_low", "pred_qty_mid", "pred_qty_high",
             "margin_pct", "days_since_sale", "months_active"]
    if has_rev:
        dcols.append("pred_revenue_mid")
    dcols = [c for c in dcols if c in view.columns]
    dd = view[dcols].copy()
    dd["stage"] = dd["stage"].apply(stage_badge)
    dd["abc"]   = dd["abc"].apply(abc_badge)
    dd["xyz"]   = dd["xyz"].apply(xyz_badge)
    dd = dd.rename(columns={
        "base_id": "ID", "name": "Product", "category": "Category",
        "abc": "ABC", "xyz": "XYZ", "stage": "Stage",
        "last_month_qty": "Last Mo (Actual)", "true_avg_6m": "Avg/Mo (Actual)", "wtd_avg_6m": "Wtd Avg/Mo",
        "pred_qty_low": "★ Pred Low", "pred_qty_mid": "★ Pred Mid", "pred_qty_high": "★ Pred High",
        "margin_pct": "Margin %",
        "days_since_sale": "Days Since Sale", "months_active": "Months Active",
        "pred_revenue_mid": "★ Pred Revenue",
    })
    st.write(tbl_wrap(dd.to_html(escape=False, index=False, classes="tbl")), unsafe_allow_html=True)
    st.markdown("")
    st.download_button(
        "⬇ Download Full Table (CSV)",
        view.to_csv(index=False).encode("utf-8"),
        f"inventory_master_{datetime.date.today()}.csv", "text/csv",
    )


# ── TAB B: ACTION QUEUE ───────────────────────────────────────────────────────
def _tab_action_queue(master, horizon_label):
    sec_hdr("Action Queue — Items Requiring Immediate Attention", "⚡")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            '<div class="chart-title">🪦 Dead A/B-class products</div>'
            '<div class="chart-subtitle">No sales in the last 60+ days</div>',
            unsafe_allow_html=True,
        )
        dead = master[(master["stage"] == "dead") & master["abc"].isin(["A", "B"])].copy()
        if dead.empty:
            st.markdown('<div class="success-box">✅ No dead A/B products — portfolio is healthy.</div>', unsafe_allow_html=True)
        else:
            d = dead[["name", "abc", "last_6m_qty", "days_since_sale", "true_avg_6m", "margin_pct"]].copy()
            d["abc"] = d["abc"].apply(abc_badge)
            d = d.rename(columns={
                "name": "Product", "abc": "ABC", "last_6m_qty": "6M Qty",
                "days_since_sale": "Days Dormant", "true_avg_6m": "Avg/Mo", "margin_pct": "Margin %",
            })
            st.write(tbl_wrap(d.to_html(escape=False, index=False, classes="tbl")), unsafe_allow_html=True)
            st.download_button(
                "⬇ Export Dead A/B List",
                dead.to_csv(index=False).encode("utf-8"),
                f"dead_ab_{datetime.date.today()}.csv", "text/csv", key="dl_dead",
            )

    with c2:
        st.markdown(
            '<div class="chart-title">🔥 Trending / Fast movers</div>'
            '<div class="chart-subtitle">Ensure adequate stock coverage</div>',
            unsafe_allow_html=True,
        )
        hot = master[master["stage"].isin(["trending", "fast_mover"])].copy()
        hot = hot.sort_values("pred_qty_mid", ascending=False)
        if hot.empty:
            st.markdown('<div class="info-box">No trending products detected at this time.</div>', unsafe_allow_html=True)
        else:
            h = hot.head(15)[["name", "abc", "stage", "last_month_qty",
                               "pred_qty_low", "pred_qty_mid", "pred_qty_high"]].copy()
            h["abc"]   = h["abc"].apply(abc_badge)
            h["stage"] = h["stage"].apply(stage_badge)
            h = h.rename(columns={
                "name": "Product", "abc": "ABC", "stage": "Stage",
                "last_month_qty": "Last Mo (Actual)",
                "pred_qty_low": "★ Pred Low", "pred_qty_mid": "★ Pred Mid", "pred_qty_high": "★ Pred High",
            })
            st.write(tbl_wrap(h.to_html(escape=False, index=False, classes="tbl")), unsafe_allow_html=True)

    st.markdown("---")

    # ── Slow movers ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="chart-title">🐢 Slow movers in A/B class</div>'
        '<div class="chart-subtitle">Below-average velocity — consider promotions or clearance</div>',
        unsafe_allow_html=True,
    )
    slow = master[(master["stage"] == "slow_mover") & master["abc"].isin(["A", "B"])].copy()
    if slow.empty:
        st.markdown('<div class="success-box">✅ No slow movers in A/B class.</div>', unsafe_allow_html=True)
    else:
        s = slow[["name", "abc", "xyz", "last_month_qty", "true_avg_6m", "margin_pct",
                   "days_since_sale", "pred_qty_mid"]].copy()
        s["abc"] = s["abc"].apply(abc_badge)
        s["xyz"] = s["xyz"].apply(xyz_badge)
        s = s.rename(columns={
            "name": "Product", "abc": "ABC", "xyz": "XYZ",
            "last_month_qty": "Last Mo (Actual)", "true_avg_6m": "Avg/Mo (Actual)",
            "margin_pct": "Margin %", "days_since_sale": "Days Since Sale",
            "pred_qty_mid": f"★ Pred ({horizon_label})",
        })
        st.write(tbl_wrap(s.to_html(escape=False, index=False, classes="tbl")), unsafe_allow_html=True)


# ── TAB C: CATEGORY ANALYSIS ──────────────────────────────────────────────────
def _tab_category(cat_view, monthly):
    sec_hdr("Category Analysis — Monthly Trends & Composition", "📊")

    if cat_view.empty:
        empty_state("No category data available.", "📭")
        return

    cats = sorted(cat_view["category"].unique().tolist())

    # ── Monthly Units Stacked Bar ──────────────────────────────────────────────
    cat_rev = cat_view.pivot_table(
        index="month_str", columns="category", values="qty_sold",
        aggfunc="sum", fill_value=0,
    ).reset_index()
    fig = go.Figure()
    palette = [
    "#1E293B", 
    "#3B82F6", 
    "#10B981", 
    "#F59E0B", 
    "#EF4444", 
    "#8B5CF6", 
    "#06B6D4", 
    "#6366F1", 
    "#F97316",
    "#94A3B8"  ]
    for i, cat in enumerate([c for c in cats if c in cat_rev.columns]):
        fig.add_trace(go.Bar(
            x=cat_rev["month_str"], y=cat_rev[cat], name=cat,
            marker_color=palette[i % len(palette)], opacity=0.85,
            hovertemplate=f"<b>{cat}</b><br>Month: %{{x}}<br>Units: %{{y:,}}<extra></extra>",
        ))
    fig.update_layout(**_L(
        title="Monthly Units Sold by Category",
        barmode="stack", height=380,
        xaxis_title="Month", yaxis_title="Total Units Sold",
        legend=dict(orientation="h", y=-0.28, **PLOTLY["legend"]),
    ))
    st.plotly_chart(fig, use_container_width=True)

    # ── Revenue & Margin Charts ────────────────────────────────────────────────
    cat_tot = cat_view.groupby("category").agg(
        total_qty=("qty_sold", "sum"),
        total_revenue=("revenue", "sum"),
        total_profit=("profit", "sum"),
        months=("month_str", "nunique"),
    ).reset_index()
    cat_tot["margin_pct"] = (
        cat_tot["total_profit"] / cat_tot["total_revenue"].replace(0, np.nan) * 100
    ).round(1).fillna(0)
    cat_tot = cat_tot.sort_values("total_revenue", ascending=False)

    cl, cr = st.columns(2)
    with cl:
        fig2 = go.Figure(go.Bar(
            x=cat_tot["category"].str.title(), y=cat_tot["total_revenue"],
            name="Revenue", marker_color=C["blue"], opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.0f}<extra></extra>",
        ))
        fig2.update_layout(**_L(
            title="Total Revenue by Category",
            height=320, xaxis_tickangle=-30,
            xaxis_title="Category", yaxis_title="Total Revenue",
        ))
        st.plotly_chart(fig2, use_container_width=True)

    with cr:
        bar_colors = [
            C["green"] if v >= 25 else C["yellow"] if v >= 15 else C["red"]
            for v in cat_tot["margin_pct"]
        ]
        fig3 = go.Figure(go.Bar(
            x=cat_tot["category"].str.title(), y=cat_tot["margin_pct"],
            name="Gross Margin %", marker_color=bar_colors, opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
        ))
        avg_m = cat_tot["margin_pct"].mean()
        fig3.add_hline(y=avg_m, line_dash="dot", line_color=C["faint"],
                       annotation_text=f"Avg {avg_m:.1f}%",
                       annotation_font_color=C["faint"])
        fig3.update_layout(**_L(
            title="Gross Margin % by Category",
            height=320, xaxis_tickangle=-30,
            xaxis_title="Category", yaxis_title="Gross Margin %",
        ))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Category Drill-Down ────────────────────────────────────────────────────
    sec_hdr("Category Drill-Down — Monthly Trend", "🔍")
    chosen = st.selectbox("Select category", cats, key="cat_drilldown")
    sub = cat_view[cat_view["category"] == chosen].sort_values("month_str")
    if not sub.empty:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=sub["month_str"], y=sub["qty_sold"],
            name="Units Sold", marker_color=C["blue"], opacity=0.8,
            hovertemplate="<b>%{x}</b><br>Units: %{y:,}<extra></extra>",
        ))
        fig4.add_trace(go.Scatter(
            x=sub["month_str"], y=sub["revenue"],
            name="Revenue", yaxis="y2",
            mode="lines+markers",
            line=dict(color=C["green"], width=2), marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.1f}<extra></extra>",
        ))
        fig4.update_layout(**_L(
            title=f"{chosen} — Monthly Units & Revenue",
            height=320, xaxis_title="Month", yaxis_title="Units Sold",
            yaxis2=dict(
                overlaying="y", side="right",
                tickfont=dict(color=C["green"], size=11),
                title="Revenue", title_font=dict(color=C["green"], size=12),
                showgrid=False,
            ),
        ))
        st.plotly_chart(fig4, use_container_width=True)

        fig5 = go.Figure(go.Bar(
            x=sub["month_str"], y=sub["mom_qty"].fillna(0),
            marker_color=[C["green"] if v >= 0 else C["red"] for v in sub["mom_qty"].fillna(0)],
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>MoM Change: %{y:+.1f}%<extra></extra>",
        ))
        fig5.add_hline(y=0, line_color=C["faint"], line_width=1)
        fig5.update_layout(**_L(
            title=f"{chosen} — Month-over-Month Units Change (%)",
            height=240, xaxis_title="Month", yaxis_title="MoM Change %",
        ))
        st.plotly_chart(fig5, use_container_width=True)


# ── TAB D: SUMMARY ────────────────────────────────────────────────────────────
def _tab_model(master, monthly, feat_imp):
    sec_hdr("Portfolio Summary", "🗺")

    cl, cr = st.columns(2)

    with cl:
        if "abcxyz" in master.columns:
            all_combos = [f"{a}{x}" for a in ["A", "B", "C"] for x in ["X", "Y", "Z"]]
            matrix_data = master.groupby(["abc", "xyz"]).size().reset_index(name="count")
            matrix_data["abcxyz"] = matrix_data["abc"] + matrix_data["xyz"]
            existing = matrix_data.set_index("abcxyz")["count"].reindex(all_combos, fill_value=0)
            fig = go.Figure(go.Bar(
                x=existing.index, y=existing.values,
                marker_color=[ABCXYZ_COLORS.get(c, C["gray"]) for c in existing.index],
                opacity=0.85,
                hovertemplate="<b>%{x}</b><br>Products: %{y}<extra></extra>",
            ))
            fig.update_layout(**_L(
                title="ABC×XYZ Portfolio Matrix",
                height=300, xaxis_title="ABC×XYZ Class", yaxis_title="Product Count",
            ))
            st.plotly_chart(fig, use_container_width=True)

    with cr:
        stage_counts = master["stage"].value_counts().reset_index()
        stage_counts.columns = ["stage", "count"]
        fig2 = go.Figure(go.Bar(
            x=stage_counts["stage"].str.replace("_", " ").str.title(),
            y=stage_counts["count"],
            marker_color=[STAGE_COLORS.get(s, C["gray"]) for s in stage_counts["stage"]],
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Products: %{y}<extra></extra>",
        ))
        fig2.update_layout(**_L(
            title="Lifecycle Stage Distribution",
            height=300, xaxis_title="Stage", yaxis_title="Product Count",
        ))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Data Quality ───────────────────────────────────────────────────────────
    sec_hdr("Data Quality", "🔬")
    monthly_copy = monthly.copy()
    monthly_copy["month"] = pd.to_datetime(monthly_copy["month"])
    dq = pd.DataFrame([
        ("Products in model",       f"{master['base_id'].nunique():,}"),
        ("Months of training data", f"{monthly_copy['month'].nunique()}"),
        ("Training rows (total)",   f"{len(monthly_copy):,}"),
        ("Products w/ 3+ months",   f"{(monthly_copy.groupby('base_id')['month'].count() >= 3).sum()}"),
    ], columns=["Metric", "Value"])
    st.dataframe(dq, use_container_width=True, hide_index=True)
