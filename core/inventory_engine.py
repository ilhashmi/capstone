"""
Pipeline:
  1. build_monthly_grain()   — aggregate to product × month
  2. engineer_features()     — lag/rolling/contextual features
  3. build_abc_xyz()         — ABC by revenue, XYZ by CV
  4. train_quantile_models() — LGBMRegressor q25/q50/q75
  5. predict_next_period()   — roll forward per product
  6. train_classifier()      — lifecycle stage (RandomForest)
  7. build_facts()           — historical summaries
  8. assemble_master()       — master table
  9. build_category_view()   — category-level aggregations
"""
import warnings; warnings.filterwarnings("ignore")
import calendar
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

FEATURE_COLS = [
    "lag1_qty","lag2_qty","lag3_qty",
    "lag1_rev","lag1_txns","lag1_loyal",
    "roll2_mean","roll3_mean","roll_std",
    "trend_slope","velocity","product_age",
    "cat_share","month_num","margin_pct",
    "cat_encoded","cat_qty","n_weekend_days","is_ramadan",
]

CLF_FEATURES = [
    "total_qty","days_since_sale","product_age_days","months_active",
    "roll3_mean","trend_slope","velocity","cat_encoded","cat_share",
    "margin_pct","avg_monthly_qty",
]

XYZ_X_THRESH    = 0.75
XYZ_Z_THRESH    = 1.50
WEEKS_PER_MONTH = 4.333   # average weeks per calendar month

STRATEGY_MAP = {
    "AX":"ML · full investment",   "AY":"ML · full investment",
    "AZ":"ML · monitor closely",   "BX":"ML · moderate investment",
    "BY":"ML · moderate investment","BZ":"Rule-based · watch",
    "CX":"Simple average",         "CY":"Simple average",
    "CZ":"Minimum threshold",
}


# 1. MONTHLY GRAIN ────────────────────────────────────────────────────────

def build_monthly_grain(df: pd.DataFrame):
    pos = df[df["qty"] > 0].copy()
    prod_m = pos.groupby(
        ["base_id","name","category", pd.Grouper(key="date", freq="ME")]
    ).agg(
        qty_sold      =("qty",           "sum"),
        revenue       =("revenue",       "sum"),
        profit        =("profit",        "sum") if "profit" in pos.columns else ("revenue","count"),
        cost          =("cost",          "sum") if "cost"   in pos.columns else ("revenue","count"),
        transactions  =("sale_id",       "nunique"),
        avg_unit_price=("selling_price", "mean") if "selling_price" in pos.columns else ("revenue","count"),
        unique_custs  =("customer_id",   "nunique"),
    ).reset_index().rename(columns={"date":"month"})

    for col, default in [("profit",0.0),("cost",0.0)]:
        if col not in pos.columns:
            prod_m[col] = default
    if prod_m.get("avg_unit_price", pd.Series(dtype=int)).dtype == "int64":
        prod_m["avg_unit_price"] = prod_m["revenue"] / prod_m["qty_sold"].replace(0, np.nan)

    # Category totals
    cat_m = pos.groupby(["category", pd.Grouper(key="date", freq="ME")]).agg(
        cat_qty=("qty","sum"), cat_revenue=("revenue","sum")
    ).reset_index().rename(columns={"date":"month"})
    prod_m = prod_m.merge(cat_m, on=["category","month"], how="left")

    # Loyal customer %
    named = pos[pos["is_named"] & pos["customer_id"].notna()].copy()
    walkin_ids = (named.groupby("customer_id")["customer"].first()
                  .loc[lambda s: s.str.lower().str.contains("walk|unknown|guest", na=False)].index)
    named = named[~named["customer_id"].isin(walkin_ids)]
    named_m = named.groupby(["base_id", pd.Grouper(key="date", freq="ME")]).agg(
        named_qty=("qty","sum")
    ).reset_index().rename(columns={"date":"month"})
    prod_m = prod_m.merge(named_m, on=["base_id","month"], how="left")
    prod_m["named_qty"] = prod_m["named_qty"].fillna(0)
    prod_m["loyal_pct"] = (prod_m["named_qty"] / prod_m["qty_sold"].replace(0,np.nan) * 100).fillna(0).clip(0,100)

    # Calendar features
    def _weekends(d):
        cal = calendar.monthcalendar(d.year, d.month)
        return sum(1 for w in cal if w[4]!=0) + sum(1 for w in cal if w[5]!=0)

    prod_m["n_weekend_days"] = prod_m["month"].apply(_weekends)
    prod_m["is_ramadan"]     = ((prod_m["month"].dt.month==3) & (prod_m["month"].dt.year==2026)).astype(int)
    prod_m["month_num"]      = prod_m["month"].dt.month

    le = LabelEncoder()
    prod_m["cat_encoded"] = le.fit_transform(prod_m["category"])
    return prod_m.sort_values(["base_id","month"]).reset_index(drop=True), le


