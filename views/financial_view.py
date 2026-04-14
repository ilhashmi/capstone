import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.styles import PLOTLY, C, kpi, sec_hdr


def _L(**kw):
    d = dict(**PLOTLY); d.update(kw); return d


def render(df, baskets, monthly, branch_df, cat_df, sku_df,
           employee_df, top_cust, basket_trend_df, cogs_df,
           payment_df, dow_df, hour_df, retention_info):

    st.markdown('<div class="sec-hdr">Financial Dashboard</div>', unsafe_allow_html=True)

    if monthly.empty:
        st.warning("No financial data available.")
        return

    latest  = monthly.iloc[-1]
    mom_rev = latest.get("mom_revenue_pct", None)
    mom_gp  = latest.get("mom_profit_pct",  None)

    # KPIs ──────────────────────────────────────────────────────────────────
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        kpi("Total Revenue", f"{monthly['revenue'].sum():,.0f}",
            sub=f"Latest month: {latest['revenue']:,.0f}",
            delta=float(mom_rev) if mom_rev and not np.isnan(mom_rev) else None)
    with c2:
        gp = monthly["profit"].sum() if "profit" in monthly.columns else 0
        kpi("Gross Profit", f"{gp:,.0f}",
            sub=f"Latest: {latest.get('profit',0):,.0f}",
            delta=float(mom_gp) if mom_gp and not np.isnan(mom_gp) else None)
    with c3:
        kpi("Gross Margin %", f"{latest['gross_margin_pct']:.1f}", suffix="%",
            sub=f"Overall: {(monthly['profit'].sum()/monthly['revenue'].sum()*100):.1f}%")
    with c4:
        kpi("Total Units Sold", f"{int(monthly['units_sold'].sum()):,}",
            sub=f"Latest: {int(latest['units_sold']):,}")
    with c5:
        kpi("Transactions", f"{int(monthly['transactions'].sum()):,}",
            sub=f"Avg basket: {monthly['avg_basket_value'].mean():,.2f}")

    st.markdown("---")

    # Revenue + GP trend ────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["month_str"], y=monthly["revenue"],
        name="Revenue", marker_color=C["blue"], opacity=0.8,
        hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.1f}<extra></extra>"))
    if "profit" in monthly.columns:
        fig.add_trace(go.Bar(x=monthly["month_str"], y=monthly["profit"],
            name="Gross Profit", marker_color=C["green"], opacity=0.8,
            hovertemplate="<b>%{x}</b><br>Gross Profit: %{y:,.1f}<extra></extra>"))
    fig.update_layout(**_L(
        title="Monthly Revenue & Gross Profit",
        barmode="group", height=320,
        xaxis_title="Month", yaxis_title="Amount (BD)",
    ))
    st.plotly_chart(fig, use_container_width=True)

    # MoM + Margin row ──────────────────────────────────────────────────────
    cl, cr = st.columns(2)
    with cl:
        mom_data = monthly[monthly["mom_revenue_pct"].notna()].copy()
        if not mom_data.empty:
            fig2 = go.Figure(go.Bar(
                x=mom_data["month_str"], y=mom_data["mom_revenue_pct"],
                marker_color=[C["green"] if v>=0 else C["red"] for v in mom_data["mom_revenue_pct"]],
                opacity=0.85,
                hovertemplate="<b>%{x}</b><br>MoM Revenue: %{y:+.1f}%<extra></extra>",
            ))
            fig2.add_hline(y=0, line_color=C["faint"], line_width=1)
            fig2.update_layout(**_L(title="Month-over-Month Revenue Growth %",
                height=260, xaxis_title="Month", yaxis_title="Growth %"))
            st.plotly_chart(fig2, use_container_width=True)
    with cr:
        if "gross_margin_pct" in monthly.columns:
            avg_m = monthly["gross_margin_pct"].mean()
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=monthly["month_str"], y=monthly["gross_margin_pct"],
                mode="lines+markers+text",
                text=[f"{v:.1f}%" for v in monthly["gross_margin_pct"]],
                textposition="top center", textfont=dict(size=11,color=C["purple"]),
                line=dict(color=C["purple"],width=2), marker=dict(size=7),
                hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>"))
            fig3.add_hline(y=avg_m, line_dash="dot", line_color=C["faint"],
                           annotation_text=f"Avg {avg_m:.1f}%",
                           annotation_font_color=C["faint"])
            fig3.update_layout(**_L(title="Gross Margin % Trend",
                height=260, xaxis_title="Month", yaxis_title="Gross Margin %"))
            st.plotly_chart(fig3, use_container_width=True)

    # Performance Drivers ───────────────────────────────────────────────────
    sec_hdr("Performance Drivers")
    cl2, cr2 = st.columns(2)

    with cl2:
        if not branch_df.empty:
            branches = branch_df["branch"].unique()
            fig4 = go.Figure()
            palette = [C["blue"],C["teal"],C["purple"]]
            for i,b in enumerate(branches):
                sub = branch_df[branch_df["branch"]==b].sort_values("month_str")
                fig4.add_trace(go.Bar(
                    x=sub["month_str"], y=sub["revenue"], name=b,
                    marker_color=palette[i%len(palette)], opacity=0.85,
                    hovertemplate=f"<b>{b}</b> %{{x}}<br>Revenue: %{{y:,.1f}}<extra></extra>"))
            fig4.update_layout(**_L(title="Branch Revenue by Month",
                barmode="group", height=280,
                xaxis_title="Month", yaxis_title="Revenue (BD)"))
            st.plotly_chart(fig4, use_container_width=True)

    with cr2:
        if not cat_df.empty:
            fig5 = go.Figure(go.Pie(
                labels=cat_df["category"].str.title(),
                values=cat_df["revenue"], hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=11, color="#E8EAF0"),
                marker=dict(colors=px.colors.qualitative.Set2, line=dict(color="#1A1D2E",width=1.5)),
                hovertemplate="<b>%{label}</b><br>Revenue: %{value:,.1f} (%{percent})<extra></extra>"))
            fig5.update_layout(**_L(title="Revenue by Category",
                height=280, showlegend=False))
            st.plotly_chart(fig5, use_container_width=True)

    cl3, cr3 = st.columns(2)
    with cl3:
        if not basket_trend_df.empty:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(
                x=basket_trend_df["month_str"], y=basket_trend_df["avg_basket"],
                mode="lines+markers+text",
                text=[f"{v:.1f}" for v in basket_trend_df["avg_basket"]],
                textposition="top center", textfont=dict(size=11,color=C["teal"]),
                name="Avg Basket",
                line=dict(color=C["teal"],width=2), marker=dict(size=7),
                hovertemplate="<b>%{x}</b><br>Avg Basket: %{y:.2f}<extra></extra>"))
            fig6.update_layout(**_L(title="Average Basket Value / Transaction",
                height=260, xaxis_title="Month", yaxis_title="Avg Basket Value (BD)"))
            st.plotly_chart(fig6, use_container_width=True)

    with cr3:
        if cogs_df is not None and not cogs_df.empty:
            fig7 = go.Figure()
            fig7.add_trace(go.Bar(x=cogs_df["month_str"], y=cogs_df["cogs"],
                name="COGS", marker_color=C["orange"], opacity=0.8,
                hovertemplate="<b>%{x}</b><br>COGS: %{y:,.1f}<extra></extra>"))
            fig7.add_trace(go.Scatter(
                x=cogs_df["month_str"], y=cogs_df["cogs_pct"],
                name="COGS %", yaxis="y2", mode="lines+markers",
                line=dict(color=C["red"],width=2),
                hovertemplate="<b>%{x}</b><br>COGS %: %{y:.1f}%<extra></extra>"))
            fig7.update_layout(**_L(title="COGS & COGS % of Revenue",
                height=260, xaxis_title="Month", yaxis_title="COGS (BD)",
                yaxis2=dict(overlaying="y", side="right", showgrid=False,
                            tickfont=dict(color=C["red"],size=11),
                            title="COGS %", title_font=dict(color=C["red"],size=12))))
            st.plotly_chart(fig7, use_container_width=True)

    # Operational ───────────────────────────────────────────────────────────
    sec_hdr("Operational Intelligence")
    cl4, cr4 = st.columns(2)
    with cl4:
        if not dow_df.empty:
            fig8 = go.Figure(go.Bar(
                x=dow_df["dow"], y=dow_df["revenue"],
                marker_color=C["blue"], opacity=0.85,
                hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.1f}<extra></extra>"))
            fig8.update_layout(**_L(title="Sales by Day of Week",
                height=260, xaxis_title="Day of Week", yaxis_title="Revenue (BD)"))
            st.plotly_chart(fig8, use_container_width=True)
    with cr4:
        if not hour_df.empty:
            fig9 = go.Figure(go.Scatter(
                x=hour_df["hour"], y=hour_df["revenue"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color=C["teal"],width=2),
                fillcolor="rgba(12,133,153,0.10)",
                hovertemplate="<b>%{x}:00</b><br>Revenue: %{y:,.1f}<extra></extra>"))
            fig9.update_layout(**_L(title="Sales by Hour of Day",
                height=260, xaxis_title="Hour (24h)", yaxis_title="Revenue (BD)"))
            st.plotly_chart(fig9, use_container_width=True)

    # SKU velocity
    if not sku_df.empty:
        st.markdown("**Top 20 SKUs by Revenue**")
        top_sku = sku_df.head(20)[["name","category","units","revenue","profit","margin_pct","transactions"]].copy()
        for c in ["revenue","profit"]: top_sku[c] = top_sku[c].round(1)
        st.dataframe(top_sku.rename(columns={"name":"Product","category":"Category","units":"Units",
            "revenue":"Revenue","profit":"Profit","margin_pct":"Margin %","transactions":"Txns"}),
            use_container_width=True, hide_index=True)

    # Employee + top customers
    cl5, cr5 = st.columns(2)
    with cl5:
        if not employee_df.empty:
            st.markdown("**Sales by Employee**")
            emp = employee_df[["employee","revenue","profit","units","transactions"]].copy()
            for c in ["revenue","profit"]: emp[c] = emp[c].round(1) if c in emp.columns else 0
            st.dataframe(emp.rename(columns={"employee":"Employee","revenue":"Revenue",
                "profit":"Profit","units":"Units","transactions":"Transactions"}),
                use_container_width=True, hide_index=True)
    with cr5:
        if not top_cust.empty:
            st.markdown("**Top 10 Customers by Spend**")
            tc = top_cust[["customer","revenue","profit","orders","units"]].copy()
            for c in ["revenue","profit"]: tc[c] = tc[c].round(1) if c in tc.columns else 0
            st.dataframe(tc.rename(columns={"customer":"Customer","revenue":"Revenue",
                "profit":"Profit","orders":"Orders","units":"Units"}),
                use_container_width=True, hide_index=True)

    # Top 10 tabs
    sec_hdr("Top 10 Product Rankings")
    t1,t2,t3 = st.tabs(["By Revenue","By Qty","By Profit"])
    from core.finance_engine import sku_velocity
    for tab, sort_col, label in [
        (t1,"revenue","Revenue"), (t2,"units","Units"), (t3,"profit","Profit")
    ]:
        with tab:
            t = sku_df.nlargest(10, sort_col)[["name","category",sort_col]].copy()
            t[sort_col] = t[sort_col].round(1)
            st.dataframe(t.rename(columns={"name":"Product","category":"Category",sort_col:label}),
                use_container_width=True, hide_index=True)

    st.markdown("---")
    st.download_button("Download P&L Summary (CSV)",
        monthly.to_csv(index=False).encode("utf-8"),
        f"pnl_{datetime.date.today()}.csv","text/csv")
