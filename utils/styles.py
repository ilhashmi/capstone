import streamlit as st

# ── 1. COLOR PALETTE ─────────────────────────────────────────────────────────
# PlayStation-inspired: Paper White canvas · Console Black hero · PS Blue (#0070cc)
C = {
    # Surfaces
    "bg":           "#ffffff",      # Paper White — main canvas
    "surface":      "#f5f7fa",      # Ice Mist — sidebar & card lift
    "surface2":     "#f3f3f3",      # Divider Tint — subtle row separation
    "hero_bg":      "#000000",      # Console Black — masthead / hero panels
    "footer_bg":    "#0070cc",      # PlayStation Blue — footer anchor

    # Borders
    "border":       "#e8e8e8",      # Resting border
    "border_dark":  "#cccccc",      # Stronger border

    # Text
    "text":         "#000000",      # Display Ink
    "text2":        "#1f1f1f",      # Deep Charcoal — body headlines
    "muted":        "#6b6b6b",      # Body Gray — secondary text
    "faint":        "#999999",      # Mute Gray — tertiary / disabled
    "inverse":      "#ffffff",      # On dark/blue surfaces

    # Brand
    "blue":         "#0070cc",      # PlayStation Blue — primary CTA & anchor
    "cyan":         "#1eaedb",      # PlayStation Cyan — hover/focus only
    "orange":       "#d53b00",      # Commerce Orange — alerts & buy CTAs
    "orange_active":"#aa2f00",      # Commerce Orange active

    # Semantic — all accessible on #ffffff
    "green":        "#15803d",      # Success
    "red":          "#c81b3a",      # Error / Warning Red
    "yellow":       "#b45309",      # Caution amber
    "teal":         "#0369a1",      # Info teal
    "purple":       "#6d28d9",      # Analytics purple

    # Chart extended palette
    "chart1":       "#0070cc",
    "chart2":       "#15803d",
    "chart3":       "#b45309",
    "chart4":       "#6d28d9",
    "chart5":       "#0369a1",
    "chart6":       "#d53b00",

    # Legacy alias (used as chart fallback)
    "gray":         "#999999",

    # Elevation shadows (PlayStation depth scale)
    "shadow_hero":  "rgba(0,0,0,0.80)",
    "shadow_lg":    "rgba(0,0,0,0.16)",
    "shadow_md":    "rgba(0,0,0,0.08)",
    "shadow_sm":    "rgba(0,0,0,0.06)",
}

# ── 2. PLOTLY DEFAULTS — Light Theme ─────────────────────────────────────────
PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(245,247,250,0.4)",
    font=dict(family="Inter, Arial, Helvetica, sans-serif", color=C["muted"], size=12),
    xaxis=dict(
        gridcolor="rgba(0,0,0,0.06)", linecolor=C["border"],
        tickfont=dict(color=C["muted"]), title_font=dict(color=C["text2"]),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor="rgba(0,0,0,0.06)", linecolor=C["border"],
        tickfont=dict(color=C["muted"]), title_font=dict(color=C["text2"]),
        zeroline=False,
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.95)", bordercolor=C["border"],
        borderwidth=1, font=dict(color=C["text2"]),
    ),
    margin=dict(l=16, r=16, t=44, b=16),
    title=dict(font=dict(size=14, color=C["text2"], family="Inter, Arial, sans-serif"), x=0),
    hoverlabel=dict(
        bgcolor="#ffffff", bordercolor=C["border"],
        font=dict(color=C["text2"], family="Inter, Arial, sans-serif", size=12),
    ),
)

