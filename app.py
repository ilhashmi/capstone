import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.express as px
from sklearn.ensemble import HistGradientBoostingRegressor
from thefuzz import process

st.set_page_config(page_title="Inventory Intelligence", layout="wide")

def auto_map_columns(df_columns, required_fields):
    mapping = {}
    for req in required_fields:
        match, score = process.extractOne(req, df_columns)
        mapping[req] = match if score > 75 else None
    return mapping

def croston_forecast(ts, periods=1):
    d = np.array(ts)
    if len(d) == 0: return [0] * periods
    non_zero_idx = np.where(d > 0)[0]
    if len(non_zero_idx) == 0: return [0] * periods
    
    demand = d[non_zero_idx]
    intervals = np.diff(np.insert(non_zero_idx, 0, -1))
    
    alpha = 0.1
    z, p = np.zeros(len(demand)), np.zeros(len(intervals))
    z[0], p[0] = demand[0], intervals[0]
    
    for i in range(1, len(demand)):
        z[i] = alpha * demand[i] + (1 - alpha) * z[i-1]
        p[i] = alpha * intervals[i] + (1 - alpha) * p[i-1]
        
    forecast = z[-1] / p[-1] if p[-1] > 0 else 0
    return [max(0, forecast)] * periods

def ml_forecast(df_product, target_col='qty', periods=4):
    if len(df_product) < 10:
        return [df_product[target_col].mean()] * periods
        
    df_product = df_product.copy()
    df_product['lag_1'] = df_product[target_col].shift(1)
    df_product['lag_2'] = df_product[target_col].shift(2)
    df_product['lag_3'] = df_product[target_col].shift(3)
    df_product['rolling_mean_3'] = df_product[target_col].rolling(3).mean()
    
    train = df_product.dropna()
    if len(train) < 5:
        return croston_forecast(df_product[target_col].fillna(0), periods)
        
    X = train[['lag_1', 'lag_2', 'lag_3', 'rolling_mean_3']]
    y = train[target_col]
    
    model = HistGradientBoostingRegressor(max_iter=50, min_samples_leaf=1)
    model.fit(X, y)
    
    forecasts = []
    current_data = train.iloc[-1].copy()
    
    for _ in range(periods):
        x_pred = pd.DataFrame({
            'lag_1': [current_data[target_col] if _ == 0 else forecasts[-1]],
            'lag_2': [current_data['lag_1']],
            'lag_3': [current_data['lag_2']],
            'rolling_mean_3': [(current_data['lag_1'] + current_data['lag_2'] + (forecasts[-1] if _ > 0 else current_data[target_col]))/3]
        })
        
        pred = model.predict(x_pred)[0]
        forecasts.append(max(0, pred))
        
        current_data['lag_2'] = current_data['lag_1']
        current_data['lag_1'] = forecasts[-1]
        
    return forecasts

def build_intelligence_matrix(df, lead_time_weeks):
    facts = df.groupby('name').agg(
        total_qty=('qty', 'sum'),
        total_revenue=('subtotal', 'sum') if 'subtotal' in df.columns else ('qty', 'sum'),
        total_profit=('profit', 'sum') if 'profit' in df.columns else ('qty', 'sum'),
        last_sold=('date', 'max'),
        first_sold=('date', 'min')
    ).reset_index()
    
    max_date = df['date'].max()
    facts['days_since_sold'] = (max_date - facts['last_sold']).dt.days
    facts['lifespan_days'] = (facts['last_sold'] - facts['first_sold']).dt.days + 1
    
    facts = facts.sort_values('total_profit', ascending=False)
    facts['cum_pct'] = facts['total_profit'].cumsum() / facts['total_profit'].sum()
    facts['abc_class'] = np.where(facts['cum_pct'] <= 0.8, 'A',
                         np.where(facts['cum_pct'] <= 0.95, 'B', 'C'))
    
    df_weekly = df.set_index('date').groupby(['name', pd.Grouper(freq='W')])['qty'].sum().reset_index()
    
    results = []
    for product in facts['name'].unique():
        prod_data = df_weekly[df_weekly['name'] == product].sort_values('date')
        
        all_weeks = pd.date_range(start=df_weekly['date'].min(), end=df_weekly['date'].max(), freq='W')
        prod_data = prod_data.set_index('date').reindex(all_weeks, fill_value=0).reset_index()
        prod_data = prod_data.rename(columns={'index': 'date', 'qty': 'qty'})
        prod_data['name'] = product
        
        mean_qty = prod_data['qty'].mean()
        std_qty = prod_data['qty'].std()
        cv = (std_qty / mean_qty) if mean_qty > 0 else 1
        xyz = 'X' if cv <= 0.5 else ('Y' if cv <= 1.0 else 'Z')
        
        sparsity = (prod_data['qty'] == 0).mean()
        
        forecast_horizon = max(1, int(lead_time_weeks))
        
        if sparsity > 0.4 or xyz == 'Z':
            fcst = croston_forecast(prod_data['qty'], periods=forecast_horizon)
            model_used = 'Croston (Intermittent)'
        else:
            fcst = ml_forecast(prod_data, target_col='qty', periods=forecast_horizon)
            model_used = 'HistGradientBoost'
            
        total_lead_demand = sum(fcst)
        
        results.append({
            'name': product,
            'xyz_class': xyz,
            'cv_score': cv,
            'sparsity_pct': sparsity,
            'model_used': model_used,
            f'lead_demand_({forecast_horizon}w)': round(total_lead_demand, 2)
        })
        
    forecast_df = pd.DataFrame(results)
    final_df = pd.merge(facts, forecast_df, on='name')
    
    final_df['segment'] = final_df['abc_class'] + final_df['xyz_class']
    
    def generate_action(row):
        if row['days_since_sold'] > 90:
            return "Liquidate (Dead Stock)"
        if row['segment'] in ['AX', 'AY', 'BX']:
            return "Restock Aggressively"
        if row['segment'] in ['AZ', 'BZ', 'CX', 'CY']:
            return "Maintain Level"
        return "Review / Reduce"
        
    final_df['suggested_action'] = final_df.apply(generate_action, axis=1)
    
    return final_df

