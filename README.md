# Flow ERP — Data-Driven Business Intelligence for Sales Operations

> **Capstone Project · General Assembly Data Science Immersive**
> A self-contained, file-based intelligence platform that transforms raw point-of-sale exports into demand forecasts, financial diagnostics, and customer lifecycle analytics.

---

## Problem Statement

Small and mid-sized retailers generate substantial transactional data but rarely have the infrastructure to act on it. Inventory decisions are made by intuition, customer retention is reactive, and financial visibility is limited to monthly reports. This project addresses three concrete business problems:

1. **Demand uncertainty** — managers over-order safe products and under-order fast movers. A calibrated probabilistic forecast (not just a point estimate) enables smarter replenishment decisions.
2. **Customer attrition** — without a systematic model, at-risk customers are invisible until they stop buying entirely. Early identification enables win-back campaigns before revenue is lost.
3. **Financial opacity** — P&L is often viewed at the business level. Decomposing margin and COGS by branch, category, and employee surfaces the levers that actually drive profitability.

---

## Methodology Overview

The pipeline follows a standard end-to-end data science workflow applied to transactional retail data:

```
Raw POS Export
      │
      ▼
 Data Detection
      │
      ▼
 Preprocessing & Feature Engineering
      │
      ├──► Inventory Engine (Forecasting + Classification)
      ├──► Finance Engine   (Aggregation + Trend Analysis)
      └──► Churn Engine     (Scoring + Risk Classification)
                │
                ▼
         Interactive Dashboard (Streamlit)
```

All three engines operate on the same preprocessed DataFrame. Models re-train fresh on every upload — there is no pre-trained artefact to manage, and predictions are always anchored to the user's own historical data.

---

## Module 1 — Inventory Intelligence

### 1.1 Data Detials
Raw line-item transactions are aggregated to a **product × month** grain (`build_monthly_grain`). This produces the time series used for all downstream modelling. Walk-in and return transactions are excluded from the sales signal.

### 1.2 Feature Engineering
Features are constructed with strict **no-look-ahead discipline**: all lag and rolling computations use `pandas.shift()` so that each row's features contain only information available before that month.

| Feature Group | Features | Rationale |
|---|---|---|
| **Lag features** | `lag1_qty`, `lag2_qty`, `lag3_qty`, `lag1_rev`, `lag1_txns`, `lag1_loyal` | Capture recent demand level and revenue momentum |
| **Rolling statistics** | `roll2_mean`, `roll3_mean`, `roll_std` | Smooth noise; `roll_std` proxies demand volatility |
| **Trend** | `trend_slope` (OLS over trailing 3-month window) | Identifies accelerating or decelerating products |
| **Velocity** | `lag1_qty / (roll2_mean + ε)` | Ratio of recent to rolling average — flags momentum shifts |
| **Category context** | `cat_share`, `cat_qty` | Product's share of category demand; controls for category-level seasonality |
| **Profitability** | `margin_pct` | Encourages the model to differentiate high-value SKUs |
| **Calendar** | `month_num`, `n_weekend_days`, `is_ramadan` | Encodes seasonality and known demand drivers |
| **Product maturity** | `product_age` | Younger products have structurally different demand patterns |

### 1.3 Demand Forecasting — LightGBM Quantile Regression
Rather than producing a single point estimate, the model outputs a **prediction interval** at three quantile levels:

| Model | Quantile | Interpretation |
|---|---|---|
| `m25` | q0.25 | Conservative / low-stock scenario |
| `m50` | q0.50 | Median expected demand (primary recommendation) |
| `m75` | q0.75 | Optimistic / safety-stock scenario |

**Why quantile regression?** Standard regression minimises MSE and predicts the conditional mean. Quantile regression minimises the pinball loss, producing estimates at specific percentiles of the demand distribution. This is more actionable for inventory planning: a buyer can choose to stock to the 75th percentile if they have low stockout tolerance, or the 25th if cash flow is constrained.

**Why LightGBM?** Gradient-boosted trees handle the mixed numeric/categorical feature space, non-linear interactions (e.g. category-share × trend-slope), and sparse product histories without requiring feature normalisation. LightGBM's histogram-based algorithm also trains efficiently on the relatively small product-month datasets typical of SME retailers.

```
Hyperparameters:
  objective       = quantile
  n_estimators    = 500
  learning_rate   = 0.04
  num_leaves      = 31
  max_depth       = 6
  min_child_samples = 5
  subsample       = 0.8        # stochastic gradient boosting
  colsample_bytree = 0.8       # feature subsampling per tree
  reg_alpha / reg_lambda = 0.1 # L1 + L2 regularisation
```

**Fallback:** If the training set has fewer than 30 product-month rows, the model falls back to a 3-period weighted rolling average with ±25% bounds — ensuring the app remains useful for small datasets.

**Weekly disaggregation:** When the user selects "Next Week", the monthly forecast is scaled by `1 / 4.333` (average weeks per calendar month). This is a proportional disaggregation of the monthly model — the underlying model always trains on monthly grain, and the weekly figure inherits its uncertainty bounds.

