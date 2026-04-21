import requests
import pandas as pd

OPENROUTER_API_KEY = "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"
_API_URL           = "https://openrouter.ai/api/v1/chat/completions"

_FREE_MODELS = [
    "openai/gpt-oss-120b:free",
    "deepseek/deepseek-r1:free",
    "nvidia/nemotron-3-super:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "arcee-ai/trinity-large-preview:free",
    "openrouter/elephant-alpha:free",
    "z-ai/glm-4.5-air:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-3.6-plus:free",
    "upstage/solar-pro-3:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "google/gemma-3-27b-it:free",
    "arcee-ai/trinity-mini:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "openrouter/free"
]

def win_back_insight(cust_row, df):

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in core/ai_engine.py")

    # Purchase history ──────────────────────────────────────────────────
    cid = cust_row.get("customer_id")
    history_lines = []
    if cid is not None and "customer_id" in df.columns:
        hist = (
            df[df["customer_id"] == cid]
            .sort_values("date", ascending=False)
            [["date", "name", "qty", "revenue"]]
            .head(30)
        )
        for _, row in hist.iterrows():
            history_lines.append(
                f"  {str(row['date'])[:10]}  {row['name'][:35]:<35}  "
                f"qty={int(row['qty'])}  rev={row['revenue']:,.0f}"
            )

    history_block = (
        "\n".join(history_lines) if history_lines
        else "  (No detailed transaction history available)"
    )

    # Helpers ───────────────────────────────────────────────────────────
    def _fmt(val):
        try:
            return format(int(val), ",d")
        except Exception:
            return "N/A"

    avg_interval = (
        f"{cust_row['avg_interval_days']:.0f} days"
        if pd.notna(cust_row.get("avg_interval_days"))
        else "unknown"
    )

    prompt = f"""YYou are an expert, no-nonsense retail CRM strategist advising a business owner. Your goal is to provide a highly actionable, concise win-back strategy for a churned or at-risk customer. Focus entirely on ROI and specific data points. Do not include fluff, pleasantries, or generic marketing advice.

CUSTOMER BEHAVIORAL PROFILE:
- Name: {cust_row['customer']}
- Churn Status: {cust_row['churn_risk']}
- RFM Segment: {cust_row['rfm_segment']}
- RFM Score: {cust_row['rfm_score']} (R={cust_row['r_score']}, F={cust_row['f_score']}, M={cust_row['m_score']})
- Lifetime Value: {_fmt(cust_row['monetary'])}
- Projected LTV: {_fmt(cust_row.get('ltv_proj', 'N/A'))}
- Total Profit generated: {_fmt(cust_row.get('total_profit', 'N/A'))}
- Visit Frequency: {_fmt(cust_row['frequency'])} visits
- Average Order Value: {_fmt(cust_row['avg_order_value'])}
- Average Visit Interval: {avg_interval}
- Days Since Last Purchase: {_fmt(cust_row['recency_days'])} days
- Spending Trend: {cust_row.get('spending_trend', 'N/A')}

RECENT PURCHASE HISTORY (newest first):
{history_block}

YOUR TASK:
1. **Customer Profile:** Write exactly 2 to 3 sentences summarizing the customer's financial value, their core buying behavior, and the severity of their churn risk. 
2. **Win-Back Actions:** Provide exactly 4 highly specific, tactical steps to re-engage them. You MUST ground these actions in their specific `RECENT PURCHASE HISTORY` and `CUSTOMER DATA` (e.g., target them with complementary items to their last purchase, or time an offer based on their `Average Visit Interval`). Start each point with a strong action verb.

STRICT OUTPUT FORMAT:
**Customer Profile:**
[2-3 sentence summary]

**Win-Back Actions:**
* [Action 1: specific to past purchases/data]
* [Action 2: specific to past purchases/data]
* [Action 3: specific to past purchases/data]
* [Action 4: specific to past purchases/data]

CONSTRAINTS: 
- Maximum 200 words. 
- Output strictly the format above. 
- No introductory, conversational, or concluding remarks"""



    # API call 
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flow-erp.app",
        "X-Title": "Flow ERP Win-Back Advisor",
    }
    last_error = None
    for model in _FREE_MODELS:
        try:
            response = requests.post(
                _API_URL,
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 380,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code in (429, 404):
                last_error = e
                continue   
            raise          
    raise last_error      