# 2. FEATURE ENGINEERING ──────────────────────────────────────────────────

def engineer_features(monthly: pd.DataFrame) -> pd.DataFrame:
    def _features_for_product(grp: pd.DataFrame) -> pd.DataFrame:
        grp  = grp.sort_values("month").reset_index(drop=True)
        qty  = grp["qty_sold"]
        lagged = qty.shift(1)                       

        # Lag features 
        grp["lag1_qty"]   = lagged
        grp["lag2_qty"]   = qty.shift(2)
        grp["lag3_qty"]   = qty.shift(3)
        grp["lag1_rev"]   = grp["revenue"].shift(1)
        grp["lag1_txns"]  = grp["transactions"].shift(1)
        grp["lag1_loyal"] = grp["loyal_pct"].shift(1)

        #  Rolling statistics 
        grp["roll2_mean"] = lagged.rolling(2, min_periods=1).mean()
        grp["roll3_mean"] = lagged.rolling(3, min_periods=1).mean()
        grp["roll_std"]   = lagged.rolling(3, min_periods=2).std().fillna(0.0)

        #  trend slope  
        slopes = np.zeros(len(grp))
        for i in range(2, len(grp)):
            window = qty.iloc[max(0, i - 3):i].values
            if len(window) >= 2:
                try:
                    slopes[i] = np.polyfit(np.arange(len(window)), window, 1)[0]
                except Exception:
                    pass
        grp["trend_slope"] = slopes

        # ratios 
        grp["velocity"]    = (lagged / (grp["roll2_mean"] + 0.1)).fillna(1.0)
        grp["product_age"] = np.arange(len(grp))
        grp["cat_share"]   = (
            lagged / grp["cat_qty"].replace(0, np.nan) * 100
        ).fillna(0.0)
        grp["margin_pct"]  = (
            grp["profit"] / grp["revenue"].replace(0, np.nan) * 100
        ).fillna(0.0)
        return grp

    featured = (
        monthly.groupby("base_id", group_keys=False)
               .apply(_features_for_product)
               .reset_index(drop=True)
    )
    for f in FEATURE_COLS:
        if f not in featured.columns:
            featured[f] = 0.0
    return featured


# 3. ABC × XYZ