# ── 3. SEMANTIC COLOR MAPS ───────────────────────────────────────────────────
STAGE_COLORS = {
    "trending":   C["green"],  "fast_mover": C["teal"],   "new":     C["blue"],
    "neutral":    C["faint"],  "slow_mover": C["yellow"], "dead":    C["red"],
}
ABCXYZ_COLORS = {
    "AX": "#0070cc", "AY": "#3b8fd4", "AZ": "#7ab0e0",
    "BX": "#15803d", "BY": "#22a25a", "BZ": "#6abf8a",
    "CX": "#999999", "CY": "#bbbbbb", "CZ": "#dddddd",
}
CHURN_COLORS = {
    "Active":  C["green"],
    "At Risk": C["yellow"],
    "Churned": C["red"],
}
SEG_COLORS = {
    "Champions":          C["blue"],
    "Loyal":              C["green"],
    "Potential Loyalists":C["teal"],
    "New Customers":      "#3b8fd4",
    "Needs Attention":    C["yellow"],
    "At Risk":            C["orange"],
    "Cannot Lose":        C["red"],
    "Hibernating":        C["faint"],
}

# ── 4. CSS INJECTION ─────────────────────────────────────────────────────────
def apply_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Base Reset ───────────────────────────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Inter', Arial, Helvetica, sans-serif !important;
    }}
    .stApp {{
        background: {C["bg"]} !important;
        color: {C["text2"]} !important;
    }}
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main {{
        background: {C["bg"]} !important;
    }}
    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }}

    /* Force all text to dark on light canvas */
    h1, h2, h3, h4, h5, h6 {{
        color: {C["text2"]} !important;
        font-weight: 600 !important;
    }}
    p, li, span, label {{
        color: {C["text2"]};
    }}
    .stMarkdown p, .stMarkdown li {{
        color: {C["text2"]} !important;
        line-height: 1.6;
    }}

    /* ── Scrollbar ────────────────────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: {C["surface"]}; }}
    ::-webkit-scrollbar-thumb {{ background: {C["border_dark"]}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {C["muted"]}; }}

    /* ── Sidebar ──────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {C["surface"]} !important;
        border-right: 1px solid {C["border"]} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {C["text2"]} !important;
    }}
    [data-testid="stSidebarNav"] {{
        background: transparent !important;
    }}

    /* ── Widget Labels ────────────────────────────────────────────────────── */
    [data-testid="stWidgetLabel"] * {{
        color: {C["muted"]} !important;
        font-weight: 500 !important;
        font-size: 12px !important;
    }}

    /* ── Selectbox ────────────────────────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {{
        background: {C["bg"]} !important;
        border-color: {C["border"]} !important;
        color: {C["text2"]} !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSelectbox"] > div > div:focus-within {{
        border-color: {C["blue"]} !important;
        box-shadow: 0 0 0 2px rgba(0,112,204,0.15) !important;
    }}
    [data-testid="stSelectbox"] svg {{ fill: {C["muted"]} !important; }}

    /* ── Text Input ───────────────────────────────────────────────────────── */
    [data-testid="stTextInput"] > div > div > input {{
        background: {C["bg"]} !important;
        border-color: {C["border"]} !important;
        color: {C["text2"]} !important;
        border-radius: 6px !important;
    }}
    [data-testid="stTextInput"] > div > div > input:focus {{
        border-color: {C["blue"]} !important;
        box-shadow: 0 0 0 2px rgba(0,112,204,0.15) !important;
    }}
    [data-testid="stTextInput"] > div > div > input::placeholder {{
        color: {C["faint"]} !important;
    }}

    /* ── Multiselect ──────────────────────────────────────────────────────── */
    [data-baseweb="tag"] {{
        background: rgba(0,112,204,0.08) !important;
        border: 1px solid rgba(0,112,204,0.2) !important;
        color: {C["blue"]} !important;
        border-radius: 4px !important;
    }}
    [data-baseweb="tag"] span {{
        color: {C["blue"]} !important;
    }}

    /* ── Tabs ─────────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {C["surface"]};
        border-radius: 8px;
        padding: 4px;
        border: 1px solid {C["border"]};
        gap: 2px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 500;
        color: {C["muted"]} !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.18s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {C["text2"]} !important;
        background: {C["bg"]} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: {C["bg"]} !important;
        color: {C["blue"]} !important;
        font-weight: 600 !important;
        border: 1px solid {C["border"]} !important;
        box-shadow: 0 1px 4px {C["shadow_sm"]} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none !important; }}
    .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}
    .stTabs [data-baseweb="tab-panel"] {{
        background: {C["bg"]} !important;
        padding-top: 20px !important;
    }}

    /* ── Buttons ──────────────────────────────────────────────────────────── */
    .stButton > button {{
        background: {C["bg"]} !important;
        border: 1px solid {C["border"]} !important;
        color: {C["text2"]} !important;
        border-radius: 999px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        transition: background 0.18s ease, border-color 0.18s ease,
                    box-shadow 0.18s ease, transform 0.18s ease !important;
    }}
    .stButton > button:hover {{
        border-color: {C["blue"]} !important;
        color: {C["blue"]} !important;
        background: rgba(0,112,204,0.04) !important;
    }}

    /* Primary button — full PlayStation signature */
    .stButton > button[kind="primary"] {{
        background: {C["blue"]} !important;
        border: none !important;
        color: {C["inverse"]} !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 28px !important;
        box-shadow: none !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {C["cyan"]} !important;
        border: 2px solid {C["inverse"]} !important;
        box-shadow: 0 0 0 2px {C["blue"]} !important;
        transform: scale(1.05) !important;
    }}
    .stButton > button[kind="primary"]:active {{
        opacity: 0.6 !important;
    }}

    /* ── Download Button ──────────────────────────────────────────────────── */
    .stDownloadButton > button {{
        background: {C["bg"]} !important;
        border: 1px solid {C["border"]} !important;
        color: {C["blue"]} !important;
        border-radius: 999px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
    }}
    .stDownloadButton > button:hover {{
        border-color: {C["blue"]} !important;
        background: rgba(0,112,204,0.04) !important;
    }}

    /* ── Expander ─────────────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: {C["bg"]} !important;
        border: 1px solid {C["border"]} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary {{
        color: {C["text2"]} !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }}

    /* ── Slider ───────────────────────────────────────────────────────────── */
    [data-testid="stSlider"] [role="slider"] {{
        background: {C["blue"]} !important;
    }}
    [data-testid="stSlider"] div[data-baseweb="slider"] div {{
        background: {C["blue"]} !important;
    }}

    /* ── Radio ────────────────────────────────────────────────────────────── */
    [data-testid="stRadio"] > div {{
        gap: 6px !important;
    }}
    [data-testid="stRadio"] label {{
        background: {C["bg"]} !important;
        border: 1px solid {C["border"]} !important;
        border-radius: 999px !important;
        padding: 6px 16px !important;
        font-size: 13px !important;
        cursor: pointer;
        transition: all 0.15s ease;
    }}
    [data-testid="stRadio"] label:has(input:checked) {{
        border-color: {C["blue"]} !important;
        color: {C["blue"]} !important;
        background: rgba(0,112,204,0.06) !important;
    }}

    /* ── File Uploader ────────────────────────────────────────────────────── */
    [data-testid="stFileUploader"] > div {{
        background: {C["bg"]} !important;
        border: 1.5px dashed {C["border_dark"]} !important;
        border-radius: 10px !important;
        transition: border-color 0.18s ease;
    }}
    [data-testid="stFileUploader"] > div:hover {{
        border-color: {C["blue"]} !important;
        background: rgba(0,112,204,0.02) !important;
    }}

    /* ── Divider ──────────────────────────────────────────────────────────── */
    hr {{
        border-color: {C["border"]} !important;
        opacity: 1 !important;
        margin: 20px 0 !important;
    }}

    /* ── Dataframe / Table ────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {C["border"]} !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }}
    [data-testid="stDataFrame"] th {{
        background: {C["surface"]} !important;
        color: {C["muted"]} !important;
        font-weight: 600 !important;
        font-size: 11px !important;
    }}
    [data-testid="stDataFrame"] td {{
        color: {C["text2"]} !important;
    }}

    /* ── Native Alerts ────────────────────────────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 8px !important;
    }}

    /* ── Metrics ──────────────────────────────────────────────────────────── */
    [data-testid="stMetricValue"] {{
        color: {C["text2"]} !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {C["muted"]} !important;
        font-weight: 500 !important;
        font-size: 12px !important;
    }}

    /* ── Spinner ──────────────────────────────────────────────────────────── */
    [data-testid="stSpinner"] {{
        color: {C["blue"]} !important;
    }}


    /* ════════════════════════════════════════════════════════════════════════
       CUSTOM COMPONENT CLASSES
       ════════════════════════════════════════════════════════════════════════ */

    /* ── KPI Cards ────────────────────────────────────────────────────────── */
    .kpi-card {{
        background: {C["bg"]};
        border: 1px solid {C["border"]};
        border-radius: 12px;
        padding: 20px 22px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px {C["shadow_sm"]};
        transition: box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }}
    .kpi-card:hover {{
        box-shadow: 0 4px 16px {C["shadow_md"]};
    }}
    .kpi-card.accent-blue   {{ border-top: 3px solid {C["blue"]}; }}
    .kpi-card.accent-green  {{ border-top: 3px solid {C["green"]}; }}
    .kpi-card.accent-red    {{ border-top: 3px solid {C["red"]}; }}
    .kpi-card.accent-yellow {{ border-top: 3px solid {C["yellow"]}; }}
    .kpi-card.accent-purple {{ border-top: 3px solid {C["purple"]}; }}
    .kpi-label {{
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: {C["muted"]};
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 30px;
        font-weight: 700;
        color: {C["text2"]};
        line-height: 1.1;
        letter-spacing: -0.02em;
    }}
    .kpi-sub {{
        font-size: 12px;
        color: {C["muted"]};
        margin-top: 5px;
        font-weight: 400;
    }}
    .kpi-delta-pos {{
        display: inline-flex; align-items: center; gap: 3px;
        font-size: 11px; color: {C["green"]}; margin-top: 6px; font-weight: 600;
        background: rgba(21,128,61,0.08); padding: 2px 8px; border-radius: 20px;
    }}
    .kpi-delta-neg {{
        display: inline-flex; align-items: center; gap: 3px;
        font-size: 11px; color: {C["red"]}; margin-top: 6px; font-weight: 600;
        background: rgba(200,27,58,0.08); padding: 2px 8px; border-radius: 20px;
    }}
    .kpi-delta-neu {{
        font-size: 11px; color: {C["muted"]}; margin-top: 6px; font-weight: 500;
        padding: 2px 8px;
    }}

    /* ── Section Headers ──────────────────────────────────────────────────── */
    .sec-hdr {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 15px;
        font-weight: 600;
        color: {C["text2"]};
        padding: 20px 0 12px;
        border-bottom: 1px solid {C["border"]};
        margin-bottom: 16px;
    }}
    .sec-hdr::before {{
        content: '';
        display: block;
        width: 3px;
        height: 16px;
        border-radius: 2px;
        background: {C["blue"]};
        flex-shrink: 0;
    }}
    .sec-hdr-icon {{
        font-size: 15px;
    }}

    /* ── Chart Card Wrapper ───────────────────────────────────────────────── */
    .chart-card {{
        background: {C["bg"]};
        border: 1px solid {C["border"]};
        border-radius: 12px;
        padding: 20px 18px 10px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px {C["shadow_sm"]};
    }}
    .chart-title {{
        font-size: 13px;
        font-weight: 600;
        color: {C["text2"]};
        margin-bottom: 3px;
    }}
    .chart-subtitle {{
        font-size: 12px;
        color: {C["muted"]};
        margin-bottom: 10px;
    }}

    /* ── Badge System ─────────────────────────────────────────────────────── */
    .badge {{
        display: inline-flex;
        align-items: center;
        padding: 2px 9px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 600;
        white-space: nowrap;
    }}
    .b-green  {{ background: rgba(21,128,61,0.10);  color: {C["green"]};  border: 1px solid rgba(21,128,61,0.25); }}
    .b-yellow {{ background: rgba(180,83,9,0.10);   color: {C["yellow"]}; border: 1px solid rgba(180,83,9,0.25); }}
    .b-red    {{ background: rgba(200,27,58,0.10);  color: {C["red"]};    border: 1px solid rgba(200,27,58,0.25); }}
    .b-blue   {{ background: rgba(0,112,204,0.10);  color: {C["blue"]};   border: 1px solid rgba(0,112,204,0.25); }}
    .b-gray   {{ background: rgba(153,153,153,0.10);color: {C["faint"]};  border: 1px solid rgba(153,153,153,0.25); }}
    .b-cyan   {{ background: rgba(3,105,161,0.10);  color: {C["teal"]};   border: 1px solid rgba(3,105,161,0.25); }}
    .b-orange {{ background: rgba(213,59,0,0.10);   color: {C["orange"]}; border: 1px solid rgba(213,59,0,0.25); }}
    .b-teal   {{ background: rgba(3,105,161,0.10);  color: {C["teal"]};   border: 1px solid rgba(3,105,161,0.25); }}
    .b-purple {{ background: rgba(109,40,217,0.10); color: {C["purple"]}; border: 1px solid rgba(109,40,217,0.25); }}

    /* ── Alert / Info Boxes ───────────────────────────────────────────────── */
    .alert-box {{
        background: rgba(200,27,58,0.04);
        border: 1px solid rgba(200,27,58,0.18);
        border-left: 3px solid {C["red"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: {C["red"]};
        line-height: 1.5;
    }}
    .info-box {{
        background: rgba(0,112,204,0.04);
        border: 1px solid rgba(0,112,204,0.16);
        border-left: 3px solid {C["blue"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: {C["blue"]};
        line-height: 1.5;
    }}
    .warn-box {{
        background: rgba(180,83,9,0.04);
        border: 1px solid rgba(180,83,9,0.18);
        border-left: 3px solid {C["yellow"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: {C["yellow"]};
        line-height: 1.5;
    }}
    .success-box {{
        background: rgba(21,128,61,0.04);
        border: 1px solid rgba(21,128,61,0.18);
        border-left: 3px solid {C["green"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: {C["green"]};
        line-height: 1.5;
    }}

    /* ── Tables ───────────────────────────────────────────────────────────── */
    .tbl {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        border-radius: 8px;
        overflow: hidden;
    }}
    .tbl th {{
        background: {C["surface"]};
        color: {C["muted"]};
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 11px 14px;
        text-align: left;
        border-bottom: 1px solid {C["border"]};
        white-space: nowrap;
    }}
    .tbl td {{
        padding: 11px 14px;
        border-bottom: 1px solid {C["surface2"]};
        color: {C["text2"]};
        vertical-align: middle;
        line-height: 1.4;
        background: {C["bg"]};
    }}
    .tbl tr:last-child td {{ border-bottom: none; }}
    .tbl tr:hover td {{
        background: rgba(0,112,204,0.03);
    }}
    .tbl-wrapper {{
        border: 1px solid {C["border"]};
        border-radius: 10px;
        overflow: hidden;
        margin: 8px 0 16px;
        box-shadow: 0 1px 4px {C["shadow_sm"]};
    }}

    /* ── Traffic Lights ───────────────────────────────────────────────────── */
    @keyframes pulse-dot {{
        0%,100%{{ opacity:1; }} 50%{{ opacity:0.55; }}
    }}
    .traffic-red    {{
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: {C["red"]}; animation: pulse-dot 2.5s ease-in-out infinite;
    }}
    .traffic-yellow {{
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: {C["yellow"]}; animation: pulse-dot 2.5s ease-in-out infinite;
    }}
    .traffic-green  {{
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        background: {C["green"]}; animation: pulse-dot 2.5s ease-in-out infinite;
    }}

    /* ── Hero Section (Welcome Page) ──────────────────────────────────────── */
    @keyframes fade-up {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    .hero-wrapper {{
        background: {C["bg"]};
        text-align: center;
        padding: 56px 24px 48px;
        margin: -1.5rem -1rem 32px;
        animation: fade-up 0.45s ease both;
    }}
    .hero-eyebrow {{
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: {C["blue"]};
        background: rgba(0,112,204,0.12);
        border: 1px solid rgba(0,112,204,0.28);
        padding: 4px 14px;
        border-radius: 20px;
        margin-bottom: 20px;
    }}
    .hero-title {{
        font-size: 48px;
        font-weight: 300;
        letter-spacing: -0.02em;
        line-height: 1.15;
        margin: 0 0 16px;
        color: {C["inverse"]};
    }}
    .hero-title b {{
        font-weight: 700;
        color: {C["inverse"]};
    }}
    .hero-title .brand {{
        color: {C["blue"]};
        font-weight: 700;
    }}
    .hero-subtitle {{
        font-size: 16px;
        color: rgba(255,255,255,0.62);
        max-width: 520px;
        margin: 0 auto 12px;
        line-height: 1.6;
        font-weight: 400;
    }}
    .hero-tags {{
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
        margin: 22px 0 36px;
    }}
    .hero-tag {{
        font-size: 11px;
        font-weight: 500;
        color: rgba(255,255,255,0.55);
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.14);
        padding: 4px 12px;
        border-radius: 20px;
    }}
    .hero-cta {{
        font-size: 13px;
        color: rgba(255,255,255,0.45);
        margin-top: 8px;
    }}
    .hero-cta b {{ color: {C["blue"]}; }}

    /* ── Feature Cards (Welcome Page) ─────────────────────────────────────── */
    .fc-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin: 0 0 40px;
    }}
    @media (max-width: 900px) {{
        .fc-grid {{ grid-template-columns: 1fr; }}
        .hero-title {{ font-size: 32px; }}
        .hero-wrapper {{ padding: 40px 16px 36px; }}
    }}
    .fc {{
        background: {C["bg"]};
        border: 1px solid {C["border"]};
        border-radius: 14px;
        padding: 28px 24px;
        box-shadow: 0 1px 4px {C["shadow_sm"]};
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
        text-align: left;
        animation: fade-up 0.45s ease both;
    }}
    .fc:hover {{
        box-shadow: 0 4px 20px {C["shadow_md"]};
        border-color: {C["border_dark"]};
    }}
    .fc-blue  {{ border-top: 3px solid {C["blue"]}; }}
    .fc-green {{ border-top: 3px solid {C["green"]}; }}
    .fc-teal  {{ border-top: 3px solid {C["teal"]}; }}
    .fc-icon  {{
        font-size: 28px;
        margin-bottom: 14px;
        display: block;
    }}
    .fc-title {{
        font-size: 16px;
        font-weight: 600;
        color: {C["text2"]};
        margin-bottom: 8px;
        letter-spacing: -0.01em;
    }}
    .fc-desc {{
        font-size: 13px;
        color: {C["muted"]};
        line-height: 1.65;
        margin-bottom: 16px;
    }}
    .fc-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
    }}
    .fc-tag {{
        font-size: 10px;
        font-weight: 500;
        color: {C["muted"]};
        background: {C["surface"]};
        border: 1px solid {C["border"]};
        padding: 2px 8px;
        border-radius: 20px;
    }}

    /* ── Forecast Banner ──────────────────────────────────────────────────── */
    .forecast-banner {{
        background: rgba(0,112,204,0.04);
        border: 1px solid rgba(0,112,204,0.14);
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 16px;
        font-size: 13px;
        color: {C["text2"]};
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .forecast-banner b {{ color: {C["blue"]}; }}
    .forecast-banner .fb-sep {{
        color: {C["border_dark"]};
        font-size: 16px;
    }}
    .forecast-banner .fb-note {{
        font-size: 11px;
        color: {C["muted"]};
        width: 100%;
        margin-top: 3px;
    }}

    /* ── Sidebar Logo Area ────────────────────────────────────────────────── */
    .sidebar-logo {{
        padding: 20px 16px 16px;
        border-bottom: 1px solid {C["border"]};
        margin-bottom: 8px;
    }}
    .sidebar-label {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: {C["muted"]};
        padding: 12px 0 6px;
    }}

    /* ── Module Header Banner ─────────────────────────────────────────────── */
    .module-hdr {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 2px solid {C["border"]};
    }}
    .module-hdr-icon {{
        font-size: 22px;
        width: 44px; height: 44px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(0,112,204,0.07);
        border: 1px solid rgba(0,112,204,0.18);
        border-radius: 10px;
    }}
    .module-hdr-text {{ flex: 1; }}
    .module-hdr-title {{
        font-size: 20px;
        font-weight: 600;
        color: {C["text2"]};
        letter-spacing: -0.01em;
    }}
    .module-hdr-sub {{
        font-size: 12px;
        color: {C["muted"]};
        margin-top: 2px;
    }}

    /* ── Empty State ──────────────────────────────────────────────────────── */
    .empty-state {{
        text-align: center;
        padding: 48px 20px;
        color: {C["faint"]};
    }}
    .empty-state-icon {{ font-size: 36px; margin-bottom: 12px; display: block; opacity: 0.4; }}
    .empty-state-text {{ font-size: 14px; color: {C["muted"]}; }}

    /* ── Stat Row ─────────────────────────────────────────────────────────── */
    .stat-row {{
        display: flex;
        gap: 6px;
        margin: 8px 0 12px;
        flex-wrap: wrap;
    }}
    .stat-pill {{
        font-size: 12px;
        font-weight: 500;
        padding: 4px 12px;
        border-radius: 20px;
        background: {C["surface"]};
        border: 1px solid {C["border"]};
        color: {C["text2"]};
    }}
    .stat-pill b {{ color: {C["blue"]}; }}

    </style>
    """, unsafe_allow_html=True)


# ── 5. UI COMPONENT LIBRARY ──────────────────────────────────────────────────

def kpi(label, value, sub=None, delta=None, delta_fmt="+.1f", prefix="", suffix="", accent=None):
    """Render a KPI metric card.
    accent: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | None
    """
    accent_cls = f" accent-{accent}" if accent else ""

    dhtml = ""
    if delta is not None:
        if isinstance(delta, str):
            dhtml = f'<div class="kpi-delta-neu">{delta}</div>'
        elif delta > 0:
            dhtml = f'<div class="kpi-delta-pos">▲ {delta:{delta_fmt.replace("+","")}}{suffix}</div>'
        elif delta < 0:
            dhtml = f'<div class="kpi-delta-neg">▼ {abs(delta):{delta_fmt.replace("+","")}}{suffix}</div>'
        else:
            dhtml = f'<div class="kpi-delta-neu">— No change</div>'

    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
        <div class="kpi-card{accent_cls}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{prefix}{value}{suffix}</div>
            {sub_html}{dhtml}
        </div>
    """, unsafe_allow_html=True)


def badge(text, color="gray"):
    return f'<span class="badge b-{color}">{text}</span>'


def stage_badge(s):
    m = {
        "trending": "green", "fast_mover": "teal", "new": "blue",
        "neutral": "gray", "slow_mover": "yellow", "dead": "red",
    }
    return badge(s.replace("_", " ").title(), m.get(s, "gray"))


def abc_badge(a):
    return badge(a, {"A": "blue", "B": "cyan", "C": "gray"}.get(a, "gray"))


def xyz_badge(x):
    return badge(x, {"X": "green", "Y": "yellow", "Z": "red"}.get(x, "gray"))


def traffic_light(status):
    cls = {
        "green":  "traffic-green",
        "yellow": "traffic-yellow",
        "red":    "traffic-red",
    }.get(status, "traffic-green")
    return f'<span class="{cls}"></span>'


def sec_hdr(t, icon=None):
    icon_html = f'<span class="sec-hdr-icon">{icon}</span>' if icon else ""
    st.markdown(f'<div class="sec-hdr">{icon_html}{t}</div>', unsafe_allow_html=True)


def module_header(icon, title, subtitle=""):
    st.markdown(f"""
    <div class="module-hdr">
        <div class="module-hdr-icon">{icon}</div>
        <div class="module-hdr-text">
            <div class="module-hdr-title">{title}</div>
            {'<div class="module-hdr-sub">' + subtitle + '</div>' if subtitle else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


def empty_state(message="No data available", icon="📭"):
    st.markdown(f"""
    <div class="empty-state">
        <span class="empty-state-icon">{icon}</span>
        <div class="empty-state-text">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def tbl_wrap(html):
    """Wrap a .tbl HTML string in the styled container div."""
    return f'<div class="tbl-wrapper">{html}</div>'
