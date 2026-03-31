# app.py
import numpy as np
import pandas as pd
import streamlit as st
from hijri_converter import Gregorian
from sklearn.ensemble import HistGradientBoostingRegressor

# ----------------------------
# PAGE SETUP
# ----------------------------
st.set_page_config(page_title="Demand Forecast & Restock", layout="wide")
st.title("Demand Forecast & Restock Report")

# ----------------------------
# HELPERS
# ----------------------------
@st.cache_data(show_spinner=False)
def read_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)

def safe_to_datetime(df: pd.DataFrame, col: str) -> pd.Series:
    # matches your original: '%d-%m-%Y-%I:%M %p'
    return pd.to_datetime(df[col], format="%d-%m-%Y-%I:%M %p", errors="coerce")

def get_hijri_features(date: pd.Timestamp):
    h = Gregorian(date.year, date.month, date.day).to_hijri()
    is_ramadan = 1 if h.month == 9 else 0
    is_eid = 1 if (h.month == 10 and h.day <= 3) or (h.month == 12 and h.day >= 10) else 0
    return h.month, is_ramadan, is_eid

def build_monthly_data(sales_df: pd.DataFrame) -> pd.DataFrame:
    sales_df = sales_df.copy()

    sales_df["date_time"] = safe_to_datetime(sales_df, "date_time")
    sales_df = sales_df.dropna(subset=["date_time"])

    sales_df["year_month"] = sales_df["date_time"].dt.to_period("M")

    monthly = (
        sales_df.groupby(["year_month", "product_id", "branch", "category"], as_index=False)
        .agg(
            qty_purchased=("qty_purchased", "sum"),
            subtotal=("subtotal", "mean"),
            profit=("profit", "sum"),
            cogs=("cogs", "mean"),
        )
    )

    monthly["date"] = monthly["year_month"].dt.to_timestamp()
    monthly = monthly.sort_values(["product_id", "branch", "date"])

    hijri = monthly["date"].apply(lambda x: pd.Series(get_hijri_features(x)))
    monthly[["hijri_month", "is_ramadan", "is_eid"]] = hijri

    monthly["lag_1"] = monthly.groupby(["product_id", "branch"])["qty_purchased"].shift(1)
    monthly["lag_12"] = monthly.groupby(["product_id", "branch"])["qty_purchased"].shift(12)
    monthly["rolling_mean_3"] = (
        monthly.groupby(["product_id", "branch"])["qty_purchased"]
        .shift(1)
        .rolling(window=3)
        .mean()
    )

    return monthly

@st.cache_resource(show_spinner=False)
def train_model(train_df: pd.DataFrame, features: list[str], max_iter: int, random_state: int):
    model = HistGradientBoostingRegressor(max_iter=max_iter, random_state=random_state)
    X = train_df[features]
    y = train_df["qty_purchased"]
    model.fit(X, y)
    return model

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# Toggle-driven: hide product name + category columns from viewing (not downloads)
SENSITIVE_COLS = {
    "product_name", "Product Name", "product category", "Product Category",
    "category", "Category", "cogs", "Cogs", "cost", "Cost", "profit", "Profit","subtotal"
}

def apply_privacy_view(df: pd.DataFrame, hide: bool) -> pd.DataFrame:
    if not hide:
        return df
    cols_to_drop = [c for c in df.columns if c in SENSITIVE_COLS]
    return df.drop(columns=cols_to_drop, errors="ignore")

# ----------------------------
# SIDEBAR
# ----------------------------
with st.sidebar:
    st.header("Inputs")
    sales_file = st.file_uploader("Upload sales_cleaned_adliya.csv", type=["csv"])
    inv_file = st.file_uploader("Upload inventory_cleaned.csv", type=["csv"])

    st.divider()
    st.header("Forecast Settings")
    forecast_month = st.text_input("Forecast month (YYYY-MM)", value="2026-02")
    latest_month = st.text_input("Latest actual month (YYYY-MM)", value="2026-01")

    st.divider()
    st.header("Model Settings")
    max_iter = st.slider("HistGB max_iter", min_value=50, max_value=500, value=200, step=25)
    random_state = st.number_input("random_state", value=42, step=1)

    st.divider()
    st.header("Inventory Policy")
    safety_buffer = st.number_input("Safety buffer (units)", min_value=0, value=4, step=1)

    st.divider()
    st.header("Privacy")
    hide_sensitive = st.toggle("Hide product name/category", value=True)

# ----------------------------
# MAIN
# ----------------------------
if not sales_file or not inv_file:
    st.info("Upload both CSV files from the sidebar to generate the restock report.")
    st.stop()

sales_df = read_csv(sales_file)
inv_df = read_csv(inv_file)

required_sales_cols = {"date_time", "product_id", "branch", "category", "qty_purchased", "subtotal", "profit", "cogs"}
required_inv_cols = {"product_id", "stock_on_hand"}

missing_sales = required_sales_cols - set(sales_df.columns)
missing_inv = required_inv_cols - set(inv_df.columns)

if missing_sales:
    st.error(f"Sales file missing columns: {sorted(list(missing_sales))}")
    st.stop()