def build_abc_xyz(monthly: pd.DataFrame, df_pos: pd.DataFrame) -> pd.DataFrame:
    tot = (monthly.groupby("base_id")["qty_sold"].sum()
           .reset_index(name="total_qty").sort_values("total_qty", ascending=False))
    tot["cum_pct"] = tot["total_qty"].cumsum() / tot["total_qty"].sum() * 100
    tot["abc"] = "C"
    tot.loc[tot["cum_pct"]<=80, "abc"] = "A"
    tot.loc[(tot["cum_pct"]>80)&(tot["cum_pct"]<=95), "abc"] = "B"

    xyz = monthly.groupby("base_id").agg(
        mean_qty=("qty_sold","mean"), std_qty=("qty_sold","std"), months=("qty_sold","count")
    ).reset_index()
    xyz["cv"] = (xyz["std_qty"].fillna(0) / xyz["mean_qty"].replace(0,np.nan)).fillna(0)
    xyz["xyz"] = "Y"
    xyz.loc[xyz["cv"]<=XYZ_X_THRESH, "xyz"] = "X"
    xyz.loc[xyz["cv"]>XYZ_Z_THRESH,  "xyz"] = "Z"

    snapshot   = pd.Timestamp(df_pos["date"].max()) + pd.Timedelta(days=1)
    last_sale  = df_pos[df_pos["qty"]>0].groupby("base_id")["date"].max().rename("last_sale_date")
    first_sale = df_pos[df_pos["qty"]>0].groupby("base_id")["date"].min().rename("first_sale_date")
    months_act = df_pos.groupby("base_id")["date"].apply(lambda x: x.dt.to_period("M").nunique()).rename("months_active")
    avg_price  = (df_pos.groupby("base_id")["selling_price"].median().rename("avg_unit_price")
                  if "selling_price" in df_pos.columns
                  else (df_pos.groupby("base_id")["revenue"].sum() / df_pos.groupby("base_id")["qty"].sum()).rename("avg_unit_price"))

    meta = (tot.merge(xyz[["base_id","cv","xyz","mean_qty","std_qty","months"]], on="base_id", how="left")
               .merge(last_sale.reset_index(),  on="base_id", how="left")
               .merge(first_sale.reset_index(), on="base_id", how="left")
               .merge(months_act.reset_index(), on="base_id", how="left")
               .merge(avg_price.reset_index(),  on="base_id", how="left"))

    meta["days_since_sale"]  = (snapshot - pd.to_datetime(meta["last_sale_date"])).dt.days
    meta["product_age_days"] = (pd.to_datetime(meta["last_sale_date"]) - pd.to_datetime(meta["first_sale_date"])).dt.days.fillna(0)
    meta["avg_monthly_qty"]  = meta["total_qty"] / meta["months_active"].replace(0,1)
    meta["abcxyz"]   = meta["abc"] + meta["xyz"]
    meta["strategy"] = meta["abcxyz"].map(STRATEGY_MAP).fillna("Simple average")
    name_cat = monthly.groupby("base_id").agg(name=("name","first"), category=("category","first")).reset_index()
    return meta.merge(name_cat, on="base_id", how="left").fillna(0)


# 4. TRAIN MODELS ─────────────────────────────────────────────────────────

def train_quantile_models(featured: pd.DataFrame):
    train = featured.dropna(subset=["lag1_qty"]).copy()
    for f in FEATURE_COLS:
        train[f] = pd.to_numeric(train.get(f, 0), errors="coerce").fillna(0)
    X = train[FEATURE_COLS]
    y = train["qty_sold"].clip(lower=0)
    if len(train) < 30:
        return None, None, None, pd.DataFrame()

    def _lgbm(q):
        return LGBMRegressor(
            objective="quantile", alpha=q, n_estimators=500,
            learning_rate=0.04, num_leaves=31, max_depth=6,
            min_child_samples=5, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=0.1, verbose=-1, n_jobs=-1,
        )

    m25, m50, m75 = _lgbm(0.25), _lgbm(0.50), _lgbm(0.75)
    m25.fit(X, y); m50.fit(X, y); m75.fit(X, y)
    feat_imp = pd.DataFrame({"feature": FEATURE_COLS, "importance": m50.feature_importances_}).sort_values("importance", ascending=False)
    return m25, m50, m75, feat_imp


# 5. PREDICT ──────────────────────────────────────────────────────────────