### 1.4 ABC×XYZ Portfolio Classification
Every product is classified on two independent axes:

**ABC (revenue concentration — Pareto principle):**
- **A** — top 80% of cumulative quantity sold (core products, high investment priority)
- **B** — 80–95% (secondary products, moderate investment)
- **C** — remaining 5% (tail, rule-based or minimal planning)

**XYZ (demand variability — coefficient of variation):**
- **X** — CV ≤ 0.75 (stable, predictable demand)
- **Y** — 0.75 < CV ≤ 1.50 (moderate variability)
- **Z** — CV > 1.50 (highly irregular demand, ML less reliable)

The combined 3×3 matrix (AX through CZ) determines the **planning strategy** applied to each product — from full ML investment (AX, AY) to simple averaging (CX, CY) to minimum-threshold rules (CZ).

### 1.5 Lifecycle Stage Classification — Random Forest
A supervised classifier (`RandomForestClassifier`) assigns each product to a lifecycle stage using rule-derived training labels:

| Stage | Rule (training signal) |
|---|---|
| `dead` | No sales in 60+ days |
| `new` | ≤ 2 months active |
| `trending` | velocity > 1.5 and roll3_mean > 5 |
| `fast_mover` | roll3_mean ≥ 8 |
| `slow_mover` | roll3_mean < 1.5 and days_since_sale > 25 |
| `neutral` | all other products |

The classifier then learns to generalise these rules across the full feature space, capturing interactions that the hard rules miss (e.g. a product that is trending within a high-variance category).

---

## Module 2 — Financial Dashboard

This module applies **aggregation and segmentation analytics** rather than predictive modelling. Key computations:

- **Monthly P&L:** revenue, gross profit, COGS, and margin trend with month-over-month change rates.
- **Branch benchmarking:** revenue and margin decomposed by location to identify under- and over-performing branches.
- **Basket analytics:** average and median basket value trends reveal whether revenue growth is driven by transaction volume or average spend per visit.
- **COGS trend:** tracks cost-of-goods as a percentage of revenue monthly — a rising COGS% indicates margin compression.
- **Day-of-week and hour-of-day patterns:** surface peak trading periods to inform staffing and promotional scheduling.
- **SKU velocity:** products ranked by revenue contribution with Pareto concentration analysis.

---

## Module 3 — Customer Intelligence

### 3.1 Customer Table Construction
Named customer transactions (non-walk-in) are aggregated to one row per customer with the following engineered attributes:

| Feature | Description | Modelling role |
|---|---|---|
| `recency_days` | Days since last purchase | Primary churn signal |
| `frequency` | Number of purchase visits | Loyalty indicator |
| `monetary` | Total lifetime spend | Value weighting |
| `avg_order_value` | Mean basket size | Spend behaviour |
| `avg_interval_days` | Mean days between visits | Baseline purchase rhythm |
| `interval_cv` | Coefficient of variation of inter-purchase gaps | Distinguishes regular vs. sporadic shoppers |
| `spending_trend` | mean(last 3 baskets) − mean(prior baskets) | Detects customers who are spending more or less over time |
| `ltv_proj` | `frequency × avg_order_value` | Simplified LTV proxy |

### 3.2 RFM Segmentation
Each customer receives independent quintile scores (1–5) for Recency (inverted), Frequency, and Monetary. The composite RFM score (3–15) maps to eight named segments: **Champions, Loyal, Potential Loyalists, New Customers, Needs Attention, At Risk, Cannot Lose, Hibernating**.

Quintile scoring with `rank(method="first")` handles ties without creating unequal bins.

### 3.3 Churn Risk Classification — Semi-Supervised LightGBM
The churn model uses a **semi-supervised** approach:

1. **Label generation (rule-based):** Training labels are derived from the ratio of recency to average purchase interval — a transparent business rule that domain experts can audit and adjust. No external labelled dataset is required.

   ```
   Churned  : recency > 3.0 × avg_interval
   At Risk  : recency > 1.5 × avg_interval
   Active   : otherwise
   Fallback (no interval data): 180d → Churned, 90d → At Risk
   ```

2. **Model training (LightGBM):** A `LGBMClassifier` is trained on these labels plus the engineered behavioural features. The model learns non-linear interactions that the rules miss — for example, a high-spending customer with a naturally long purchase cycle (high `avg_interval_days`) should be scored differently from a frequent buyer who has gone silent.

   `class_weight="balanced"` is applied to compensate for the natural skew toward Active customers in healthy businesses.

3. **Fallback:** If the dataset has fewer than 20 named customers or fewer than 2 label classes with ≥ 3 members, the rule-based labels are used directly.

### 3.4 Additional Customer Analytics
- **Customer Retention Rate (CRR):** month-over-month cohort overlap — customers who purchased in both the current and prior month.
- **New vs. Returning revenue split:** tracks the balance between acquisition and retention as revenue drivers.
- **Pareto analysis:** cumulative revenue distribution across the customer base (80/20 rule visualised).
- **Product affinity / market basket analysis:** pairwise co-occurrence counting across multi-item transactions to surface frequently bought-together pairs.

---