if missing_inv:
    st.error(f"Inventory file missing columns: {sorted(list(missing_inv))}")
    st.stop()

with st.spinner("Building monthly dataset + features..."):
    monthly_data = build_monthly_data(sales_df)

train_df = monthly_data.dropna().copy()

features = [
    "subtotal",
    "cogs",
    "hijri_month",
    "is_ramadan",
    "is_eid",
    "lag_1",
    "lag_12",
    "rolling_mean_3",
]

missing_feat = [c for c in features if c not in train_df.columns]
if missing_feat:
    st.error(f"Feature columns missing after processing: {missing_feat}")
    st.stop()

with st.spinner("Training model..."):
    model = train_model(train_df, features, max_iter=int(max_iter), random_state=int(random_state))

train_r2 = model.score(train_df[features], train_df["qty_purchased"])

try:
    latest_period = pd.Period(latest_month, freq="M")
    forecast_period = pd.Period(forecast_month, freq="M")
    forecast_date = forecast_period.to_timestamp()
except Exception:
    st.error("Invalid month format. Use YYYY-MM (example: 2026-02).")
    st.stop()

latest_state = monthly_data[monthly_data["year_month"] == latest_period].copy()
if latest_state.empty:
    st.error(f"No rows found for latest actual month = {latest_month}.")
    st.stop()

h_m, is_r, is_e = get_hijri_features(forecast_date)

forecast_input = latest_state.copy()
forecast_input["hijri_month"] = h_m
forecast_input["is_ramadan"] = is_r
forecast_input["is_eid"] = is_e

# Use actuals from latest month as lag_1 for the forecast month
forecast_input["lag_1"] = latest_state["qty_purchased"]

# Predict demand
forecast_input["predicted_demand"] = model.predict(forecast_input[features])

total_forecast = (
    forecast_input.groupby("product_id", as_index=False)["predicted_demand"].sum()
    .rename(columns={"predicted_demand": "predicted_demand_feb"})
)

report = (
    pd.merge(inv_df.copy(), total_forecast, on="product_id", how="left")
    .fillna({"predicted_demand_feb": 0})
)

report["stock_needed"] = report["predicted_demand_feb"] + float(safety_buffer)
report["restock_qty"] = np.maximum(0, report["stock_needed"] - report["stock_on_hand"])

report["status"] = np.where(
    report["stock_on_hand"] < report["predicted_demand_feb"],
    "STOCKOUT RISK",
    np.where(report["restock_qty"] > 0, "LOW STOCK", "HEALTHY"),
)

# ----------------------------
# UI: KPIs
# ----------------------------
k1, k2 = st.columns(2)
k1.metric("Products in report", f"{report['product_id'].nunique():,}")
k2.metric("Total restock qty", f"{report['restock_qty'].sum():,.0f}")

st.divider()

# ----------------------------
# UI: FILTERS
# ----------------------------
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    status_filter = st.multiselect(
        "Filter status",
        options=["STOCKOUT RISK", "LOW STOCK", "HEALTHY"],
        default=["STOCKOUT RISK", "LOW STOCK"],
    )
with c2:
    min_restock = st.number_input("Min restock qty", min_value=0, value=0, step=1)
with c3:
    search = st.text_input("Search product_id (contains)", value="")

filtered = report.copy()
if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]
filtered = filtered[filtered["restock_qty"] >= float(min_restock)]
if search.strip():
    filtered = filtered[filtered["product_id"].astype(str).str.contains(search.strip(), na=False)]

status_order = {"STOCKOUT RISK": 0, "LOW STOCK": 1, "HEALTHY": 2}
filtered["_status_rank"] = filtered["status"].map(status_order).fillna(99)
filtered = (
    filtered.sort_values(["_status_rank", "restock_qty"], ascending=[True, False])
    .drop(columns=["_status_rank"])
)

# ----------------------------
# UI: TABS
# ----------------------------
tab1, tab2, tab3 = st.tabs(["Restock Report", "Top Risks", "Data Preview"])

with tab1:
    st.subheader("Restock Report")
    view_df = apply_privacy_view(filtered, hide_sensitive)
    st.dataframe(view_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download CSV (filtered)",
        data=to_csv_bytes(filtered),  # full data
        file_name=f"Restock_Proposal_{forecast_month}.csv",
        mime="text/csv",
    )

with tab2:
    st.subheader("Top STOCKOUT RISK")
    top_risk = (
        report[report["status"] == "STOCKOUT RISK"]
        .sort_values("restock_qty", ascending=False)
        .head(50)
    )
    view_risk = apply_privacy_view(top_risk, hide_sensitive)
    st.dataframe(view_risk, use_container_width=True, hide_index=True)

    st.download_button(
        "Download CSV (top risk)",
        data=to_csv_bytes(top_risk),  # full data
        file_name=f"Top_Stockout_Risk_{forecast_month}.csv",
        mime="text/csv",
    )

with tab3:
    st.subheader("Monthly Data (feature engineered) — sample")
    view_monthly = apply_privacy_view(monthly_data.tail(200), hide_sensitive)
    st.dataframe(view_monthly, use_container_width=True, hide_index=True)