def predict_next_period(
    featured:         pd.DataFrame,
    m25, m50, m75,
    next_week:        bool = False,
    target_month_num: int  = None,
    n_weekend_days:   int  = 9,
    is_ramadan:       int  = 0,
) -> pd.DataFrame:
    if target_month_num is None:
        target_month_num = (featured["month"].max() + pd.DateOffset(months=1)).month

    latest = featured.groupby("base_id").last().reset_index()
    latest["lag3_qty"]        = latest.get("lag2_qty",  latest["qty_sold"]).fillna(0)
    latest["lag2_qty"]        = latest.get("lag1_qty",  latest["qty_sold"]).fillna(0)
    latest["lag1_qty"]        = latest["qty_sold"]
    latest["roll2_mean"]      = (latest["qty_sold"] + latest["lag2_qty"]) / 2
    latest["roll3_mean"]      = (latest["qty_sold"] + latest["lag2_qty"] + latest["lag3_qty"]) / 3
    latest["velocity"]        = latest["lag1_qty"] / (latest["roll2_mean"] + 0.1)
    latest["month_num"]       = target_month_num
    latest["n_weekend_days"]  = n_weekend_days
    latest["is_ramadan"]      = is_ramadan

    for f in FEATURE_COLS:
        latest[f] = pd.to_numeric(latest.get(f, 0), errors="coerce").fillna(0)
    Xp = latest[FEATURE_COLS]

    if m50 is not None:
        p25 = np.clip(m25.predict(Xp), 0, None)
        p50 = np.clip(m50.predict(Xp), 0, None)
        p75 = np.clip(m75.predict(Xp), 0, None)
    else:
        p50 = np.clip(latest["roll3_mean"].fillna(latest["qty_sold"]).values, 0, None)
        p25, p75 = p50 * 0.75, p50 * 1.25

    # Scale to weekly
    if next_week:
        p25 = p25 / WEEKS_PER_MONTH
        p50 = p50 / WEEKS_PER_MONTH
        p75 = p75 / WEEKS_PER_MONTH

    prices = (
        latest.set_index("base_id")["avg_unit_price"]
              .reindex(latest["base_id"].values).fillna(0).values
    )
    results = pd.DataFrame({
        "base_id":          latest["base_id"].values,
        "pred_qty_low":     np.round(p25, 1),
        "pred_qty_mid":     np.round(p50, 1),
        "pred_qty_high":    np.round(p75, 1),
        "model_used":       "LightGBM" if m50 is not None else "Simple avg",
        "pred_revenue_mid": np.round(p50 * prices, 2),
    })
    return results


# 6. LIFECYCLE CLASSIFIER ─────────────────────────────────────────────────

def train_classifier(featured: pd.DataFrame, meta: pd.DataFrame):
    last_feat = featured.groupby("base_id").last()[
        ["roll3_mean","trend_slope","velocity","cat_share","margin_pct","cat_encoded"]
    ].reset_index()
    prod = meta.merge(last_feat, on="base_id", how="left").fillna(0)

    def _stage(row):
        if row["days_since_sale"] > 60:   return "dead"
        if row["months_active"] <= 2:     return "new"
        if row["velocity"] > 1.5 and row["roll3_mean"] > 5: return "trending"
        if row["roll3_mean"] >= 8:        return "fast_mover"
        if row["roll3_mean"] < 1.5 and row["days_since_sale"] > 25: return "slow_mover"
        return "neutral"

    prod["stage_label"] = prod.apply(_stage, axis=1)
    for f in CLF_FEATURES:
        if f not in prod.columns:
            prod[f] = 0.0
        prod[f] = pd.to_numeric(prod[f], errors="coerce").fillna(0)

    clf = RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=3, random_state=42)
    clf.fit(prod[CLF_FEATURES], prod["stage_label"])
    return clf, prod[["base_id","stage_label"]]


def predict_stages(clf, meta: pd.DataFrame, featured: pd.DataFrame) -> pd.Series:
    last_feat = featured.groupby("base_id").last()[
        ["roll3_mean","trend_slope","velocity","cat_share","margin_pct","cat_encoded"]
    ].reset_index()
    prod = meta.merge(last_feat, on="base_id", how="left").fillna(0)
    for f in CLF_FEATURES:
        if f not in prod.columns:
            prod[f] = 0.0
        prod[f] = pd.to_numeric(prod[f], errors="coerce").fillna(0)
    return pd.Series(clf.predict(prod[CLF_FEATURES]), index=prod["base_id"].values, name="stage")


# 7. HISTORICAL FACTS ─────────────────────────────────────────────────────

