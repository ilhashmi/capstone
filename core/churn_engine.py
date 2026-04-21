
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from itertools import combinations
from collections import Counter
from lightgbm import LGBMClassifier


# Module-level constants ───────────────────────────────────────────────────

# Features fed into the churn classifier
CHURN_FEATURES = [
    "recency_days",       # days since last purchase
    "frequency",          # total number of purchase visits
    "monetary",           # total lifetime spend
    "avg_order_value",    # average basket size
    "ltv_proj",           # projected LTV (frequency × avg_order_value)
    "avg_interval_safe",  # avg days between visits 
    "interval_cv_safe",   # coefficient of variation of purchase intervals (low CV → regular shopper, high CV → sporadic)
    "spending_trend",     # mean(last 3 baskets) − mean(prior baskets)(positive → customer is spending more over time)
]

# Thresholds for the rule-based label generator 
CHURN_MULTIPLIER   = 3.0   # recency > 3× avg interval → Churned
AT_RISK_MULTIPLIER = 1.5   # recency > 1.5× avg interval → At Risk
# Fallback thresholds (days) when avg_interval is unavailable
FALLBACK_CHURNED  = 180
FALLBACK_AT_RISK  =  90


# Helpers ──────────────────────────────────────────────────────────────────

def _named(df):
    return df[df["is_named"] & (df["qty"] > 0)].copy()


# 1. CUSTOMER TABLE ────────────────────────────────────────────────────────

def build_customer_table(df, baskets, snapshot: pd.Timestamp = None):
    if snapshot is None:
        snapshot = pd.Timestamp(df["date"].max()) + pd.Timedelta(days=1)

    named_b = baskets[baskets["is_named"] & ~baskets["is_return"]].copy()
    if named_b.empty:
        return None

    rows = []
    for cid, grp in named_b.groupby("customer_id"):
        grp       = grp.sort_values("date")
        dates     = grp["date"].tolist()
        revenues  = grp["basket_revenue"].values

        # Inter-purchase intervals (positive gaps only)
        intervals = [(b - a).days for a, b in zip(dates[:-1], dates[1:])
                     if (b - a).days > 0]

        avg_interval = float(np.mean(intervals)) if intervals else None
        # CV of intervals: low → predictable shopper, high → sporadic
        interval_cv  = (
            float(np.std(intervals) / np.mean(intervals))
            if intervals and np.mean(intervals) > 0
            else None
        )
        # Spending trend: mean of last-3 baskets vs. mean of prior baskets
        spending_trend = 0.0
        if len(revenues) >= 4:
            spending_trend = float(
                np.mean(revenues[-3:]) - np.mean(revenues[:-3])
            )

        rows.append({
            "customer_id":       float(cid),
            "customer":          grp["customer"].iloc[-1],
            "branch":            grp["branch"].mode().iloc[0] if not grp.empty else "—",
            "first_purchase":    dates[0],
            "last_purchase":     dates[-1],
            "frequency":         len(grp),
            "monetary":          round(revenues.sum(), 2),
            "total_profit":      round(grp["basket_profit"].sum(), 2),
            "avg_order_value":   round(revenues.mean(), 2),
            "recency_days":      (snapshot - pd.Timestamp(dates[-1])).days,
            "avg_interval_days": round(avg_interval, 1) if avg_interval else None,
            "interval_cv":       round(interval_cv, 3)  if interval_cv  else None,
            "spending_trend":    round(spending_trend, 2),
        })

    cust = pd.DataFrame(rows)
    cust["ltv_proj"] = (cust["avg_order_value"] * cust["frequency"]).round(2)
    return cust.sort_values("monetary", ascending=False).reset_index(drop=True)


# 2. RFM SCORING ──────────────────────────────────────────────────────────

