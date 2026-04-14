import streamlit as st
# 1. COLOR PALETTE
C = {
    "bg":           "#0d0f14",
    "surface":      "#161922",
    "surface2":     "#13151c",
    "border":       "#1e2130",
    "border_hover": "#3d4a6e",
    "text":         "#e8e6df",  
    "muted":        "#9ca3af",  
    "faint":        "#6b7280",
    
    "blue":         "#3b82f6",
    "green":        "#4ade80",
    "yellow":       "#fbbf24",
    "red":          "#f87171",
    "purple":       "#8b5cf6",
    "cyan":         "#38bdf8",
    "teal":         "#2dd4bf",
    "orange":       "#fb923c",
    "gray":         "#9ca3af",
}

# 2. PLOTLY CHART
PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)", 
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Sora, sans-serif", color=C["muted"], size=12),
    xaxis=dict(
        gridcolor=C["border"], linecolor=C["border"], 
        tickfont=dict(color=C["muted"]), title_font=dict(color=C["text"])
    ),
    yaxis=dict(
        gridcolor=C["border"], linecolor=C["border"], 
        tickfont=dict(color=C["muted"]), title_font=dict(color=C["text"])
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"], font=dict(color=C["text"])),
    margin=dict(l=16, r=16, t=40, b=16),
    title=dict(font=dict(size=14, color=C["text"]), x=0),
)
STAGE_COLORS  = {
    "trending": C["green"], "fast_mover": C["teal"], "new": C["blue"],
    "neutral": C["faint"], "slow_mover": C["yellow"], "dead": C["red"]
}

ABCXYZ_COLORS = {
    "AX": C["blue"], "AY": "#60A5FA", "BX": C["green"],
    "BY": C["teal"], "CX": C["faint"], "CY": C["muted"]
}

CHURN_COLORS = {
    "Active": C["green"], "At Risk": C["yellow"], "Churned": C["red"]
}

SEG_COLORS = {
    "Champions": C["green"], "Loyal": "#86efac", "Potential Loyalists": C["cyan"],
    "New Customers": C["blue"], "Needs Attention": C["yellow"],
    "At Risk": C["orange"], "Cannot Lose": C["red"], "Hibernating": C["faint"]
}

