import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import io

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Regulatory Intelligence Platform",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d1117;
    color: #e6edf3;
  }

  .main { background-color: #0d1117; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
  }
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stMultiSelect label,
  section[data-testid="stSidebar"] p {
    color: #8b949e !important;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
  }

  /* Header */
  .rip-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border-bottom: 1px solid #21262d;
    padding: 28px 0 20px 0;
    margin-bottom: 32px;
  }
  .rip-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: #f0f6fc;
    letter-spacing: -0.02em;
    margin: 0;
  }
  .rip-subtitle {
    color: #8b949e;
    font-size: 0.82rem;
    font-weight: 400;
    margin-top: 4px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  /* Metric cards */
  .metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 20px 24px;
    text-align: center;
  }
  .metric-number {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #58a6ff;
    line-height: 1;
  }
  .metric-label {
    color: #8b949e;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
  }

  /* Priority badges */
  .badge-high   { background:#3d1a1a; color:#f85149; border:1px solid #6e1a1a; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-medium { background:#2d2a16; color:#e3b341; border:1px solid #5a4a10; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-low    { background:#122116; color:#3fb950; border:1px solid #1a4a25; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-na     { background:#1c2128; color:#8b949e; border:1px solid #30363d; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }

  /* Intelligence cards */
  .intel-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
  }
  .intel-card:hover { border-color: #58a6ff44; }
  .intel-card-high  { border-left: 3px solid #f85149; }
  .intel-card-medium { border-left: 3px solid #e3b341; }
  .intel-card-low   { border-left: 3px solid #3fb950; }
  .intel-card-na    { border-left: 3px solid #30363d; }

  .card-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f0f6fc;
    margin-bottom: 6px;
    line-height: 1.4;
  }
  .card-meta {
    font-size: 0.75rem;
    color: #8b949e;
    margin-bottom: 8px;
  }
  .card-summary {
    font-size: 0.82rem;
    color: #c9d1d9;
    line-height: 1.6;
    margin-bottom: 10px;
  }
  .card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .tag {
    background: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .tag-blue { background:#0d2140; color:#58a6ff; border-color:#1a3a6a; }

  /* Section headers */
  .section-header {
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem;
    color: #f0f6fc;
    border-bottom: 1px solid #21262d;
    padding-bottom: 10px;
    margin-bottom: 20px;
    margin-top: 8px;
  }

  /* Search bar */
  .stTextInput input {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #f0f6fc !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
  }
  .stTextInput input:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 2px #58a6ff22 !important;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background-color: #161b22;
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
  }
  .stTabs [data-baseweb="tab"] {
    color: #8b949e !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    border-radius: 6px !important;
  }
  .stTabs [aria-selected="true"] {
    background-color: #21262d !important;
    color: #f0f6fc !important;
  }

  /* Expander */
  .streamlit-expanderHeader {
    background-color: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
    font-size: 0.85rem !important;
  }
  .streamlit-expanderContent {
    background-color: #161b22 !important;
    border: 1px solid #21262d !important;
    border-top: none !important;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0d1117; }
  ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
  .viewerBadge_container__1QSob { display: none; }
</style>
""", unsafe_allow_html=True)


# ── GOOGLE SHEETS CONNECTION (public, read-only) ─────────────────────────────
SHEET_ID = "1VIkRptXrV0HPjTxuzq96wVx67rBtbk8tW-acGop5DME"

TAB_IDS = {
    "Updates":     "1528624300",
    "News":        "685156462",
    "Competitors": "1451797372",
}

@st.cache_data(ttl=300)
def load_tab(tab_name: str) -> pd.DataFrame:
    try:
        gid = TAB_IDS.get(tab_name, "0")
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        return df
    except Exception as e:
        st.error(f"Could not load '{tab_name}': {e}")
        return pd.DataFrame()


# ── HELPERS ───────────────────────────────────────────────────────────────────
def priority_badge(p: str) -> str:
    p = str(p).strip().lower()
    if p == "high":   return '<span class="badge-high">HIGH</span>'
    if p == "medium": return '<span class="badge-medium">MEDIUM</span>'
    if p == "low":    return '<span class="badge-low">LOW</span>'
    return '<span class="badge-na">—</span>'

def card_class(p: str) -> str:
    p = str(p).strip().lower()
    if p == "high":   return "intel-card intel-card-high"
    if p == "medium": return "intel-card intel-card-medium"
    if p == "low":    return "intel-card intel-card-low"
    return "intel-card intel-card-na"

def render_card(row: pd.Series, show_source=True):
    title   = str(row.get("Title", "")).strip() or "Untitled"
    url     = str(row.get("URL", "")).strip()
    summary = str(row.get("AI Summary", row.get("Summary", ""))).strip()
    pri     = str(row.get("Priority", "")).strip()
    ta      = str(row.get("Therapeutic Area", "")).strip()
    ha      = str(row.get("Health Authority", row.get("Source", ""))).strip()
    pub     = str(row.get("Published Date", row.get("Date", ""))).strip()[:16]
    source  = str(row.get("Source", row.get("Feed", ""))).strip()
    impl    = str(row.get("Implications", "")).strip()
    actions = str(row.get("Action Items", "")).strip()

    title_html = f'<a href="{url}" target="_blank" style="color:#f0f6fc;text-decoration:none;">{title}</a>' if url else title

    tags_html = ""
    if ta and ta not in ("-", ""):
        tags_html += f'<span class="tag tag-blue">{ta}</span>'
    if ha and ha not in ("-", ""):
        tags_html += f'<span class="tag">{ha}</span>'
    if show_source and source:
        tags_html += f'<span class="tag">{source}</span>'

    meta = pub
    if not meta:
        meta = "—"

    html = f"""
    <div class="{card_class(pri)}">
      <div class="card-title">{title_html}</div>
      <div class="card-meta">{meta}</div>
      <div class="card-summary">{summary[:400] if summary else "No summary available."}</div>
      <div class="card-tags">{priority_badge(pri)}{tags_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if impl or actions:
        with st.expander("Analysis details"):
            if impl:
                st.markdown(f"**Implications:** {impl}")
            if actions:
                st.markdown(f"**Action Items:** {actions}")


def filter_df(df, search="", ha_filter=None, ta_filter=None, pri_filter=None):
    if df.empty:
        return df
    if search:
        mask = df.apply(lambda r: search.lower() in " ".join(r.astype(str).values).lower(), axis=1)
        df = df[mask]
    if ha_filter:
        df = df[df.get("Health Authority", df.get("Source", pd.Series(dtype=str))).str.contains("|".join(ha_filter), case=False, na=False)]
    if ta_filter:
        df = df[df.get("Therapeutic Area", pd.Series(dtype=str)).str.contains("|".join(ta_filter), case=False, na=False)]
    if pri_filter:
        df = df[df.get("Priority", pd.Series(dtype=str)).str.lower().isin([p.lower() for p in pri_filter])]
    return df


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 24px 0;">
      <div style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:#f0f6fc;">⚕ RIP</div>
      <div style="color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Regulatory Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**SEARCH**")
    search_query = st.text_input("", placeholder="Search all intelligence…", label_visibility="collapsed")

    st.divider()
    st.markdown("**FILTERS**")

    priority_options = ["High", "Medium", "Low"]
    selected_priority = st.multiselect("Priority", priority_options, default=[])

    ha_options = ["FDA", "EMA", "ICH", "FDA/EMA", "Other"]
    selected_ha = st.multiselect("Health Authority", ha_options, default=[])

    ta_options = ["Oncology", "Gene Therapy", "Cell Therapy", "Rare Disease", "Autoimmune", "General"]
    selected_ta = st.multiselect("Therapeutic Area", ta_options, default=[])

    st.divider()
    if st.button("🔄  Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"""
    <div style="color:#8b949e;font-size:10px;text-align:center;margin-top:16px;">
      Last updated<br>{datetime.now().strftime("%b %d, %Y %H:%M")}
    </div>
    """, unsafe_allow_html=True)


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="rip-header">
  <div class="rip-title">Regulatory Intelligence Platform</div>
  <div class="rip-subtitle">Automated pharmaceutical intelligence — {date.today().strftime("%B %d, %Y")}</div>
</div>
""", unsafe_allow_html=True)


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
with st.spinner("Loading intelligence data…"):
    df_updates     = load_tab("Updates")
    df_news        = load_tab("News")
    df_competitors = load_tab("Competitors")


# ── METRIC CARDS ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

def high_count(df):
    if df.empty or "Priority" not in df.columns: return 0
    return int((df["Priority"].fillna("").str.lower() == "high").sum())

total_items  = len(df_updates) + len(df_news) + len(df_competitors)
high_total   = high_count(df_updates) + high_count(df_news)
reg_count    = len(df_updates)
news_count   = len(df_news)
comp_count   = len(df_competitors)

for col, num, label in [
    (c1, total_items, "Total Items"),
    (c2, high_total,  "High Priority"),
    (c3, reg_count,   "Regulatory"),
    (c4, news_count,  "News"),
    (c5, comp_count,  "Competitors"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-number">{num}</div>
          <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)


# ── TABS ──────────────────────────────────────────────────────────────────────
tab_home, tab_regulatory, tab_news, tab_competitors, tab_search = st.tabs([
    "🏠  Home", "🏛  Regulatory", "📰  News", "🔎  Competitors", "🔍  Search"
])


# ─── HOME TAB ─────────────────────────────────────────────────────────────────
with tab_home:
    st.markdown('<div class="section-header">🚨 High Priority Items</div>', unsafe_allow_html=True)

    high_updates = df_updates[df_updates["Priority"].str.lower() == "high"] if not df_updates.empty and "Priority" in df_updates.columns else pd.DataFrame()
    high_news    = df_news[df_news["Priority"].str.lower() == "high"] if not df_news.empty and "Priority" in df_news.columns else pd.DataFrame()
    high_all     = pd.concat([high_updates, high_news]).head(10)

    if high_all.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No high priority items today.</div>', unsafe_allow_html=True)
    else:
        for _, row in high_all.iterrows():
            render_card(row)

    st.markdown('<div class="section-header" style="margin-top:32px;">📋 Latest Regulatory Updates</div>', unsafe_allow_html=True)
    recent_updates = df_updates.head(5) if not df_updates.empty else pd.DataFrame()
    if recent_updates.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No regulatory updates available.</div>', unsafe_allow_html=True)
    else:
        for _, row in recent_updates.iterrows():
            render_card(row)

    st.markdown('<div class="section-header" style="margin-top:32px;">📰 Latest News</div>', unsafe_allow_html=True)
    recent_news = df_news.head(5) if not df_news.empty else pd.DataFrame()
    if recent_news.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No news available.</div>', unsafe_allow_html=True)
    else:
        for _, row in recent_news.iterrows():
            render_card(row)


# ─── REGULATORY TAB ───────────────────────────────────────────────────────────
with tab_regulatory:
    st.markdown('<div class="section-header">🏛 Regulatory Updates — FDA / EMA / ICH</div>', unsafe_allow_html=True)

    df_reg_filtered = filter_df(df_updates, search_query, selected_ha, selected_ta, selected_priority)

    if df_reg_filtered.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No items match your filters.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="color:#8b949e;font-size:12px;margin-bottom:16px;">{len(df_reg_filtered)} items</div>', unsafe_allow_html=True)
        for _, row in df_reg_filtered.iterrows():
            render_card(row)


# ─── NEWS TAB ─────────────────────────────────────────────────────────────────
with tab_news:
    st.markdown('<div class="section-header">📰 Industry News & Publications</div>', unsafe_allow_html=True)

    df_news_filtered = filter_df(df_news, search_query, selected_ha, selected_ta, selected_priority)

    if df_news_filtered.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No items match your filters.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="color:#8b949e;font-size:12px;margin-bottom:16px;">{len(df_news_filtered)} items</div>', unsafe_allow_html=True)

        # Group by source
        sources = df_news_filtered["Source"].unique() if "Source" in df_news_filtered.columns else ["All"]
        show_all = st.toggle("Group by source", value=False)

        if show_all and "Source" in df_news_filtered.columns:
            for src in sources:
                src_df = df_news_filtered[df_news_filtered["Source"] == src]
                with st.expander(f"**{src}** — {len(src_df)} items"):
                    for _, row in src_df.iterrows():
                        render_card(row, show_source=False)
        else:
            for _, row in df_news_filtered.iterrows():
                render_card(row)


# ─── COMPETITORS TAB ──────────────────────────────────────────────────────────
with tab_competitors:
    st.markdown('<div class="section-header">🔎 Competitive Intelligence</div>', unsafe_allow_html=True)

    if df_competitors.empty:
        st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No competitor intelligence available.</div>', unsafe_allow_html=True)
    else:
        search_comp = search_query
        df_comp_filtered = df_competitors.copy()
        if search_comp:
            mask = df_comp_filtered.apply(lambda r: search_comp.lower() in " ".join(r.astype(str).values).lower(), axis=1)
            df_comp_filtered = df_comp_filtered[mask]

        st.markdown(f'<div style="color:#8b949e;font-size:12px;margin-bottom:16px;">{len(df_comp_filtered)} items</div>', unsafe_allow_html=True)

        for _, row in df_comp_filtered.iterrows():
            title   = str(row.get("Title", "")).strip() or "Untitled"
            url     = str(row.get("URL", "")).strip()
            summary = str(row.get("Summary", "")).strip()
            company = str(row.get("Company", "")).strip()
            cat     = str(row.get("Category", "")).strip()
            source  = str(row.get("Source", "")).strip()
            dt      = str(row.get("Date", row.get("Run Date", ""))).strip()[:16]
            notes   = str(row.get("Notes", "")).strip()

            title_html = f'<a href="{url}" target="_blank" style="color:#f0f6fc;text-decoration:none;">{title}</a>' if url else title

            tags_html = ""
            if company: tags_html += f'<span class="tag tag-blue">{company}</span>'
            if cat:     tags_html += f'<span class="tag">{cat}</span>'
            if source:  tags_html += f'<span class="tag">{source}</span>'

            st.markdown(f"""
            <div class="intel-card intel-card-na">
              <div class="card-title">{title_html}</div>
              <div class="card-meta">{dt}</div>
              <div class="card-summary">{summary[:400] if summary else "No summary available."}</div>
              <div class="card-tags">{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)

            if notes:
                with st.expander("Details"):
                    st.markdown(notes)


# ─── SEARCH TAB ───────────────────────────────────────────────────────────────
with tab_search:
    st.markdown('<div class="section-header">🔍 Search All Intelligence</div>', unsafe_allow_html=True)

    search_input = st.text_input("", placeholder="Search across regulatory updates, news, and competitors…",
                                  key="search_main", label_visibility="collapsed")

    if search_input:
        results_updates     = filter_df(df_updates, search_input)
        results_news        = filter_df(df_news, search_input)
        results_competitors = filter_df(df_competitors, search_input)

        total_results = len(results_updates) + len(results_news) + len(results_competitors)
        st.markdown(f'<div style="color:#8b949e;font-size:12px;margin-bottom:20px;">{total_results} results for "<strong style="color:#f0f6fc;">{search_input}</strong>"</div>', unsafe_allow_html=True)

        if not results_updates.empty:
            st.markdown(f'<div style="color:#58a6ff;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">Regulatory ({len(results_updates)})</div>', unsafe_allow_html=True)
            for _, row in results_updates.iterrows():
                render_card(row)

        if not results_news.empty:
            st.markdown(f'<div style="color:#58a6ff;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin:20px 0 10px 0;">News ({len(results_news)})</div>', unsafe_allow_html=True)
            for _, row in results_news.iterrows():
                render_card(row)

        if not results_competitors.empty:
            st.markdown(f'<div style="color:#58a6ff;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin:20px 0 10px 0;">Competitors ({len(results_competitors)})</div>', unsafe_allow_html=True)
            for _, row in results_competitors.head(20).iterrows():
                render_card(row)

        if total_results == 0:
            st.markdown('<div class="intel-card" style="color:#8b949e;text-align:center;padding:32px;">No results found.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#8b949e;text-align:center;padding:48px;font-size:0.9rem;">Type something above to search across all intelligence.</div>', unsafe_allow_html=True)
