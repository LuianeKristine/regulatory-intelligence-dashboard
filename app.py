import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
import threading

st.set_page_config(
    page_title="Regulatory Intelligence Platform",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&family=Geist:wght@300;400;500;600&display=swap');

  :root {
    --bg: #fafaf9;
    --surface: #ffffff;
    --surface-2: #f5f5f4;
    --border: #e7e5e4;
    --border-light: #f0efee;
    --text-primary: #1c1917;
    --text-secondary: #78716c;
    --text-muted: #a8a29e;
    --gold: #92400e;
    --gold-bg: #fef3c7;
    --gold-border: #fde68a;
    --high: #991b1b;
    --high-bg: #fef2f2;
    --high-border: #fecaca;
    --med: #92400e;
    --med-bg: #fffbeb;
    --med-border: #fde68a;
    --low: #166534;
    --low-bg: #f0fdf4;
    --low-border: #bbf7d0;
    --radius: 8px;
  }

  html, body, [class*="css"] {
    font-family: 'Geist', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
  }
  .main { background: var(--bg) !important; }
  .block-container { padding-top: 1.5rem !important; max-width: 1100px !important; }

  /* SIDEBAR */
  section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
  }
  section[data-testid="stSidebar"] * { color: var(--text-secondary) !important; }
  section[data-testid="stSidebar"] .stTextInput input {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-family: 'Geist', sans-serif !important;
    color: var(--text-primary) !important;
  }
  section[data-testid="stSidebar"] label {
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--text-muted) !important;
  }

  /* SIDEBAR LOGO */
  .rip-logo {
    font-family: 'Instrument Serif', serif;
    font-size: 1.15rem;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }
  .rip-sub {
    font-size: 10px;
    color: var(--text-muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: 2px;
  }

  /* TOPBAR */
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
  }
  .topbar-title {
    font-family: 'Instrument Serif', serif;
    font-size: 1.05rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }
  .topbar-date {
    font-family: 'Geist Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    display: flex; align-items: center; gap: 8px;
  }
  .live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 0 2px rgba(34,197,94,0.2);
  }

  /* METRICS */
  .metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 32px;
  }
  .metric {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
  }
  .metric-num {
    font-family: 'Instrument Serif', serif;
    font-size: 2rem;
    line-height: 1;
    color: var(--text-primary);
    margin-bottom: 4px;
  }
  .metric-num.alert { color: var(--high); }
  .metric-label {
    font-size: 11px;
    color: var(--text-muted);
    font-weight: 500;
    letter-spacing: 0.04em;
  }

  /* SECTION HEADER */
  .section-hdr {
    font-family: 'Instrument Serif', serif;
    font-size: 1.05rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    margin-bottom: 14px;
    margin-top: 32px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  .section-hdr:first-child { margin-top: 0; }
  .item-count {
    font-family: 'Geist Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 14px;
  }

  /* CARDS */
  .intel-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 6px;
    transition: border-color 0.15s, box-shadow 0.15s;
    position: relative;
    overflow: hidden;
  }
  .intel-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
  }
  .intel-card:hover { border-color: #d4d0cc; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
  .intel-card-high::before   { background: var(--high); }
  .intel-card-medium::before { background: #d97706; }
  .intel-card-low::before    { background: #16a34a; }
  .intel-card-na::before     { background: var(--border); }

  .card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
  .card-title  { font-size: 13.5px; font-weight: 500; color: var(--text-primary); line-height: 1.45; text-decoration: none; }
  .card-title a { color: var(--text-primary); text-decoration: none; }
  .card-title a:hover { color: #2563eb; }
  .card-date   { font-family: 'Geist Mono', monospace; font-size: 10px; color: var(--text-muted); white-space: nowrap; flex-shrink: 0; padding-top: 2px; }
  .card-summary { font-size: 12.5px; color: var(--text-secondary); line-height: 1.65; margin-bottom: 12px; }
  .card-tags   { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }

  /* TAGS & BADGES */
  .tag {
    font-family: 'Geist Mono', monospace;
    font-size: 10px; font-weight: 500;
    padding: 2px 7px; border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--surface-2);
    color: var(--text-secondary);
    letter-spacing: 0.02em;
  }
  .tag-gold { background: var(--gold-bg); color: var(--gold); border-color: var(--gold-border); }
  .badge-high   { background: var(--high-bg); color: var(--high); border: 1px solid var(--high-border); padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: 'Geist Mono', monospace; }
  .badge-medium { background: var(--med-bg);  color: var(--med);  border: 1px solid var(--med-border);  padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: 'Geist Mono', monospace; }
  .badge-low    { background: var(--low-bg);  color: var(--low);  border: 1px solid var(--low-border);  padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: 'Geist Mono', monospace; }
  .badge-na     { background: var(--surface-2); color: var(--text-muted); border: 1px solid var(--border); padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: 'Geist Mono', monospace; }

  /* TABS */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important; padding: 0 !important;
  }
  .stTabs [data-baseweb="tab"] {
    color: var(--text-muted) !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    padding: 10px 16px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
  }
  .stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--text-primary) !important;
    background: transparent !important;
    font-weight: 500 !important;
  }

  /* BUTTONS */
  .stButton button {
    background: var(--surface) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 12px !important;
    padding: 4px 12px !important;
    transition: all 0.1s !important;
  }
  .stButton button:hover {
    background: var(--surface-2) !important;
    color: var(--text-primary) !important;
    border-color: var(--text-muted) !important;
  }

  /* TEXT INPUT */
  .stTextInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 13px !important;
    color: var(--text-primary) !important;
    padding: 9px 14px !important;
  }
  .stTextInput input::placeholder { color: var(--text-muted) !important; }
  .stTextInput input:focus { border-color: var(--text-muted) !important; }

  /* EXPANDER */
  details {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    margin-top: 4px !important;
  }
  summary { font-size: 11px !important; color: var(--text-muted) !important; padding: 6px 12px !important; }

  /* ARCHIVE NOTE */
  .archive-note {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 14px;
    font-family: 'Geist Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 20px;
  }

  /* EMPTY STATE */
  .empty-state {
    text-align: center;
    padding: 48px 32px;
    color: var(--text-muted);
    font-size: 13px;
    background: var(--surface);
    border: 1px dashed var(--border);
    border-radius: var(--radius);
  }

  /* HOME 3-COLUMN GRID */
  .home-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    align-items: start;
  }
  .home-col {}
  .home-col-hdr {
    font-family: 'Instrument Serif', serif;
    font-size: 1rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  /* MOBILE RESPONSIVE */
  @media (max-width: 768px) {
    .home-grid { grid-template-columns: 1fr; }
    .block-container { padding: 1rem !important; }
    .topbar { padding: 0 0 16px 0; }
    .content { padding: 16px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 10px !important; font-size: 12px !important; }
  }
  @media (max-width: 480px) {
    .stTabs [data-baseweb="tab"] { padding: 6px 8px !important; font-size: 11px !important; }
  }

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

    title_html = f'<a href="{url}" target="_blank" class="card-title">{title}</a>' if url else f'<span class="card-title">{title}</span>'
    tags = ""
    if ta and ta not in ("-",""):  tags += f'<span class="tag tag-gold">{ta}</span>'
    if ha and ha not in ("-",""):  tags += f'<span class="tag">{ha}</span>'
    if show_source and source:     tags += f'<span class="tag">{source}</span>'

    st.markdown(f"""
    <div class="{card_border(pri)}">
      <div class="card-header">
        <div class="card-title">{title_html}</div>
        <span class="card-date">{pub or "—"}</span>
      </div>
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
            from datetime import timezone, timedelta
            BR_TZ = timezone(timedelta(hours=-3))
            saved_at = datetime.now(BR_TZ).strftime("%Y-%m-%d %H:%M")
            st.session_state["saved_favs"].add(title)
            st.session_state["pending_favs"].append({
                "Title": title,
                "URL": url,
                "Source": source,
                "Published Date": pub,
                "Priority": pri,
                "Therapeutic Area": ta,
                "AI Summary": summary,
                "Saved At": saved_at,
                "Deleted": "",
            })
            # Write to Sheets in background thread — never blocks rerun
            def _write(t, u, s, p, pr, ta_, sm, dt, sheet_name, secrets):
                try:
                    creds = Credentials.from_service_account_info(secrets, scopes=[
                        "https://spreadsheets.google.com/feeds",
                        "https://www.googleapis.com/auth/drive",
                    ])
                    gc2 = gspread.authorize(creds)
                    ws2 = gc2.open(sheet_name).worksheet("Favorites")
                    ws2.append_row([t, u, s, p, pr, ta_, sm, dt, ""])
                except Exception:
                    pass
            threading.Thread(
                target=_write,
                args=(title, url, source, pub, pri, ta, summary,
                      saved_at,
                      SHEET_NAME, dict(st.secrets["gcp_service_account"])),
                daemon=True
            ).start()
            st.rerun()

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
    <div style="padding:4px 0 20px 0;border-bottom:1px solid var(--border-light);margin-bottom:16px;">
      <div class="rip-logo">RIP</div>
      <div class="rip-sub">Regulatory Intelligence</div>
    </div>""", unsafe_allow_html=True)

    search_query      = st.text_input("", placeholder="Filter…", label_visibility="collapsed")
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    selected_priority = st.multiselect("Priority",         ["High","Medium","Low"], default=[])
    selected_ha       = st.multiselect("Health Authority", ["FDA","EMA","ICH"],     default=[])
    selected_ta       = st.multiselect("Therapeutic Area", ["Oncology","Gene Therapy","Cell Therapy","Rare Disease","Autoimmune"], default=[])
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button("↺  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    from datetime import timezone, timedelta as _td
    _br = datetime.now(timezone(_td(hours=-3))).strftime("%H:%M")
    st.markdown(f'<div style="font-family:Geist Mono,monospace;font-size:10px;color:var(--text-muted);text-align:center;margin-top:8px;">updated {_br}</div>', unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
  <div class="topbar-title">Regulatory Intelligence Platform</div>
  <div class="topbar-date">
    <span class="live-dot"></span>
    {date.today().strftime("%a, %b %d %Y")}
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

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_home, tab_reg, tab_news_t, tab_comp, tab_search, tab_arc, tab_fav = st.tabs([
    "Home", "Regulatory", "News", "Competitors", "Search", "Archive", "⭐ Favorites"
])

# HOME
with tab_home:
    high_u   = df_updates[df_updates["Priority"].fillna("").str.strip().str.lower() == "high"] if not df_updates.empty and "Priority" in df_updates.columns else pd.DataFrame()
    high_n   = df_news[df_news["Priority"].fillna("").str.strip().str.lower() == "high"]       if not df_news.empty    and "Priority" in df_news.columns    else pd.DataFrame()
    high_all = pd.concat([high_u, high_n]).head(5)

    def home_card(row, idx):
        title   = str(row.get("Title","")).strip() or "Untitled"
        url     = str(row.get("URL","")).strip()
        summary = str(row.get("AI Summary", row.get("Summary",""))).strip()
        pri     = str(row.get("Priority","")).strip()
        pub     = str(row.get("Published Date", row.get("Date",""))).strip()[:16]
        ta      = str(row.get("Therapeutic Area","")).strip()
        title_html = f'<a href="{url}" target="_blank" class="card-title">{title}</a>' if url else f'<span class="card-title">{title}</span>'
        tags = priority_badge(pri)
        if ta and ta not in ("-",""): tags += f' <span class="tag tag-gold">{ta}</span>'
        return f"""
        <div class="{card_border(pri)}" style="margin-bottom:6px;">
          <div class="card-header">
            <div class="card-title">{title_html}</div>
            <span class="card-date">{pub or "—"}</span>
          </div>
          <div class="card-summary" style="font-size:12px;">{summary[:200] if summary else "No summary."}</div>
          <div class="card-tags">{tags}</div>
        </div>"""

    # Build columns HTML
    col_high = "".join(home_card(r, f"hh{i}") for i, (_, r) in enumerate(high_all.iterrows())) if not high_all.empty else '<div class="empty-state" style="padding:24px;">No high priority items.</div>'
    col_reg  = "".join(home_card(r, f"hr{i}") for i, (_, r) in enumerate(df_updates.head(5).iterrows())) if not df_updates.empty else '<div class="empty-state" style="padding:24px;">No items.</div>'
    col_news = "".join(home_card(r, f"hn{i}") for i, (_, r) in enumerate(df_news.head(5).iterrows())) if not df_news.empty else '<div class="empty-state" style="padding:24px;">No items.</div>'

    st.markdown(f"""
    <div class="home-grid">
      <div class="home-col">
        <div class="home-col-hdr">🚨 High Priority</div>
        {col_high}
      </div>
      <div class="home-col">
        <div class="home-col-hdr">Regulatory Updates</div>
        {col_reg}
      </div>
      <div class="home-col">
        <div class="home-col-hdr">Latest News</div>
        {col_news}
      </div>
    </div>
    """, unsafe_allow_html=True)

# REGULATORY
with tab_reg:
    st.markdown('<div class="section-hdr">Regulatory Updates — FDA / EMA / ICH</div>', unsafe_allow_html=True)
    df_f = filter_df(df_updates, search_query, selected_ha, selected_ta, selected_priority)
    st.markdown(f'<div class="item-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="intel-card" class="empty-state">No items match your filters.</div>', unsafe_allow_html=True)
    else:
        paginated(df_f, "page_reg", "reg")

# NEWS
with tab_news_t:
    st.markdown('<div class="section-hdr">Industry News & Publications</div>', unsafe_allow_html=True)
    df_f  = filter_df(df_news, search_query, selected_ha, selected_ta, selected_priority)
    st.markdown(f'<div class="item-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    group = st.toggle("Group by source", value=False)
    if df_f.empty:
        st.markdown('<div class="intel-card" class="empty-state">No items match your filters.</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="intel-card" class="empty-state">No competitor intelligence available.</div>', unsafe_allow_html=True)
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
            title_html = f'<a href="{url}" target="_blank" class="card-title">{title}</a>' if url else f'<span class="card-title">{title}</span>'
            tags = ""
            if company: tags += f'<span class="tag tag-gold">{company}</span>'
            if cat:     tags += f'<span class="tag">{cat}</span>'
            if source:  tags += f'<span class="tag">{source}</span>'
            st.markdown(f"""
            <div class="intel-card intel-card-na">
              <div class="card-title">{title_html}</div>
              <div class="card-date">{dt or "—"}</div>
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

    # Init session state
    if "removed_favs"  not in st.session_state: st.session_state["removed_favs"]  = set()
    if "saved_favs"    not in st.session_state: st.session_state["saved_favs"]    = set()
    if "pending_favs"  not in st.session_state: st.session_state["pending_favs"]  = []

    # Load from Sheets (cached)
    df_fav = load_tab("Favorites")

    # Remove deleted items (sheet may lag behind)
    if not df_fav.empty and "Title" in df_fav.columns:
        df_fav = df_fav[~df_fav["Title"].isin(st.session_state["removed_favs"])]

    # Add newly saved items that aren't in cache yet
    if st.session_state["pending_favs"]:
        existing_titles = set(df_fav["Title"].tolist()) if not df_fav.empty else set()
        new_rows = [p for p in st.session_state["pending_favs"] if p["Title"] not in existing_titles]
        if new_rows:
            df_new = pd.DataFrame(new_rows)
            df_fav = pd.concat([df_fav, df_new], ignore_index=True) if not df_fav.empty else df_new

    if df_fav.empty:
        st.markdown('<div class="empty-state">No favorites yet. Click ☆ Save on any item to save it here.</div>', unsafe_allow_html=True)
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

            title_html = f'<a href="{url}" target="_blank" class="card-title">{title}</a>' if url else f'<span class="card-title">{title}</span>'
            tags = ""
            if ta and ta not in ("-",""): tags += f'<span class="tag tag-gold">{ta}</span>'
            if source:                    tags += f'<span class="tag">{source}</span>'

            st.markdown(f"""
            <div class="{card_border(pri)}">
              <div class="card-header">
                <div class="card-title">{title_html}</div>
                <span class="card-date">{pub or "—"}</span>
              </div>
              <div class="card-summary">{summary[:450] if summary else "No summary available."}</div>
              <div class="card-tags">{priority_badge(pri)}{tags}</div>
            </div>""", unsafe_allow_html=True)

            if st.button("🗑 Remove", key=f"del_fav_{_i}", help="Remove from favorites"):
                # Remove from screen instantly
                st.session_state["removed_favs"].add(title)
                st.session_state["saved_favs"].discard(title)
                st.session_state["pending_favs"] = [p for p in st.session_state["pending_favs"] if p.get("Title") != title]
                # Delete row from Sheets in background (real delete)
                def _delete(t, sheet_name, secrets):
                    try:
                        creds = Credentials.from_service_account_info(secrets, scopes=[
                            "https://spreadsheets.google.com/feeds",
                            "https://www.googleapis.com/auth/drive",
                        ])
                        gc2 = gspread.authorize(creds)
                        ws2 = gc2.open(sheet_name).worksheet("Favorites")
                        all_rows = ws2.get_all_values()
                        for row_num, r in enumerate(all_rows[1:], start=2):
                            if r and r[0] == t:
                                ws2.delete_rows(row_num)
                                break
                    except Exception:
                        pass
                threading.Thread(
                    target=_delete,
                    args=(title, SHEET_NAME, dict(st.secrets["gcp_service_account"])),
                    daemon=True
                ).start()
                st.rerun()  # session_state["removed_favs"] already hides it instantly

# ARCHIVE
with tab_arc:
    st.markdown('<div class="section-hdr">Archive</div>', unsafe_allow_html=True)
    arc_count = len(df_archive) if not df_archive.empty else 0
    st.markdown(f'<div class="archive-note">📦 {arc_count} items archived · Items older than 7 days are moved here automatically</div>', unsafe_allow_html=True)
    if df_archive.empty:
        st.markdown('<div class="intel-card" class="empty-state">Archive is empty.</div>', unsafe_allow_html=True)
    else:
        arc_q = st.text_input("", placeholder="Search archive…", key="arc_search_input", label_visibility="collapsed")
        df_arc_f = filter_df(df_archive, arc_q)
        st.markdown(f'<div class="item-count">{len(df_arc_f)} items</div>', unsafe_allow_html=True)
        paginated(df_arc_f, "page_arc", "arc")
