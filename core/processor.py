import warnings; warnings.filterwarnings("ignore")
import io, re, calendar
from typing import Optional, Dict
import numpy as np
import pandas as pd

DATE_FORMATS = [
    "%d-%m-%Y-%I:%M %p", "%d-%m-%Y-%H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
]

HINT_MAP: Dict[str, list] = {
    "id":          ["^id$","sku","product_id","actual_id","item_id"],
    "name":        ["^name$","product name","item name","description"],
    "variation":   ["variation","variant","varation"],
    "category":    ["category","cat","group","department","section"],
    "qty":         ["^qty$","quantity","units sold"],
    "selling_price":["selling_price","unit_price","price per"],
    "subtotal":    ["subtotal","sub_total","line total"],
    "total":       ["^total$","invoice total"],
    "tax":         ["^tax$"],
    "profit":      ["^profit$","gross profit"],
    "cost":        ["^cost$","cogs","cost of goods"],
    "discount":    ["discount"],
    "sale_id":     ["sale_id","sale id","order_id","invoice_id","transaction_id"],
    "branch":      ["branch","store","location","outlet","shop"],
    "date":        ["^date$","datetime","sold_at","created","timestamp"],
    "employee":    ["employee","staff","salesperson"],
    "customer":    ["^customer$","customer_name","client"],
    "phone":       ["phone","mobile","tel"],
    "customer_id": ["customer_id","cust_id","client_id"],
    "payment":     ["payment","method","tender"],
}


def parse_dates(series):
    for fmt in DATE_FORMATS:
        try:
            p = pd.to_datetime(series, format=fmt, errors="coerce")
            if p.notna().mean() > 0.8:
                return p
        except Exception:
            continue
    return pd.to_datetime(series, infer_datetime_format=True, errors="coerce")


def load_file(buf, filename):
    try:
        if filename.lower().endswith(".csv"):
            return pd.read_csv(buf, low_memory=False)
        elif filename.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(buf)
    except Exception as e:
        raise RuntimeError(f"File read error: {e}")
    raise ValueError(f"Unsupported file type: {filename}")


def smart_detect(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    mapping: Dict[str, Optional[str]] = {}
    for key, hints in HINT_MAP.items():
        found = None
        for h in hints:
            pat = h if h.startswith("^") else f".*{h}.*"
            for k, v in cols_lower.items():
                if re.match(pat, k):
                    found = v
                    break
            if found:
                break
        mapping[key] = found
    return mapping


def is_walkin(val):
    if pd.isna(val):
        return True
    s = str(val).strip().lower()
    return s in ("", "nan", "walk in", "walk-in", "walkin", "unknown", "guest")


def preprocess(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    rename = {v: k for k, v in mapping.items() if v is not None}
    df = df.rename(columns=rename).copy()
    df["date"] = parse_dates(df["date"])
    df = df.dropna(subset=["date"])
    df["qty"] = pd.to_numeric(df.get("qty", 1), errors="coerce").fillna(0)
    if "name" not in df.columns:
        df["name"] = df.get("id", "Unknown").astype(str)
    df["name"] = df["name"].astype(str).str.strip()
    df["base_id"] = (
        df["id"].astype(str).str.split("#").str[0].str.strip()
        if "id" in df.columns else df["name"].str.lower()
    )
    if "category" not in df.columns:
        df["category"] = "Uncategorized"
    df["category"] = df["category"].astype(str).str.strip()
    for col in ["subtotal","total","tax","profit","cost","discount","selling_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["revenue"] = df["subtotal"] if "subtotal" in df.columns else (
        df["selling_price"] * df["qty"] if "selling_price" in df.columns else 0.0
    )
    if "sale_id" in df.columns:
        df["sale_id"] = pd.to_numeric(df["sale_id"], errors="coerce")
    else:
        df["sale_id"] = np.arange(len(df), dtype=float)
    df["customer"] = df["customer"].astype(str).str.strip() if "customer" in df.columns else "Walk in"
    df["customer_id"] = pd.to_numeric(df.get("customer_id", np.nan), errors="coerce")
    df["is_named"] = ~df["customer"].apply(is_walkin)
    if "branch"   not in df.columns: df["branch"]   = "Main"
    if "employee" not in df.columns: df["employee"]  = "Unknown"
    df["week_start"]  = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["month_start"] = df["date"].dt.to_period("M").apply(lambda p: p.start_time)
    df["month_str"]   = df["date"].dt.strftime("%Y-%m")
    df["dow"]         = df["date"].dt.day_name()
    df["hour"]        = df["date"].dt.hour
    df["year"]        = df["date"].dt.year
    df["month"]       = df["date"].dt.month
    df["is_return"]   = df["qty"] < 0
    return df.reset_index(drop=True)


def build_baskets(df: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "basket_revenue": ("revenue",    "sum"),
        "basket_qty":     ("qty",        "sum"),
        "basket_items":   ("base_id",    "count"),
        "date":           ("date",       "first"),
        "month_str":      ("month_str",  "first"),
        "branch":         ("branch",     "first"),
        "employee":       ("employee",   "first"),
        "customer":       ("customer",   "first"),
        "customer_id":    ("customer_id","first"),
        "is_named":       ("is_named",   "first"),
    }
    if "profit" in df.columns:
        agg["basket_profit"] = ("profit","sum")
    if "cost"   in df.columns:
        agg["basket_cost"]   = ("cost",  "sum")
    basket = df.groupby("sale_id").agg(**agg).reset_index()
    if "basket_profit" not in basket.columns:
        basket["basket_profit"] = 0.0
    if "basket_cost"   not in basket.columns:
        basket["basket_cost"]   = 0.0
    basket["is_return"] = basket["basket_qty"] < 0
    return basket