def rfm_score(cust):
    df = cust.copy()
    def _qcut5(s, inv: bool = False):
        try:
            labels = [5, 4, 3, 2, 1] if inv else [1, 2, 3, 4, 5]
            return pd.qcut(s.rank(method="first"), 5, labels=labels).astype(int)
        except Exception:
            return pd.Series(3, index=s.index)

    df["r_score"]  = _qcut5(df["recency_days"], inv=True)
    df["f_score"]  = _qcut5(df["frequency"])
    df["m_score"]  = _qcut5(df["monetary"])
    df["rfm_score"] = df["r_score"] + df["f_score"] + df["m_score"]

    def _segment(row) -> str:
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 4 and f >= 4 and m >= 4: return "Champions"
        if r >= 3 and f >= 3:            return "Loyal"
        if r >= 4 and f <= 2:            return "New Customers"
        if r >= 3 and m >= 4:            return "Potential Loyalists"
        if r == 2 and f >= 3:            return "At Risk"
        if r <= 2 and f >= 3:            return "Cannot Lose"
        if r <= 2 and f <= 2:            return "Hibernating"
        return "Needs Attention"

    df["rfm_segment"] = df.apply(_segment, axis=1)
    return df


# 3. CHURN RISK CLASSIFIER ─────────────────────────────────────────────────

def churn_risk(cust):
    df = cust.copy()

    # Step 1: rule-based labels (training signal) ──────────────────────
    def _rule_label(row) -> str:
        d  = row["recency_days"]
        ai = row["avg_interval_days"]
        if ai and not np.isnan(float(ai)) and float(ai) > 0:
            if d > CHURN_MULTIPLIER   * float(ai): return "Churned"
            if d > AT_RISK_MULTIPLIER * float(ai): return "At Risk"
            return "Active"
        # Fallback: absolute-day thresholds
        if d > FALLBACK_CHURNED:  return "Churned"
        if d > FALLBACK_AT_RISK:  return "At Risk"
        return "Active"

    df["_label"] = df.apply(_rule_label, axis=1)

    # Step 2: feature prep ─────────────────────────────────────────────
    df["avg_interval_safe"] = df["avg_interval_days"].fillna(df["recency_days"])
    df["interval_cv_safe"]  = (
        df["interval_cv"].fillna(1.0) if "interval_cv" in df.columns
        else pd.Series(1.0, index=df.index)
    )
    if "spending_trend" not in df.columns:
        df["spending_trend"] = 0.0

    for f in CHURN_FEATURES:
        df[f] = pd.to_numeric(df.get(f, 0), errors="coerce").fillna(0)

    # Step 3: train or fall back ───────────────────────────────────────
    label_counts = df["_label"].value_counts()
    use_model    = (
        len(label_counts) >= 2
        and label_counts.min() >= 3
        and len(df) >= 20
    )
    if use_model:
        clf = LGBMClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            num_leaves=15, min_child_samples=3,
            subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced",   
            verbose=-1, n_jobs=-1,
        )
        clf.fit(df[CHURN_FEATURES], df["_label"])
        df["churn_risk"] = clf.predict(df[CHURN_FEATURES])
    else:
        df["churn_risk"] = df["_label"]

    return df.drop(
        columns=["_label", "avg_interval_safe", "interval_cv_safe"],
        errors="ignore",
    )


# 4. RETENTION RATE ────────────────────────────────────────────────────────

def customer_retention_rate(df):
    named         = _named(df)
    named["month_str"] = named["date"].dt.strftime("%Y-%m")
    months        = sorted(named["month_str"].unique())
    rows = []
    for i in range(1, len(months)):
        prev     = set(named[named["month_str"] == months[i - 1]]["customer_id"].dropna().unique())
        curr     = set(named[named["month_str"] == months[i]]["customer_id"].dropna().unique())
        retained = prev & curr
        crr      = round(len(retained) / len(prev) * 100, 1) if prev else 0.0
        rows.append({
            "month":          months[i],
            "prev_customers": len(prev),
            "curr_customers": len(curr),
            "retained":       len(retained),
            "new_customers":  len(curr - prev),
            "crr_pct":        crr,
        })
    return pd.DataFrame(rows)


# 5. NEW VS RETURNING ──────────────────────────────────────────────────────

