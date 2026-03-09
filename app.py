import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Regulatory Intelligence Platform",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #f7f5f0;
    color: #1a1a1a;
  }
  .main { background-color: #f7f5f0; padding-top: 0 !important; }
  .block-container { padding-top: 0 !important; max-width: 1200px; }

  section[data-testid="stSidebar"] { background-color: #1a1a1a; border-right: none; }
  section[data-testid="stSidebar"] * { color: #c8c4bc !important; }
  section[data-testid="stSidebar"] .stTextInput input {
    background: #2a2a2a !important; border: 1px solid #3a3a3a !important;
    color: #f0ece4 !important; border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 12px !important;
  }
  section[data-testid="stSidebar"] label {
    color: #555 !important; font-size: 10px !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.12em !important;
  }
  section[data-testid="stSidebar"] .stDivider { border-color: #2a2a2a !important; }

  .rip-header {
    background: #1a1a1a; padding: 32px 48px 28px 48px;
    margin: 0 -4rem 0 -4rem;
    display: flex; align-items: flex-end; justify-content: space-between;
  }
  .rip-logo { font-family: 'Playfair Display', serif; font-size: 2.6rem; color: #f0ece4; letter-spacing: -0.03em; line-height: 1; }
  .rip-logo span { color: #c8a96e; }
  .rip-tagline { color: #555; font-size: 10px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.15em; margin-top: 6px; }
  .rip-date { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #555; text-align: right; }

  .metric-strip {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1px; background: #ddd9d2; border: 1px solid #ddd9d2;
    margin: 24px 0; border-radius: 6px; overflow: hidden;
  }
  .metric-cell { background: #fff; padding: 20px 24px; text-align: center; }
  .metric-num { font-family: 'Playfair Display', serif; font-size: 2.8rem; line-height: 1; color: #1a1a1a; }
  .metric-num.high { color: #c0392b; }
  .metric-lbl { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: #888; margin-top: 4px; }

  .badge-high   { background:#fdf0ef; color:#c0392b; border:1px solid #f5c6c2; padding:2px 10px; border-radius:3px; font-size:10px; font-weight:700; font-family:'IBM Plex Mono',monospace; }
  .badge-medium { background:#fdf8ef; color:#b7770d; border:1px solid #f5e2b0; padding:2px 10px; border-radius:3px; font-size:10px; font-weight:700; font-family:'IBM Plex Mono',monospace; }
  .badge-low    { background:#eff7f0; color:#27724a; border:1px solid #b0dfc0; padding:2px 10px; border-radius:3px; font-size:10px; font-weight:700; font-family:'IBM Plex Mono',monospace; }
  .badge-na     { background:#f5f5f5; color:#888;    border:1px solid #ddd;    padding:2px 10px; border-radius:3px; font-size:10px; font-weight:700; font-family:'IBM Plex Mono',monospace; }

  .intel-card { background:#fff; border:1px solid #e8e4de; border-radius:6px; padding:20px 24px; margin-bottom:10px; transition: box-shadow 0.15s, border-color 0.15s; }
  .intel-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.07); border-color:#c8a96e; }
  .intel-card-high   { border-left:4px solid #c0392b; }
  .intel-card-medium { border-left:4px solid #e6a817; }
  .intel-card-low    { border-left:4px solid #27a85a; }
  .intel-card-na     { border-left:4px solid #ddd9d2; }

  .card-title   { font-size:0.92rem; font-weight:600; color:#1a1a1a; margin-bottom:4px; line-height:1.45; }
  .card-meta    { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#aaa; margin-bottom:10px; }
  .card-summary { font-size:0.82rem; color:#444; line-height:1.65; margin-bottom:12px; }
  .card-tags    { display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
  .tag { background:#f5f5f2; color:#777; border:1px solid #e0dbd3; padding:1px 8px; border-radius:3px; font-size:10px; font-weight:500; text-transform:uppercase; letter-spacing:0.06em; font-family:'IBM Plex Mono',monospace; }
  .tag-gold { background:#fdf5e6; color:#b7770d; border-color:#f0d89a; }

  .section-hdr { font-family:'Playfair Display',serif; font-size:1.25rem; color:#1a1a1a; border-bottom:2px solid #1a1a1a; padding-bottom:8px; margin-bottom:20px; margin-top:8px; }
  .item-count  { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#aaa; margin-bottom:16px; }

  .stTabs [data-baseweb="tab-list"] { background:transparent; border-bottom:2px solid #e8e4de; gap:0; padding:0; }
  .stTabs [data-baseweb="tab"] { color:#aaa !important; font-family:'IBM Plex Sans',sans-serif !important; font-size:0.8rem !important; font-weight:500 !important; padding:10px 20px !important; border-radius:0 !important; border-bottom:2px solid transparent !important; margin-bottom:-2px !important; }
  .stTabs [aria-selected="true"] { color:#1a1a1a !important; border-bottom:2px solid #1a1a1a !important; background:transparent !important; }

  details { background:#fafaf8 !important; border:1px solid #e8e4de !important; border-radius:4px !important; margin-top:4px; }
  summary { font-size:12px !important; color:#888 !important; padding:8px 12px !important; }

  .stTextInput input { background:#fff !important; border:1px solid #e0dbd3 !important; border-radius:4px !important; font-family:'IBM Plex Mono',monospace !important; font-size:13px !important; color:#1a1a1a !important; }

  .archive-note { background:#fafaf8; border:1px solid #e8e4de; border-radius:6px; padding:12px 16px; font-size:11px; color:#888; margin-bottom:20px; font-family:'IBM Plex Mono',monospace; }

  .stButton button { background:#1a1a1a !important; color:#f0ece4 !important; border:none !important; border-radius:4px !important; font-family:'IBM Plex Sans',sans-serif !important; font-size:12px !important; }
  .stButton button:hover { background:#333 !important; }

  #MainMenu, footer, header { visibility: hidden; }
  .viewerBadge_container__1QSob { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────────────────
SHEET_NAME = "Raw Intelligence"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(ttl=300)
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_tab(tab_name):
    try:
        gc = get_client()
        ws = gc.open(SHEET_NAME).worksheet(tab_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame()
        # Filter soft-deleted favorites
        if tab_name == "Favorites" and not df.empty and "Deleted" in df.columns:
            df = df[df["Deleted"].fillna("") != "deleted"]
        return df
    except Exception as e:
        st.error(f"Could not load '{tab_name}': {e}")
        return pd.DataFrame()

def save_favorite(row):
    try:
        gc = get_client()
        ss = gc.open(SHEET_NAME)
        try:
            ws = ss.worksheet("Favorites")
        except Exception as e1:
            try:
                ws = ss.add_worksheet("Favorites", rows=1000, cols=20)
                ws.append_row(["Title","URL","Source","Published Date","Priority","Therapeutic Area","AI Summary","Saved At","Deleted"])
            except Exception as e2:
                st.error(f"Cannot create Favorites tab: {e2}")
                return False
        try:
            ws.append_row([
                str(row.get("Title","")),
                str(row.get("URL","")),
                str(row.get("Source","")),
                str(row.get("Published Date", row.get("Date",""))),
                str(row.get("Priority","")),
                str(row.get("Therapeutic Area","")),
                str(row.get("AI Summary", row.get("Summary",""))),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "",
            ])
        except Exception as e3:
            st.error(f"Cannot write to Favorites: {e3}")
            return False
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

# ── HELPERS ───────────────────────────────────────────────────────────────────
def high_count(df):
    if df.empty or "Priority" not in df.columns: return 0
    return int((df["Priority"].fillna("").str.strip().str.lower() == "high").sum())

def priority_badge(p):
    p = str(p).strip().lower()
    if p == "high":   return '<span class="badge-high">HIGH</span>'
    if p == "medium": return '<span class="badge-medium">MED</span>'
    if p == "low":    return '<span class="badge-low">LOW</span>'
    return '<span class="badge-na">—</span>'

def card_border(p):
    p = str(p).strip().lower()
    if p == "high":   return "intel-card intel-card-high"
    if p == "medium": return "intel-card intel-card-medium"
    if p == "low":    return "intel-card intel-card-low"
    return "intel-card intel-card-na"

def render_card(row, show_source=True, idx=None):
    title   = str(row.get("Title",   "")).strip() or "Untitled"
    url     = str(row.get("URL",     "")).strip()
    summary = str(row.get("AI Summary", row.get("Summary", ""))).strip()
    pri     = str(row.get("Priority","")).strip()
    ta      = str(row.get("Therapeutic Area","")).strip()
    ha      = str(row.get("Health Authority", row.get("Source",""))).strip()
    pub     = str(row.get("Published Date", row.get("Date",""))).strip()[:16]
    source  = str(row.get("Source","")).strip()
    impl    = str(row.get("Implications","")).strip()
    actions = str(row.get("Action Items","")).strip()

    title_html = f'<a href="{url}" target="_blank" style="color:#1a1a1a;text-decoration:none;">{title}</a>' if url else title
    tags = ""
    if ta and ta not in ("-",""):  tags += f'<span class="tag tag-gold">{ta}</span>'
    if ha and ha not in ("-",""):  tags += f'<span class="tag">{ha}</span>'
    if show_source and source:     tags += f'<span class="tag">{source}</span>'

    st.markdown(f"""
    <div class="{card_border(pri)}">
      <div class="card-title">{title_html}</div>
      <div class="card-meta">{pub or "—"}</div>
      <div class="card-summary">{summary[:450] if summary else "No summary available."}</div>
      <div class="card-tags">{priority_badge(pri)}{tags}</div>
    </div>""", unsafe_allow_html=True)

    if impl or actions:
        with st.expander("Analysis details", key=f"exp_{idx}_{hash(title+pub)}"):
            if impl:    st.markdown(f"**Implications:** {impl}")
            if actions: st.markdown(f"**Action Items:** {actions}")

    col1, col2 = st.columns([6,1])
    with col2:
        already_saved = title in st.session_state.get("saved_favs", set())
        btn_label = "⭐ Saved" if already_saved else "☆ Save"
        if st.button(btn_label, key=f"fav_{idx}_{hash(title+pub)}", help="Save to Favorites", disabled=already_saved):
            # 1. Show instantly
            if "saved_favs" not in st.session_state:
                st.session_state["saved_favs"] = set()
            if "pending_favs" not in st.session_state:
                st.session_state["pending_favs"] = []
            st.session_state["saved_favs"].add(title)
            st.session_state["pending_favs"].append({
                "Title": title,
                "URL": url,
                "Source": source,
                "Published Date": pub,
                "Priority": pri,
                "Therapeutic Area": ta,
                "AI Summary": summary,
                "Saved At": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Deleted": "",
            })
            # 2. Write to Sheets in background
            try:
                gc = get_client()
                ws = gc.open(SHEET_NAME).worksheet("Favorites")
                ws.append_row([title, url, source, pub, pri, ta, summary,
                               datetime.now().strftime("%Y-%m-%d %H:%M"), ""])
            except Exception:
                pass

def filter_df(df, search="", ha_filter=None, ta_filter=None, pri_filter=None):
    if df.empty: return df
    if search:
        mask = df.apply(lambda r: search.lower() in " ".join(r.astype(str).values).lower(), axis=1)
        df = df[mask]
    if ha_filter:
        col = "Health Authority" if "Health Authority" in df.columns else "Source"
        if col in df.columns:
            df = df[df[col].fillna("").str.contains("|".join(ha_filter), case=False, na=False)]
    if ta_filter and "Therapeutic Area" in df.columns:
        df = df[df["Therapeutic Area"].fillna("").str.contains("|".join(ta_filter), case=False, na=False)]
    if pri_filter and "Priority" in df.columns:
        df = df[df["Priority"].fillna("").str.lower().isin([p.lower() for p in pri_filter])]
    return df

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:24px 0 28px 0;">
      <div style="font-family:'Playfair Display',serif;font-size:1.3rem;color:#f0ece4;">⚕ RIP</div>
      <div style="color:#444;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;margin-top:4px;">Regulatory Intelligence</div>
    </div>""", unsafe_allow_html=True)

    search_query      = st.text_input("Search", placeholder="keyword search…")
    st.divider()
    selected_priority = st.multiselect("Priority",         ["High","Medium","Low"], default=[])
    selected_ha       = st.multiselect("Health Authority", ["FDA","EMA","ICH"],     default=[])
    selected_ta       = st.multiselect("Therapeutic Area", ["Oncology","Gene Therapy","Cell Therapy","Rare Disease","Autoimmune"], default=[])
    st.divider()
    if st.button("↺  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(f'<div style="color:#333;font-size:9px;text-align:center;margin-top:12px;font-family:IBM Plex Mono,monospace;">updated {datetime.now().strftime("%H:%M")}</div>', unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="rip-header">
  <div>
    <div class="rip-logo">Regulatory<span>.</span>Intelligence</div>
    <div class="rip-tagline">Automated pharmaceutical surveillance platform</div>
  </div>
  <div class="rip-date">
    {date.today().strftime("%A, %B %d %Y")}<br>
    <span style="color:#c8a96e;">Live · Refreshes every 5 min</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
with st.spinner(""):
    df_updates     = load_tab("Updates")
    df_news        = load_tab("News")
    df_competitors = load_tab("Competitors")
    df_archive     = load_tab("Archive")

# ── PAGINATION HELPER ─────────────────────────────────────────────────────────
PAGE_SIZE = 10

def paginated(df, key, prefix):
    """Render df with Load More button. Returns nothing — renders directly."""
    if key not in st.session_state:
        st.session_state[key] = PAGE_SIZE
    n = st.session_state[key]
    subset = df.iloc[:n]
    for _i, (_idx, row) in enumerate(subset.iterrows()):
        render_card(row, idx=f"{prefix}{_i}")
    if n < len(df):
        remaining = len(df) - n
        if st.button(f"Load more  ({remaining} remaining)", key=f"btn_{key}"):
            st.session_state[key] += PAGE_SIZE
            st.rerun()

# ── METRICS ───────────────────────────────────────────────────────────────────
high_total = high_count(df_updates) + high_count(df_news)
high_class = "metric-num high" if high_total > 0 else "metric-num"

st.markdown(f"""
<div class="metric-strip">
  <div class="metric-cell"><div class="{high_class}">{high_total}</div><div class="metric-lbl">🚨 High Priority</div></div>
  <div class="metric-cell"><div class="metric-num">{len(df_updates)}</div><div class="metric-lbl">🏛 Regulatory</div></div>
  <div class="metric-cell"><div class="metric-num">{len(df_news)}</div><div class="metric-lbl">📰 News</div></div>
  <div class="metric-cell"><div class="metric-num">{len(df_competitors)}</div><div class="metric-lbl">🔎 Competitors</div></div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_home, tab_reg, tab_news_t, tab_comp, tab_search, tab_arc, tab_fav = st.tabs([
    "Home", "Regulatory", "News", "Competitors", "Search", "Archive", "⭐ Favorites"
])

# HOME
with tab_home:
    st.markdown('<div class="section-hdr">🚨 High Priority</div>', unsafe_allow_html=True)
    high_u   = df_updates[df_updates["Priority"].fillna("").str.strip().str.lower() == "high"] if not df_updates.empty and "Priority" in df_updates.columns else pd.DataFrame()
    high_n   = df_news[df_news["Priority"].fillna("").str.strip().str.lower() == "high"]       if not df_news.empty    and "Priority" in df_news.columns    else pd.DataFrame()
    high_all = pd.concat([high_u, high_n]).head(10)
    if high_all.empty:
        st.markdown('<div class="intel-card intel-card-na" style="color:#aaa;text-align:center;padding:32px;">No high priority items today.</div>', unsafe_allow_html=True)
    else:
        for _i, (_idx, row) in enumerate(high_all.iterrows()): render_card(row, idx=f"hall{_i}")

    st.markdown('<div class="section-hdr" style="margin-top:32px;">Latest Regulatory Updates</div>', unsafe_allow_html=True)
    for _i, (_idx, row) in enumerate(df_updates.head(5).iterrows()): render_card(row, idx=f"uhome{_i}")

    st.markdown('<div class="section-hdr" style="margin-top:32px;">Latest News</div>', unsafe_allow_html=True)
    for _i, (_idx, row) in enumerate(df_news.head(5).iterrows()): render_card(row, idx=f"nhome{_i}")

# REGULATORY
with tab_reg:
    st.markdown('<div class="section-hdr">Regulatory Updates — FDA / EMA / ICH</div>', unsafe_allow_html=True)
    df_f = filter_df(df_updates, search_query, selected_ha, selected_ta, selected_priority)
    st.markdown(f'<div class="item-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">No items match your filters.</div>', unsafe_allow_html=True)
    else:
        paginated(df_f, "page_reg", "reg")

# NEWS
with tab_news_t:
    st.markdown('<div class="section-hdr">Industry News & Publications</div>', unsafe_allow_html=True)
    df_f  = filter_df(df_news, search_query, selected_ha, selected_ta, selected_priority)
    st.markdown(f'<div class="item-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    group = st.toggle("Group by source", value=False)
    if df_f.empty:
        st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">No items match your filters.</div>', unsafe_allow_html=True)
    elif group and "Source" in df_f.columns:
        for src in df_f["Source"].unique():
            src_df = df_f[df_f["Source"] == src]
            with st.expander(f"{src} — {len(src_df)} items"):
                for _i, (_idx, row) in enumerate(src_df.iterrows()): render_card(row, show_source=False, idx=f"src{_i}")
    else:
        paginated(df_f, "page_news", "news")

# COMPETITORS
with tab_comp:
    st.markdown('<div class="section-hdr">Competitive Intelligence</div>', unsafe_allow_html=True)
    df_f = df_competitors.copy()
    if search_query and not df_f.empty:
        mask = df_f.apply(lambda r: search_query.lower() in " ".join(r.astype(str).values).lower(), axis=1)
        df_f = df_f[mask]
    st.markdown(f'<div class="item-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">No competitor intelligence available.</div>', unsafe_allow_html=True)
    else:
        if "page_comp" not in st.session_state: st.session_state["page_comp"] = PAGE_SIZE
        n = st.session_state["page_comp"]
        for _ci, (_, row) in enumerate(df_f.iloc[:n].iterrows()):
            title   = str(row.get("Title",   "")).strip() or "Untitled"
            url     = str(row.get("URL",     "")).strip()
            summary = str(row.get("Summary", "")).strip()
            company = str(row.get("Company", "")).strip()
            cat     = str(row.get("Category","")).strip()
            source  = str(row.get("Source",  "")).strip()
            dt      = str(row.get("Date", row.get("Run Date",""))).strip()[:16]
            notes   = str(row.get("Notes",   "")).strip()
            title_html = f'<a href="{url}" target="_blank" style="color:#1a1a1a;text-decoration:none;">{title}</a>' if url else title
            tags = ""
            if company: tags += f'<span class="tag tag-gold">{company}</span>'
            if cat:     tags += f'<span class="tag">{cat}</span>'
            if source:  tags += f'<span class="tag">{source}</span>'
            st.markdown(f"""
            <div class="intel-card intel-card-na">
              <div class="card-title">{title_html}</div>
              <div class="card-meta">{dt or "—"}</div>
              <div class="card-summary">{summary[:450] if summary else "No summary available."}</div>
              <div class="card-tags">{tags}</div>
            </div>""", unsafe_allow_html=True)
            if notes:
                with st.expander("Details", key=f"comp_exp_{_ci}"): st.markdown(notes)
        if n < len(df_f):
            remaining = len(df_f) - n
            if st.button(f"Load more  ({remaining} remaining)", key="btn_page_comp"):
                st.session_state["page_comp"] += PAGE_SIZE
                st.rerun()

# SEARCH
with tab_search:
    st.markdown('<div class="section-hdr">Search All Intelligence</div>', unsafe_allow_html=True)
    q = st.text_input("", placeholder="Search across all data…", key="search_main", label_visibility="collapsed")
    if q:
        r_u = filter_df(df_updates, q)
        r_n = filter_df(df_news,    q)
        r_c = filter_df(df_competitors, q)
        total = len(r_u) + len(r_n) + len(r_c)
        st.markdown(f'<div class="item-count">{total} results for <strong style="color:#1a1a1a">{q}</strong></div>', unsafe_allow_html=True)
        if not r_u.empty:
            st.markdown(f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#aaa;margin:20px 0 10px 0;">Regulatory ({len(r_u)})</div>', unsafe_allow_html=True)
            paginated(r_u, "page_sreg", "ru")
        if not r_n.empty:
            st.markdown(f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#aaa;margin:20px 0 10px 0;">News ({len(r_n)})</div>', unsafe_allow_html=True)
            paginated(r_n, "page_snews", "rn")
        if not r_c.empty:
            st.markdown(f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#aaa;margin:20px 0 10px 0;">Competitors ({len(r_c)})</div>', unsafe_allow_html=True)
            paginated(r_c, "page_scomp", "rc")
        if total == 0:
            st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">No results found.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#bbb;text-align:center;padding:48px;font-size:0.85rem;">Type above to search across all intelligence.</div>', unsafe_allow_html=True)

# FAVORITES
with tab_fav:
    st.markdown('<div class="section-hdr">⭐ Favorites</div>', unsafe_allow_html=True)

    if "removed_favs" not in st.session_state:
        st.session_state["removed_favs"] = set()
    if "saved_favs" not in st.session_state:
        st.session_state["saved_favs"] = set()
    if "pending_favs" not in st.session_state:
        st.session_state["pending_favs"] = []

    # Load from Sheets
    df_fav = load_tab("Favorites")

    # Merge pending (saved this session, not yet in Sheets cache)
    if st.session_state["pending_favs"]:
        df_pending = pd.DataFrame(st.session_state["pending_favs"])
        if df_fav.empty:
            df_fav = df_pending
        else:
            # Align columns before concat
            for col in df_pending.columns:
                if col not in df_fav.columns:
                    df_fav[col] = ""
            df_fav = pd.concat([df_fav, df_pending], ignore_index=True)

    # Filter removed and duplicates
    if not df_fav.empty and "Title" in df_fav.columns:
        df_fav = df_fav[~df_fav["Title"].isin(st.session_state["removed_favs"])]
        df_fav = df_fav.drop_duplicates(subset=["Title"], keep="last")

    if df_fav.empty:
        st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">No favorites yet. Click ☆ Save on any item to save it here.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="item-count">{len(df_fav)} saved items</div>', unsafe_allow_html=True)
        for _i, (_idx, row) in enumerate(df_fav.iloc[::-1].iterrows()):
            title   = str(row.get("Title","")).strip() or "Untitled"
            url     = str(row.get("URL","")).strip()
            summary = str(row.get("AI Summary", row.get("Summary",""))).strip()
            pri     = str(row.get("Priority","")).strip()
            ta      = str(row.get("Therapeutic Area","")).strip()
            pub     = str(row.get("Published Date", row.get("Saved At",""))).strip()[:16]
            source  = str(row.get("Source","")).strip()

            title_html = f'<a href="{url}" target="_blank" style="color:#1a1a1a;text-decoration:none;">{title}</a>' if url else title
            tags = ""
            if ta and ta not in ("-",""): tags += f'<span class="tag tag-gold">{ta}</span>'
            if source:                    tags += f'<span class="tag">{source}</span>'

            st.markdown(f"""
            <div class="{card_border(pri)}">
              <div class="card-title">{title_html}</div>
              <div class="card-meta">{pub or "—"}</div>
              <div class="card-summary">{summary[:450] if summary else "No summary available."}</div>
              <div class="card-tags">{priority_badge(pri)}{tags}</div>
            </div>""", unsafe_allow_html=True)

            if st.button("🗑 Remove", key=f"del_fav_{_i}", help="Remove from favorites"):
                st.session_state["removed_favs"].add(title)
                # Remove from pending too
                st.session_state["pending_favs"] = [
                    p for p in st.session_state["pending_favs"] if p.get("Title") != title
                ]
                st.session_state["saved_favs"].discard(title)
                try:
                    gc = get_client()
                    ws = gc.open("Raw Intelligence").worksheet("Favorites")
                    all_rows = ws.get_all_values()
                    for row_num, r in enumerate(all_rows[1:], start=2):
                        if r and r[0] == title:
                            ws.update_cell(row_num, 9, "deleted")
                            break
                except Exception:
                    pass
                st.rerun()

# ARCHIVE
with tab_arc:
    st.markdown('<div class="section-hdr">Archive</div>', unsafe_allow_html=True)
    arc_count = len(df_archive) if not df_archive.empty else 0
    st.markdown(f'<div class="archive-note">📦 {arc_count} items archived · Items older than 7 days are moved here automatically</div>', unsafe_allow_html=True)
    if df_archive.empty:
        st.markdown('<div class="intel-card" style="color:#aaa;text-align:center;padding:32px;">Archive is empty.</div>', unsafe_allow_html=True)
    else:
        arc_q = st.text_input("", placeholder="Search archive…", key="arc_search_input", label_visibility="collapsed")
        df_arc_f = filter_df(df_archive, arc_q)
        st.markdown(f'<div class="item-count">{len(df_arc_f)} items</div>', unsafe_allow_html=True)
        paginated(df_arc_f, "page_arc", "arc")
