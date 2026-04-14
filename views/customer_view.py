"""
views/customer_view.py — Customer Intelligence & Churn Risk, dark theme.
"""
import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.styles import PLOTLY, C, SEG_COLORS, CHURN_COLORS, kpi, sec_hdr, badge


def _L(**kw):
    d = dict(**PLOTLY); d.update(kw); return d


def render(df, baskets, cust_rfm, crr_df, new_ret_df, pareto_df, affinity_df, summary):
    st.markdown('<div class="sec-hdr">Customer Intelligence & Churn Risk</div>', unsafe_allow_html=True)

    if cust_rfm is None or cust_rfm.empty:
        st.markdown(
            '<div class="warn-box">Map a Customer ID / Name column to unlock this module.</div>',
            unsafe_allow_html=True); return

    # ── Level 1: Executive Header ─────────────────────────────────────────────
    sec_hdr("Executive Status")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        crr_val = summary.get("last_crr")
        kpi("Customer Retention Rate",
            f"{crr_val:.1f}" if crr_val else "—", suffix="%" if crr_val else "",
            sub=f"6-mo avg: {summary.get('avg_crr_6m','—')}%",
            delta=summary.get("crr_trend"))
    with c2:
        kpi("Active Customers (90d)", f"{summary.get('active_90d',0):,}")
    with c3:
        kpi("Average LTV", f"{summary.get('avg_ltv',0):,.1f}", sub="Lifetime value")
    with c4:
        tl = summary.get("churn_traffic_light","gray")
        tl_label = {"green":"Healthy","yellow":"Monitor","red":"Alert"}.get(tl,"—")
        tl_color = {"green":C["green"],"yellow":C["yellow"],"red":C["red"]}.get(tl,C["gray"])
        at_risk   = summary.get("at_risk_pct",0)
        st.markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Churn Alert</div>
  <div class="kpi-value" style="color:{tl_color};font-size:18px">{tl_label}</div>
  <div class="kpi-sub">{at_risk:.1f}% of customers at risk</div>
  <div class="kpi-sub">Revenue at risk: {summary.get('revenue_at_risk',0):,.0f}</div>