def new_vs_returning(df, baskets):
    named_b = baskets[baskets["is_named"] & ~baskets["is_return"]].copy()
    if named_b.empty:
        return pd.DataFrame()
    first_month = (named_b.groupby("customer_id")["month_str"]
                          .min().rename("first_month"))
    named_b = named_b.merge(first_month, on="customer_id", how="left")
    named_b["customer_type"] = named_b.apply(
        lambda r: "New" if r["month_str"] == r["first_month"] else "Returning",
        axis=1,
    )
    result = (
        named_b.groupby(["month_str", "customer_type"])["basket_revenue"]
               .sum().unstack(fill_value=0).reset_index()
    )
    for col in ["New", "Returning"]:
        if col not in result.columns:
            result[col] = 0.0
    result["total"]   = result["New"] + result["Returning"]
    result["new_pct"] = (result["New"] / result["total"].replace(0, np.nan) * 100).round(1)
    return result


# 6. PARETO ────────────────────────────────────────────────────────────────

def pareto_customers(cust):
    df = cust.sort_values("monetary", ascending=False).copy()
    df["cum_revenue"]  = df["monetary"].cumsum()
    df["cum_pct"]      = df["cum_revenue"] / df["monetary"].sum() * 100
    df["customer_pct"] = (np.arange(1, len(df) + 1) / len(df) * 100).round(1)
    return df.reset_index(drop=True)


# 7. PRODUCT AFFINITY ──────────────────────────────────────────────────────

def product_affinity(df, top_n: int = 20):
    multi_sids = (df.groupby("sale_id")["base_id"]
                    .count().loc[lambda x: x > 1].index)
    multi = df[df["sale_id"].isin(multi_sids) & (df["qty"] > 0)].copy()
    pairs = []
    for _, grp in multi.groupby("sale_id"):
        names = list(grp["name"].unique())
        if len(names) >= 2:
            for a, b in combinations(sorted(names), 2):
                if a != b:
                    pairs.append(tuple(sorted([a[:40], b[:40]])))
    if not pairs:
        return pd.DataFrame(columns=["product_a", "product_b", "co_purchases"])
    counter = Counter(pairs)
    return pd.DataFrame([
        {"product_a": a, "product_b": b, "co_purchases": n}
        for (a, b), n in counter.most_common(top_n)
    ])


# 8. EXECUTIVE SUMMARY ─────────────────────────────────────────────────────

def executive_summary(cust_rfm, crr_df,snapshot):
    active_90    = cust_rfm[cust_rfm["recency_days"] <= 90]
    at_risk_pct  = (cust_rfm["churn_risk"] == "At Risk").mean()  * 100
    churned_pct  = (cust_rfm["churn_risk"] == "Churned").mean()  * 100
    avg_ltv      = cust_rfm["ltv_proj"].mean()
    last_crr     = crr_df["crr_pct"].iloc[-1]       if not crr_df.empty else None
    avg_crr      = crr_df["crr_pct"].tail(6).mean() if not crr_df.empty else None
    tl = "red" if at_risk_pct > 30 else ("yellow" if at_risk_pct > 15 else "green")
    return {
        "total_named":         len(cust_rfm),
        "active_90d":          len(active_90),
        "avg_ltv":             round(float(avg_ltv), 2) if not np.isnan(avg_ltv) else 0,
        "churned_pct":         round(float(churned_pct), 1),
        "at_risk_pct":         round(float(at_risk_pct), 1),
        "last_crr":            round(float(last_crr), 1) if last_crr is not None else None,
        "avg_crr_6m":          round(float(avg_crr),  1) if avg_crr  is not None else None,
        "crr_trend":           round(float(last_crr - avg_crr), 1)
                               if (last_crr is not None and avg_crr is not None) else None,
        "churn_traffic_light": tl,
        "revenue_at_risk":     round(float(
            cust_rfm[cust_rfm["churn_risk"].isin(["At Risk", "Churned"])]["monetary"].sum()
        ), 2),
    }