## Model Summary

| Module | Algorithm | Task type | Training signal | Fallback |
|---|---|---|---|---|
| Inventory forecasting | `LGBMRegressor` × 3 (q25, q50, q75) | Quantile regression | Supervised (qty_sold) | 3-period weighted avg ± 25% |
| Lifecycle staging | `RandomForestClassifier` | Multi-class classification | Rule-derived labels | Rule labels direct |
| Churn risk | `LGBMClassifier` | 3-class classification | Semi-supervised (interval rules) | Rule labels direct |
| ABC classification | Cumulative-sum Pareto | Deterministic | Revenue/qty rank | N/A |
| XYZ classification | Coefficient of variation | Deterministic | Demand std / mean | N/A |
| RFM segmentation | Quintile scoring | Deterministic | Recency, frequency, monetary | N/A |

---

## Technical Stack

| Layer | Library | Purpose |
|---|---|---|
| Data processing | `pandas`, `numpy` | Aggregation, feature engineering, vectorised transformations |
| Machine learning | `lightgbm` | Quantile regression and churn classification |
| Classical ML | `scikit-learn` | Random Forest classifier, Label Encoder |
| Dashboard | `streamlit` | Interactive UI, file upload, session caching |
| Visualisation | `plotly` | Interactive charts (bar, scatter, heatmap) |

---

## Getting Started

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Launch the app**
```bash
streamlit run app.py
```

**3. Upload and map your data**
The app accepts `.csv`, `.xlsx`, and `.xls` files. Column names are auto-detected via regex pattern matching — confirm the mapping in the sidebar and click **Run Analysis**.

---

## Data Requirements

At minimum, your POS export needs these six fields. Financial and customer modules unlock progressively as optional columns are added.

| Field | Required | Enables |
|---|---|---|
| Product ID | Yes | All modules |
| Product Name | Yes | All modules |
| Category | Yes | All modules |
| Quantity | Yes | All modules (negative qty = return) |
| Date / Time | Yes | All modules |
| Sale / Transaction ID | Yes | Basket-level analytics |
| Subtotal / Revenue | Optional | Financial module, margin |
| Cost (COGS) | Optional | COGS trend, margin analysis |
| Profit | Optional | P&L, margin by product/category |
| Branch | Optional | Branch benchmarking |
| Employee | Optional | Staff performance |
| Customer Name | Optional | RFM, retention, affinity |
| Customer ID | Optional | Churn model (required for cohort tracking) |

---

## Project Structure

```
Flow_f/
├── app.py                  # Entry point: pipeline orchestration, sidebar, tabs
├── requirements.txt
├── core/
│   ├── processor.py        # File ingestion, schema detection, preprocessing
│   ├── inventory_engine.py # Feature engineering, LightGBM forecasting, ABC×XYZ, lifecycle
│   ├── finance_engine.py   # P&L, COGS, basket, branch, SKU aggregations
│   └── churn_engine.py     # Customer table, RFM scoring, churn classifier
├── views/
│   ├── inventory_view.py   # Inventory Intelligence tab
│   ├── financial_view.py   # Financial Dashboard tab
│   └── customer_view.py    # Customer Intelligence tab
└── utils/
    └── styles.py           # Dark theme, Plotly config, shared UI components
```

---

## Key Design Decisions

**Probabilistic forecasting over point estimates.** The quantile regression approach provides a demand range (low / mid / high) rather than a single number. This directly maps to business decisions: stock to the 50th percentile for average efficiency, or the 75th percentile to protect against stockout risk.

**Semi-supervised churn labelling.** Labelled churn datasets rarely exist for SMEs. Generating training labels from business-rule heuristics (purchase-interval ratios) allows the LightGBM model to learn non-linear generalisations of those rules without requiring manual annotation.

**No persistent model artefacts.** Models train from scratch on every upload. This eliminates model staleness, removes the need for versioning infrastructure, and ensures predictions are always anchored to the user's current data distribution.

**Graceful degradation.** Every model has an explicit fallback: rolling average for demand forecasting, rule-based labels for churn. The app remains fully functional even when datasets are too small for reliable ML training.

**Leakage-free feature engineering.** All lag and rolling features are computed via `pandas.shift()` applied per product group. No future information bleeds into training rows.

---

## Limitations

- **Customer module requires named customers.** Walk-in and anonymous transactions are excluded from RFM and churn analysis by design.
- **Minimum data thresholds for ML.** Inventory forecasting requires at least 30 product-month rows; churn classification requires at least 20 named customers with ≥ 2 observable label classes.
- **Monthly model grain.** The forecasting model trains on monthly aggregates. Weekly predictions are proportionally disaggregated, not independently modelled — a weekly-grain dataset could unlock a more accurate weekly model.
- **Single currency.** Financial figures are displayed as-is from the source data.
- **No persistent storage.** All state lives in the Streamlit session. Refreshing the page resets the analysis.

---

## Future Work

- **LL):** Add LLM to give descriptive summaries in Inventory and Customer intelligence.

- **Stockout Analysis:** let user upload stock-on-hand and stockout reports to provide better analysis and predection.