def build_facts(monthly: pd.DataFrame, df_pos: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly.copy()
    monthly["month"] = pd.to_datetime(monthly["month"])
    last_m  = monthly["month"].max()
    m3_cut  = last_m - pd.DateOffset(months=2)
    last_sale = df_pos[df_pos["qty"]>0].groupby("base_id")["date"].max().rename("last_sale_date")

    rows = []
    for pid, grp in monthly.groupby("base_id"):
        g = grp.sort_values("month")
        vals    = g["qty_sold"].values
        n       = len(vals)
        wts     = np.arange(1, n+1)
        rev_tot = g["revenue"].sum()
        pft_tot = g["profit"].sum()
        rows.append({
            "base_id":        pid,
            "last_month_qty": int(g[g["month"]==last_m]["qty_sold"].sum()),
            "last_3m_qty":    int(g[g["month"]>=m3_cut]["qty_sold"].sum()),
            "last_6m_qty":    int(vals.sum()),
            "true_avg_6m":    round(vals.sum()/6, 1),
            "wtd_avg_6m":     round(float(np.dot(vals,wts)/wts.sum()), 1) if n>0 else 0.0,
            "avg_unit_price": round(float(g["avg_unit_price"].mean()), 2),
            "margin_pct":     round(float(pft_tot/rev_tot*100), 1) if rev_tot>0 else 0.0,
            "total_revenue":  round(float(rev_tot), 2),
            "total_profit":   round(float(pft_tot), 2),
        })
    facts = pd.DataFrame(rows).merge(last_sale.reset_index(), on="base_id", how="left")
    facts["last_sale_date"] = pd.to_datetime(facts["last_sale_date"]).dt.strftime("%d %b %Y")
    return facts


# 8. MASTER TABLE ──────────────────────────────────────────────────────────

def assemble_master(predictions, meta, facts, stages, monthly) -> pd.DataFrame:
    name_cat = monthly.groupby("base_id").agg(name=("name","first"), category=("category","first")).reset_index()
    master = (
        predictions
        .merge(name_cat, on="base_id", how="left")
        .merge(meta[["base_id","abc","xyz","abcxyz","strategy","cv","days_since_sale","months_active","avg_unit_price"]],
               on="base_id", how="left")
        .merge(facts.drop(columns=["avg_unit_price"], errors="ignore"), on="base_id", how="left")
        .merge(stages.reset_index().rename(columns={0:"stage","index":"base_id"}), on="base_id", how="left")
    )
    master["stage"] = master["stage"].fillna("neutral")
    abc_ord = {"A":0,"B":1,"C":2}
    master["_s"] = master["abc"].map(abc_ord).fillna(3)
    master = master.sort_values(["_s","pred_qty_mid"], ascending=[True,False]).drop(columns="_s").reset_index(drop=True)
    for c in ["pred_qty_low","pred_qty_mid","pred_qty_high"]:
        if c in master.columns:
            master[c] = pd.to_numeric(master[c], errors="coerce").round(1).fillna(0)
    for c in ["cv","days_since_sale","margin_pct","true_avg_6m","wtd_avg_6m"]:
        if c in master.columns:
            master[c] = pd.to_numeric(master[c], errors="coerce").round(2).fillna(0)
    return master


# 9. CATEGORY VIEW ─────────────────────────────────────────────────────────

def build_category_view(monthly: pd.DataFrame) -> pd.DataFrame:
    cat = monthly.groupby(["category","month"]).agg(
        qty_sold    =("qty_sold",    "sum"),
        revenue     =("revenue",     "sum"),
        profit      =("profit",      "sum"),
        transactions=("transactions","sum"),
        sku_count   =("base_id",     "nunique"),
    ).reset_index()
    cat["month_str"] = pd.to_datetime(cat["month"]).dt.strftime("%Y-%m")
    cat["margin_pct"]= (cat["profit"] / cat["revenue"].replace(0,np.nan) * 100).round(1).fillna(0)
    cat["mom_qty"]   = cat.groupby("category")["qty_sold"].pct_change() * 100
    return cat.sort_values(["category","month"]).reset_index(drop=True)