# 4. CSS INJECTION
def apply_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Sora', sans-serif; }}
    .stApp {{ background: {C["bg"]}; color: {C["text"]}; }}
    [data-testid="stSidebar"] {{ background: {C["surface2"]}; border-right: 1px solid {C["border"]}; }}
    
    /* Streamlit Input/Widget Labels - Forced to Bright Text */
    [data-testid="stWidgetLabel"] * {{ color: {C["text"]} !important; font-weight: 500; }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ background: {C["surface"]}; border-radius: 8px; padding: 4px; }}
    .stTabs [data-baseweb="tab"] {{ border-radius: 6px; padding: 6px 16px; font-size: 13px; color: {C["muted"]}; }}
    .stTabs [aria-selected="true"] {{ background: {C["surface2"]} !important; color: {C["text"]} !important; border: 1px solid {C["border"]}; }}
    
    /* KPI Cards */
    .kpi-card {{ background: {C["surface"]}; border: 1px solid {C["border"]}; border-radius: 12px; padding: 18px 20px; margin-bottom: 10px; transition: border-color .2s; }}
    .kpi-card:hover {{ border-color: {C["border_hover"]}; }}
    .kpi-label {{ font-size: 11px; font-weight: 600; letter-spacing: .08em; color: {C["muted"]}; text-transform: uppercase; margin-bottom: 5px; }}
    .kpi-value {{ font-size: 26px; font-weight: 600; color: {C["text"]}; line-height: 1.1; }}
    .kpi-sub {{ font-size: 11px; color: {C["muted"]}; margin-top: 3px; }}
    .kpi-delta-pos {{ font-size: 12px; color: {C["green"]}; margin-top: 4px; font-weight: 500; }}
    .kpi-delta-neg {{ font-size: 12px; color: {C["red"]}; margin-top: 4px; font-weight: 500; }}
    .kpi-delta-neu {{ font-size: 12px; color: {C["muted"]}; margin-top: 4px; font-weight: 500; }}
    
    /* Section Headers */
    .sec-hdr {{ font-size: 13px; font-weight: 600; letter-spacing: .08em; color: {C["text"]}; text-transform: uppercase; padding: 14px 0 8px; border-bottom: 1px solid {C["border"]}; margin-bottom: 14px; }}
    
    /* Badges with beautiful borders from inspiration */
    .badge {{ display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 11px; font-weight: 500; }}
    .b-green {{ background: #1a3a2a; color: {C["green"]}; border: 1px solid #166534; }}
    .b-yellow {{ background: #2a1a00; color: {C["yellow"]}; border: 1px solid #92400e; }}
    .b-red {{ background: #2a1515; color: {C["red"]}; border: 1px solid #7f1d1d; }}
    .b-blue {{ background: #1a2e4a; color: #60a5fa; border: 1px solid #1d4ed8; }}
    .b-gray {{ background: #1e2130; color: {C["muted"]}; border: 1px solid #374151; }}
    .b-cyan {{ background: #0d2a2a; color: {C["cyan"]}; border: 1px solid #0f766e; }}
    .b-orange {{ background: #2a1500; color: {C["orange"]}; border: 1px solid #9a3412; }}
    .b-teal {{ background: #0d2a2a; color: {C["teal"]}; border: 1px solid #0f766e; }}
    .b-purple {{ background: #1e1a35; color: {C["purple"]}; border: 1px solid #4c1d95; }}
    
    /* Alert Boxes */
    .alert-box {{ background: #2a1515; border: 1px solid #7f1d1d; border-left: 3px solid #ef4444; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #fca5a5; }}
    .info-box {{ background: #1a2e4a; border: 1px solid #1d4ed8; border-left: 3px solid #3b82f6; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #93c5fd; }}
    .warn-box {{ background: #2a1a00; border: 1px solid #92400e; border-left: 3px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #fde68a; }}
    .success-box {{ background: #0d2a1a; border: 1px solid #166534; border-left: 3px solid #22c55e; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #86efac; }}
    
    /* Tables */
    .tbl {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .tbl th {{ background: {C["surface"]}; color: {C["muted"]}; font-weight: 600; font-size: 11px; letter-spacing: .07em; text-transform: uppercase; padding: 10px 12px; text-align: left; border-bottom: 2px solid {C["border"]}; }}
    .tbl td {{ padding: 10px 12px; border-bottom: 1px solid {C["surface2"]}; color: {C["text"]}; vertical-align: middle; }}
    .tbl tr:hover td {{ background: {C["surface"]}; }}
    
    /* Traffic Lights */
    .traffic-red {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {C["red"]}; box-shadow: 0 0 5px {C["red"]}; }}
    .traffic-yellow {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {C["yellow"]}; box-shadow: 0 0 5px {C["yellow"]}; }}
    .traffic-green {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {C["green"]}; box-shadow: 0 0 5px {C["green"]}; }}
    </style>
    """, unsafe_allow_html=True)

# 5. UI COMPONENTS
def kpi(label, value, sub=None, delta=None, delta_fmt="+.1f", prefix="", suffix=""):
    dhtml = ""
    if delta is not None:
        if isinstance(delta, str):
            dhtml = f'<div class="kpi-delta-neu">{delta}</div>'
        elif delta > 0:
            dhtml = f'<div class="kpi-delta-pos">▲ {delta:{delta_fmt.replace("+","")}}{suffix}</div>'
        elif delta < 0:
            dhtml = f'<div class="kpi-delta-neg">▼ {abs(delta):{delta_fmt.replace("+","")}}{suffix}</div>'
        else:
            dhtml = f'<div class="kpi-delta-neu">— {delta:{delta_fmt.replace("+","")}}{suffix}</div>'
            
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{prefix}{value}{suffix}</div>
            {sub_html}{dhtml}
        </div>
    """, unsafe_allow_html=True)

def badge(text, color="gray"):
    return f'<span class="badge b-{color}">{text}</span>'

def stage_badge(s):
    m = {"trending":"green","fast_mover":"teal","new":"blue","neutral":"gray","slow_mover":"yellow","dead":"red"}
    return badge(s.replace("_"," ").title(), m.get(s,"gray"))

def abc_badge(a):
    return badge(a, {"A":"blue","B":"cyan","C":"gray"}.get(a,"gray"))

def xyz_badge(x):
    return badge(x, {"X":"green","Y":"yellow","Z":"red"}.get(x,"gray"))

def traffic_light(status):
    cls = {"green": "traffic-green", "yellow": "traffic-yellow", "red": "traffic-red"}.get(status, "traffic-gray")
    return f'<span class="{cls}"></span>'

def sec_hdr(t):
    st.markdown(f'<div class="sec-hdr">{t}</div>', unsafe_allow_html=True)