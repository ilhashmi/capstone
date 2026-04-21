import numpy as np
import pandas as pd
from typing import Optional

def monthly_summary(df, baskets):
    rev = df[df["qty"]>0].groupby("month_str").agg(
        revenue   =("revenue","sum"),
        profit    =("profit", "sum") if "profit" in df.columns else ("revenue","count"),
        cost      =("cost",   "sum") if "cost"   in df.columns else ("revenue","count"),
        units_sold=("qty",    "sum"),
    ).reset_index()
    if "profit" not in df.columns:
        rev["profit"]=0.0; rev["cost"]=0.0
    txn = (
        baskets[~baskets["is_return"]]
        .groupby("month_str")
        .agg(transactions=("sale_id","nunique"),
             avg_basket_value=("basket_revenue","mean"))
        .reset_index()
    )
    m = rev.merge(txn, on="month_str", how="left")
    m["gross_margin_pct"] = np.where(m["revenue"]>0, (m["profit"]/m["revenue"]*100).round(1), 0.0)
    m["mom_revenue_pct"]  = m["revenue"].pct_change()*100
    m["mom_profit_pct"]   = m["profit"].pct_change()*100
    m["avg_basket_value"] = m["avg_basket_value"].round(2)
    return m.sort_values("month_str").reset_index(drop=True)


def branch_performance(df, baskets):
    rev = df[df["qty"]>0].groupby(["branch","month_str"]).agg(
        revenue=("revenue","sum"),
        profit =("profit","sum") if "profit" in df.columns else ("revenue","count"),
        units  =("qty","sum"),
    ).reset_index()
    if "profit" not in df.columns:
        rev["profit"]=0.0
    txn = (
        baskets[~baskets["is_return"]]
        .groupby(["branch","month_str"])
        .agg(transactions=("sale_id","nunique"), avg_basket=("basket_revenue","mean"))
        .reset_index()
    )
    return rev.merge(txn, on=["branch","month_str"], how="left")

def category_contribution(df):
    pos = df[df["qty"]>0].copy()
    c = pos.groupby("category").agg(
        revenue   =("revenue","sum"),
        profit    =("profit","sum") if "profit" in pos.columns else ("revenue","count"),
        cost      =("cost",  "sum") if "cost"   in pos.columns else ("revenue","count"),
        units     =("qty","sum"),
        sku_count =("base_id","nunique"),
    ).reset_index()
    if "profit" not in df.columns:
        c["profit"]=0.0; c["cost"]=0.0
    c["pct_revenue"]     = (c["revenue"]/c["revenue"].sum()*100).round(1)
    c["gross_margin_pct"]= np.where(c["revenue"]>0,(c["profit"]/c["revenue"]*100).round(1),0.0)
    return c.sort_values("revenue",ascending=False).reset_index(drop=True)


def basket_trend(baskets):
    return (
        baskets[~baskets["is_return"]].groupby("month_str")
        .agg(avg_basket=("basket_revenue","mean"),
             median_basket=("basket_revenue","median"),
             avg_items=("basket_items","mean"))
        .round(2).reset_index()
    )


def cogs_trend(df):
    if "cost" not in df.columns:
        return None
    return (
        df[df["qty"]>0].groupby("month_str")
        .agg(cogs=("cost","sum"), revenue=("revenue","sum"))
        .assign(cogs_pct=lambda x: (x["cogs"]/x["revenue"].replace(0,np.nan)*100).round(1))
        .reset_index()
    )


def employee_performance(df, baskets):
    rev = df[df["qty"]>0].groupby("employee").agg(
        revenue=("revenue","sum"),
        profit =("profit","sum") if "profit" in df.columns else ("revenue","count"),
        units  =("qty","sum"),
    ).reset_index()
    if "profit" not in df.columns:
        rev["profit"]=0.0
    txn = (
        baskets[~baskets["is_return"]].groupby("employee")
        .agg(transactions=("sale_id","nunique"), avg_basket=("basket_revenue","mean"))
        .reset_index()
    )
    return rev.merge(txn, on="employee", how="left").sort_values("revenue",ascending=False).reset_index(drop=True)


def sku_velocity(df):
    pos = df[df["qty"]>0].copy()
    s = pos.groupby(["base_id","name","category"]).agg(
        units=("qty","sum"), revenue=("revenue","sum"),
        profit=("profit","sum") if "profit" in pos.columns else ("revenue","count"),
        transactions=("sale_id","nunique"),
    ).reset_index()
    if "profit" not in df.columns:
        s["profit"]=0.0
    s["pct_revenue"] = (s["revenue"]/s["revenue"].sum()*100).round(2)
    s["margin_pct"]  = np.where(s["revenue"]>0,(s["profit"]/s["revenue"]*100).round(1),0.0)
    return s.sort_values("revenue",ascending=False).reset_index(drop=True)


def sales_by_dow(df):
    order=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    s = df[df["qty"]>0].groupby("dow").agg(
        revenue=("revenue","sum"), transactions=("sale_id","nunique"),units=("qty","sum")
    ).reset_index()
    s["dow"]=pd.Categorical(s["dow"],categories=order,ordered=True)
    return s.sort_values("dow").reset_index(drop=True)


def sales_by_hour(df):
    return (
        df[df["qty"]>0].groupby("hour")
        .agg(revenue=("revenue","sum"),transactions=("sale_id","nunique"))
        .reset_index().sort_values("hour")
    )


def top10_customers(df):
    named = df[df["is_named"] & (df["qty"]>0)].copy()
    return (
        named.groupby(["customer_id","customer"])
        .agg(revenue=("revenue","sum"),
             profit=("profit","sum") if "profit" in named.columns else ("revenue","count"),
             orders=("sale_id","nunique"), units=("qty","sum"))
        .reset_index().sort_values("revenue",ascending=False).head(10).reset_index(drop=True)
    )


def retention_frequency(df):
    named = df[df["is_named"] & (df["qty"]>0)].copy()
    freq  = named.groupby("customer_id")["sale_id"].nunique()
    total = len(freq)
    repeat= int((freq>1).sum())
    return {
        "one_time": int((freq==1).sum()),
        "repeat": repeat,
        "total_named": total,
        "repeat_pct": round(repeat/total*100,1) if total else 0,
        "avg_purchases": round(float(freq.mean()),2) if total else 0,
    }