</div>""", unsafe_allow_html=True)

    if crr_df is not None and not crr_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=crr_df["month"], y=crr_df["crr_pct"],
            mode="lines+markers+text",
            text=[f"{v:.0f}%" for v in crr_df["crr_pct"]],
            textposition="top center", textfont=dict(size=11,color=C["teal"]),
            line=dict(color=C["teal"],width=2), marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>CRR: %{y:.1f}%<extra></extra>"))
        avg_crr = crr_df["crr_pct"].mean()
        fig.add_hline(y=avg_crr, line_dash="dot", line_color=C["faint"],
                      annotation_text=f"Avg {avg_crr:.1f}%",
                      annotation_font_color=C["faint"])
        fig.update_layout(**_L(title="Customer Retention Rate — Month by Month",
            height=240, xaxis_title="Month", yaxis_title="Retention Rate %"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Level 2: Behavioral Engine ────────────────────────────────────────────
    sec_hdr("Behavioral Engine")
    cl, cr = st.columns(2)
    with cl:
        seg_c = cust_rfm["rfm_segment"].value_counts().reset_index()
        seg_c.columns = ["segment","count"]
        seg_c = seg_c.sort_values("count",ascending=True)
        fig2 = go.Figure(go.Bar(
            y=seg_c["segment"], x=seg_c["count"], orientation="h",
            marker_color=[SEG_COLORS.get(s,C["gray"]) for s in seg_c["segment"]],
            opacity=0.85,
            hovertemplate="<b>%{y}</b>: %{x} customers<extra></extra>"))
        fig2.update_layout(**_L(title="RFM Customer Segments",
            height=320, xaxis_title="Number of Customers", yaxis_title="RFM Segment"))
        st.plotly_chart(fig2, use_container_width=True)

    with cr:
        if new_ret_df is not None and not new_ret_df.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=new_ret_df["month_str"],
                y=new_ret_df.get("Returning",0), name="Returning",
                marker_color=C["green"], opacity=0.82,
                hovertemplate="<b>%{x}</b><br>Returning: %{y:,.1f}<extra></extra>"))
            fig3.add_trace(go.Bar(x=new_ret_df["month_str"],
                y=new_ret_df.get("New",0), name="New",
                marker_color=C["blue"], opacity=0.82,
                hovertemplate="<b>%{x}</b><br>New: %{y:,.1f}<extra></extra>"))
            fig3.update_layout(**_L(title="New vs Returning Customer Revenue",
                barmode="stack", height=320,
                xaxis_title="Month", yaxis_title="Revenue (BD)"))
            st.plotly_chart(fig3, use_container_width=True)

    # Pareto
    if pareto_df is not None and not pareto_df.empty:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=pareto_df["customer_pct"],
            y=pareto_df["monetary"], name="Individual revenue",
            marker_color=C["blue"], opacity=0.45,
            hovertemplate="Customer top %{x:.0f}%: %{y:,.0f}<extra></extra>"))
        fig4.add_trace(go.Scatter(x=pareto_df["customer_pct"],
            y=pareto_df["cum_pct"], name="Cumulative %", yaxis="y2",
            mode="lines", line=dict(color=C["orange"],width=2),
            hovertemplate="Top %{x:.0f}% customers → %{y:.1f}% of revenue<extra></extra>"))
        fig4.add_vline(x=20, line_dash="dot", line_color=C["faint"],
                       annotation_text="Top 20% customers",
                       annotation_font_color=C["faint"])
        fig4.add_hline(y=80, line_dash="dot", line_color=C["yellow"],
                       annotation_text="80% of revenue", yref="y2",
                       annotation_font_color=C["yellow"])
        fig4.update_layout(**_L(title="80/20 Pareto — Customer Revenue Distribution",
            height=320, xaxis_title="Customer Percentile (% of all customers)",
            yaxis_title="Individual Revenue",
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        tickfont=dict(color=C["orange"],size=11),
                        title="Cumulative Revenue %",
                        title_font=dict(color=C["orange"],size=12), range=[0,105])))
        st.plotly_chart(fig4, use_container_width=True)

    if affinity_df is not None and not affinity_df.empty:
        st.markdown("**Product Affinity — Frequently Co-Purchased Pairs**")
        aff = affinity_df.rename(columns={"product_a":"Product A","product_b":"Product B","co_purchases":"Co-Purchases"})
        st.dataframe(aff.head(20), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Level 3: Traction List ─────────────────────────────────────────────────
    sec_hdr("Win-Back Priority — Top 20 At-Risk VIPs")
    at_risk_vips = (
        cust_rfm[cust_rfm["churn_risk"].isin(["At Risk","Churned"])]
        .sort_values("monetary", ascending=False).head(20)
    )
    if at_risk_vips.empty:
        st.markdown('<div class="success-box">No at-risk high-value customers detected.</div>', unsafe_allow_html=True)
    else:
        rev_ar = at_risk_vips["monetary"].sum()
        st.markdown(f'<div class="alert-box">{len(at_risk_vips)} high-value customers at risk — combined lifetime spend: <b>{rev_ar:,.0f}</b></div>', unsafe_allow_html=True)
        rows=[]
        for _,r in at_risk_vips.iterrows():
            rb = '<span class="badge b-red">Churned</span>' if r["churn_risk"]=="Churned" else '<span class="badge b-yellow">At Risk</span>'
            ai = f"{r['avg_interval_days']:.0f}d" if r.get("avg_interval_days") else "—"
            rows.append(f'<tr><td>{str(r["customer"])[:30]}</td><td>{r["monetary"]:,.0f}</td><td>{int(r["frequency"])}</td><td>{ai}</td><td>{int(r["recency_days"])}d ago</td><td>{rb}</td></tr>')
        st.markdown(
            '<table class="tbl"><thead><tr><th>Customer</th><th>Lifetime Value</th><th>Visits</th><th>Usual Interval</th><th>Last Seen</th><th>Status</th></tr></thead><tbody>'+
            "".join(rows)+'</tbody></table>', unsafe_allow_html=True)
        st.markdown("")
        st.download_button("Export At-Risk List (CSV)",
            at_risk_vips.to_csv(index=False).encode("utf-8"),
            f"atrisk_{datetime.date.today()}.csv","text/csv")

    # ── Elite: Zero-sales filter ───────────────────────────────────────────────
    st.markdown("---")
    sec_hdr("Reactivation Filter")
    days_inactive = st.slider("Show customers inactive for more than X days",
                               14,180,30,7,key="zero_sales_slider")
    inactive = cust_rfm[cust_rfm["recency_days"]>days_inactive].sort_values("monetary",ascending=False)
    st.markdown(f'<div class="info-box">{len(inactive)} customers inactive {days_inactive}+ days — combined LTV: {inactive["monetary"].sum():,.0f}</div>', unsafe_allow_html=True)
    if not inactive.empty:
        show = inactive[["customer","monetary","frequency","recency_days","churn_risk","rfm_segment"]].head(30).copy()
        show["monetary"] = show["monetary"].round(1)
        st.dataframe(show.rename(columns={"customer":"Customer","monetary":"LTV","frequency":"Visits",
            "recency_days":"Days Inactive","churn_risk":"Risk","rfm_segment":"RFM Segment"}),
            use_container_width=True, hide_index=True)
        st.download_button(f"Export Reactivation List ({days_inactive}d+)",
            inactive.to_csv(index=False).encode("utf-8"),
            f"reactivation_{days_inactive}d_{datetime.date.today()}.csv","text/csv")

    # Segment export
    sec_hdr("RFM Segment Export")
    all_segs = sorted(cust_rfm["rfm_segment"].unique().tolist())
    chosen = st.selectbox("Select segment to export", all_segs, key="seg_export")
    seg_data = cust_rfm[cust_rfm["rfm_segment"]==chosen]
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Customers",  len(seg_data))
    with c2: st.metric("Total Revenue", f"{seg_data['monetary'].sum():,.0f}")
    with c3: st.metric("Avg LTV", f"{seg_data['monetary'].mean():,.0f}")
    if not seg_data.empty:
        st.download_button(f"Export '{chosen}' Segment (CSV)",
            seg_data.to_csv(index=False).encode("utf-8"),
            f"segment_{chosen.lower().replace(' ','_')}_{datetime.date.today()}.csv","text/csv",
            key=f"dl_{chosen}")