st.title("📈 Enterprise Inventory Intelligence Engine")
st.markdown("Optimize capital allocation, forecast demand using Hybrid ML, and identify actionable inventory risks.")

uploaded_file = st.file_uploader("1. Upload Raw Sales Data (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    with st.spinner("Ingesting data..."):
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
    st.success(f"Data ingested: {len(df_raw):,} rows, {df_raw.shape[1]} columns.")
    
    st.subheader("2. Business Configuration")
    col1, col2 = st.columns(2)
    with col1:
        lead_time_days = st.number_input("Supplier Lead Time (Days)", min_value=1, value=14, help="How long does it take for stock to arrive after ordering?")
    with col2:
        agg_level = st.selectbox("Forecast Aggregation", ["Weekly (Recommended)", "Monthly"])
    
    lead_time_weeks = max(1, lead_time_days / 7)
    
    st.subheader("3. Data Mapping")
    st.markdown("We attempted to auto-detect your columns. Please verify before processing.")
    
    required_cols = ['name', 'category', 'qty', 'date']
    optional_cols = ['subtotal', 'cost', 'profit']
    all_target_cols = required_cols + optional_cols
    
    raw_cols = df_raw.columns.tolist()
    auto_maps = auto_map_columns(raw_cols, all_target_cols)
    
    mapping_results = {}
    m_cols = st.columns(4)
    
    for i, target in enumerate(all_target_cols):
        with m_cols[i % 4]:
            is_req = "*" if target in required_cols else ""
            default_val = raw_cols.index(auto_maps[target]) if auto_maps.get(target) in raw_cols else 0
            mapping_results[target] = st.selectbox(
                f"{target.capitalize()} {is_req}", 
                ["-- Not Provided --"] + raw_cols, 
                index=default_val + 1 if auto_maps.get(target) else 0
            )

    if st.button("Initialize Engine & Generate Insights", type="primary"):
        for req in required_cols:
            if mapping_results[req] == "-- Not Provided --":
                st.error(f"Missing mandatory mapping: {req}")
                st.stop()
                
        with st.spinner("Running ML Forecasting & Profit Classification (This may take a minute)..."):
            df_clean = pd.DataFrame()
            for key, val in mapping_results.items():
                if val != "-- Not Provided --":
                    df_clean[key] = df_raw[val]
            
            df_clean['date'] = pd.to_datetime(df_clean['date'], format='%d-%m-%Y-%I:%M %p', errors='coerce')

            if df_clean['date'].isna().any():
                df_clean['date'] = df_clean['date'].fillna(
                    pd.to_datetime(df_raw['date'], errors='coerce', dayfirst=True)
                )
            df_clean = df_clean.dropna(subset=['date'])
            df_clean['qty'] = pd.to_numeric(df_clean['qty'], errors='coerce').fillna(0)
            df_clean = df_clean[df_clean['qty'] > 0]
            
            for num_col in ['subtotal', 'cost', 'profit']:
                if num_col in df_clean.columns:
                    df_clean[num_col] = pd.to_numeric(df_clean[num_col], errors='coerce').fillna(0)

            final_matrix = build_intelligence_matrix(df_clean, lead_time_weeks)
            
            st.divider()
            st.header("Executive Dashboard")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Active SKUs", f"{len(final_matrix):,}")
            c2.metric("Dead Stock (90d+)", f"{len(final_matrix[final_matrix['days_since_sold'] > 90]):,}")
            if 'total_profit' in final_matrix.columns:
                c3.metric("Total Profit", f"${final_matrix['total_profit'].sum():,.2f}")
            c4.metric("Aggressive Restocks", f"{len(final_matrix[final_matrix['suggested_action'] == 'Restock Aggressively']):,}")
            
            st.subheader("Portfolio Segments (ABC-XYZ)")
            segment_counts = final_matrix['segment'].value_counts().reset_index()
            segment_counts.columns = ['Segment', 'Count']
            fig = px.treemap(segment_counts, path=['Segment'], values='Count', color='Count', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Inventory Action Matrix")
            st.dataframe(
                final_matrix.sort_values(by=f'lead_demand_({max(1, int(lead_time_weeks))}w)', ascending=False),
                use_container_width=True,
                column_config={
                    "total_profit": st.column_config.NumberColumn("Profit", format="$%f"),
                    f'lead_demand_({max(1, int(lead_time_weeks))}w)': st.column_config.NumberColumn("Forecast Demand", help=f"Expected demand over the {lead_time_days} day lead time.")
                }
            )
            
            csv = final_matrix.to_csv(index=False).encode('utf-8')
            st.download_button("Download Action Matrix (CSV)", csv, "inventory_matrix.csv", "text/csv")