import streamlit as st
import pandas as pd
import re
from datetime import datetime, date, timezone, timedelta
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #f8f8f7;
  --surface: #ffffff;
  --surface-2: #f3f3f2;
  --border: #e4e4e2;
  --text-1: #1a1a18;
  --text-2: #6b6b66;
  --text-3: #a3a39e;
  --gold: #92400e;
  --gold-bg: #fef3c7;
  --gold-bd: #fde68a;
  --high: #991b1b;
  --high-bg: #fef2f2;
  --high-bd: #fecaca;
  --med: #92400e;
  --med-bg: #fffbeb;
  --med-bd: #fde68a;
  --low: #166534;
  --low-bg: #f0fdf4;
  --low-bd: #bbf7d0;
  --r: 7px;
}
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
  background: var(--bg) !important;
  color: var(--text-1) !important;
  -webkit-font-smoothing: antialiased;
}
.main { background: var(--bg) !important; }
.block-container { padding: 1.2rem 1.5rem !important; max-width: 1080px !important; }

section[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
  font-family: 'Inter', sans-serif !important;
  color: var(--text-1) !important;
}
section[data-testid="stSidebar"] label {
  font-size: 10px !important; font-weight: 600 !important;
  text-transform: uppercase !important; letter-spacing: .1em !important;
  color: var(--text-3) !important;
}
section[data-testid="stSidebar"] .stTextInput input {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--text-1) !important;
}
section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  background: var(--surface-2) !important;
  border-color: var(--border) !important;
  border-radius: var(--r) !important;
}
section[data-testid="stSidebar"] .stButton > button {
  font-family: 'Inter', sans-serif !important;
}

.topbar { display:flex; align-items:center; justify-content:space-between; padding-bottom:16px; border-bottom:1px solid var(--border); margin-bottom:22px; }
.topbar-title { font-size:1rem; font-weight:600; color:var(--text-1); letter-spacing:-.02em; }
.topbar-meta { font-family:'JetBrains Mono',monospace; font-size:10.5px; color:var(--text-3); display:flex; align-items:center; gap:7px; }
.live { width:6px; height:6px; border-radius:50%; background:#22c55e; display:inline-block; box-shadow:0 0 0 2px rgba(34,197,94,.18); }

.sec-hdr { font-size:13px; font-weight:600; color:var(--text-1); margin:0 0 4px; }
.sec-count { font-family:'JetBrains Mono',monospace; font-size:10.5px; color:var(--text-3); margin-bottom:12px; }

.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--r); padding:14px 16px; margin-bottom:5px; position:relative; overflow:hidden; }
.card::before { content:''; position:absolute; left:0;top:0;bottom:0; width:3px; background:var(--border); }
.card-high::before   { background:var(--high); }
.card-medium::before { background:#d97706; }
.card-low::before    { background:#16a34a; }
.card-na::before     { background:var(--border); }
.card-hdr { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:5px; }
.card-ttl { font-size:13px; font-weight:500; color:var(--text-1); line-height:1.45; }
.card-ttl a { color:var(--text-1); text-decoration:none; }
.card-ttl a:hover { color:#2563eb; }
.card-dt  { font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--text-3); white-space:nowrap; flex-shrink:0; padding-top:1px; }
.card-sum { font-size:12px; color:var(--text-2); line-height:1.6; margin-bottom:10px; }
.card-tags { display:flex; flex-wrap:wrap; gap:3px; }

.tag { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:500; padding:2px 6px; border-radius:4px; border:1px solid var(--border); background:var(--surface-2); color:var(--text-2); }
.tag-gold { background:var(--gold-bg); color:var(--gold); border-color:var(--gold-bd); }
.badge-high { background:var(--high-bg); color:var(--high); border:1px solid var(--high-bd); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }
.badge-med  { background:var(--med-bg);  color:var(--med);  border:1px solid var(--med-bd);  padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }
.badge-low  { background:var(--low-bg);  color:var(--low);  border:1px solid var(--low-bd);  padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }

.hgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; align-items:start; width:100%; overflow:hidden; }
.hcol  { min-width:0; overflow:hidden; }
.hcol-hdr { font-size:12px; font-weight:600; color:var(--text-1); padding-bottom:8px; border-bottom:1px solid var(--border); margin-bottom:10px; }
.hcol-scroll { max-height:560px; overflow-y:auto; overflow-x:hidden; scrollbar-width:thin; scrollbar-color:var(--border) transparent; }
.hcol-scroll::-webkit-scrollbar { width:3px; }
.hcol-scroll::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

.hcard { background:var(--surface); border:1px solid var(--border); border-radius:var(--r); padding:11px 13px; margin-bottom:5px; position:relative; overflow:hidden; }
.hcard::before { content:''; position:absolute; left:0;top:0;bottom:0; width:3px; background:var(--border); }
.hcard-high::before   { background:var(--high); }
.hcard-medium::before { background:#d97706; }
.hcard-low::before    { background:#16a34a; }
.hcard-na::before     { background:var(--border); }
.hcard-ttl { font-size:12px; font-weight:500; color:var(--text-1); line-height:1.4; margin-bottom:5px; word-break:break-word; overflow:hidden; }
.hcard-ttl a { color:var(--text-1); text-decoration:none; }
.hcard-ttl a:hover { color:#2563eb; }
.hcard-sum { font-size:11px; color:var(--text-2); line-height:1.55; margin-bottom:8px; word-break:break-word; overflow:hidden; }
.hcard-foot { display:flex; flex-wrap:wrap; gap:3px; align-items:center; }
.hcard-dt { font-family:'JetBrains Mono',monospace; font-size:9.5px; color:var(--text-3); margin-right:4px; }

.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid var(--border) !important; gap:0 !important; padding:0 !important; }
.stTabs [data-baseweb="tab"] { color:var(--text-3) !important; font-family:'Inter',sans-serif !important; font-size:12.5px !important; font-weight:400 !important; padding:9px 14px !important; border-radius:0 !important; border-bottom:2px solid transparent !important; margin-bottom:-1px !important; }
.stTabs [aria-selected="true"] { color:var(--text-1) !important; border-bottom:2px solid var(--text-1) !important; background:transparent !important; font-weight:600 !important; }

.stButton > button { background:var(--surface) !important; color:var(--text-2) !important; border:1px solid var(--border) !important; border-radius:5px !important; font-family:'Inter',sans-serif !important; font-size:11px !important; padding:3px 10px !important; height:auto !important; line-height:1.6 !important; transition:all .1s !important; }
.stButton > button:hover { background:var(--surface-2) !important; color:var(--text-1) !important; border-color:var(--text-3) !important; }

.stTextInput input { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--r) !important; font-family:'Inter',sans-serif !important; font-size:13px !important; color:var(--text-1) !important; }
.stTextInput input::placeholder { color:var(--text-3) !important; }

details { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:5px !important; margin-top:3px !important; }
details summary { font-size:11px !important; color:var(--text-3) !important; cursor:pointer; }

.empty { text-align:center; padding:36px 24px; color:var(--text-3); font-size:12.5px; background:var(--surface); border:1px dashed var(--border); border-radius:var(--r); }
.arc-note { background:var(--surface); border:1px solid var(--border); border-radius:var(--r); padding:9px 13px; font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--text-3); margin-bottom:16px; }

#MainMenu, footer, header { visibility:hidden; }

/* hide sidebar collapse button icon text */
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[kind="header"] { display:none !important; }
section[data-testid="stSidebar"] > div:first-child > div:first-child button {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────
SHEET_NAME = "Raw Intelligence"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ── DATA ──────────────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_tab(tab_name):
    try:
        gc = get_client()
        ws = gc.open(SHEET_NAME).worksheet(tab_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame()
        if tab_name == "Favorites" and not df.empty and "Deleted" in df.columns:
            df = df[df["Deleted"].fillna("") != "deleted"]
        return df
    except Exception as e:
        st.error(f"Could not load '{tab_name}': {e}")
        return pd.DataFrame()

# ── HELPERS ───────────────────────────────────────────────────
def clean(text, max_len=400):
    t = str(text or "")
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'!\[.*?\]\(.*?\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    t = re.sub(r'[#*_`>~]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return (t[:max_len] + "…") if len(t) > max_len else t

def pclass(p):
    p = str(p).strip().lower()
    return p if p in ("high","medium","low") else "na"

def pbadge(p):
    pc = pclass(p)
    if pc == "high":   return '<span class="badge-high">HIGH</span>'
    if pc == "medium": return '<span class="badge-med">MED</span>'
    if pc == "low":    return '<span class="badge-low">LOW</span>'
    return ""

def build_tags(row):
    ta  = clean(row.get("Therapeutic Area", ""), 60)
    ha  = clean(row.get("Health Authority",  ""), 60)
    src = clean(row.get("Source",            ""), 60)
    pri = str(row.get("Priority", "")).strip()
    out = pbadge(pri)
    if ta  and ta  not in ("-",): out += f' <span class="tag tag-gold">{ta}</span>'
    if ha  and ha  not in ("-",) and ha != src: out += f' <span class="tag">{ha}</span>'
    if src and src not in ("-",): out += f' <span class="tag">{src}</span>'
    return out

def filter_df(df, search="", ha_f=None, ta_f=None, pri_f=None):
    if df.empty: return df
    if search:
        q = search.lower()
        df = df[df.apply(lambda r: q in " ".join(r.astype(str).values).lower(), axis=1)]
    if ha_f:
        col = "Health Authority" if "Health Authority" in df.columns else "Source"
        if col in df.columns:
            df = df[df[col].fillna("").str.contains("|".join(ha_f), case=False)]
    if ta_f and "Therapeutic Area" in df.columns:
        df = df[df["Therapeutic Area"].fillna("").str.contains("|".join(ta_f), case=False)]
    if pri_f and "Priority" in df.columns:
        df = df[df["Priority"].fillna("").str.lower().isin([p.lower() for p in pri_f])]
    return df

def render_card(row, key, show_save=True):
    title   = clean(row.get("Title",   ""), 200) or "Untitled"
    url     = str(row.get("URL", "")).strip()
    summary = clean(row.get("AI Summary", row.get("Summary", "")), 400)
    pri     = str(row.get("Priority", "")).strip()
    pub     = clean(row.get("Published Date", row.get("Date", "")), 16)
    src     = clean(row.get("Source", ""), 60)
    ta      = clean(row.get("Therapeutic Area", ""), 60)
    impl    = clean(row.get("Implications", ""), 600)
    actions = clean(row.get("Action Items",  ""), 600)

    pc  = pclass(pri)
    ttl = f'<a href="{url}" target="_blank">{title}</a>' if url else title
    tags = build_tags(row)

    st.markdown(f"""
    <div class="card card-{pc}">
      <div class="card-hdr">
        <div class="card-ttl">{ttl}</div>
        <span class="card-dt">{pub or "—"}</span>
      </div>
      <div class="card-sum">{summary or "No summary available."}</div>
      <div class="card-tags">{tags}</div>
    </div>""", unsafe_allow_html=True)

    if impl or actions:
        with st.expander("Analysis"):
            if impl:    st.write(f"**Implications:** {impl}")
            if actions: st.write(f"**Actions:** {actions}")

    if show_save:
        already = title in st.session_state.get("saved_favs", set())
        if st.button("⭐ Saved" if already else "☆ Save", key=f"sav_{key}", disabled=already):
            st.session_state.setdefault("saved_favs",   set()).add(title)
            st.session_state.setdefault("pending_favs", []).append({
                "Title": title, "URL": url, "Source": src,
                "Published Date": pub, "Priority": pri,
                "Therapeutic Area": ta, "AI Summary": summary,
                "Saved At": datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
                "Deleted": "",
            })
            def _write(t, u, s, p, pr, ta_, sm, dt, sname, sec):
                try:
                    c2 = Credentials.from_service_account_info(sec, scopes=SCOPES)
                    gspread.authorize(c2).open(sname).worksheet("Favorites").append_row(
                        [t, u, s, p, pr, ta_, sm, dt, ""])
                except Exception: pass
            threading.Thread(target=_write, args=(
                title, url, src, pub, pri, ta, summary,
                datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
                SHEET_NAME, dict(st.secrets["gcp_service_account"])), daemon=True).start()
            st.rerun()

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style="padding:2px 0 18px;border-bottom:1px solid #eee;margin-bottom:14px;">
      <div style="font-size:1rem;font-weight:700;letter-spacing:-.02em;font-family:'Inter',sans-serif;">RI</div>
      <div style="font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.1em;margin-top:2px;font-family:'Inter',sans-serif;">Regulatory Intelligence</div>
    </div>""", unsafe_allow_html=True)
    search_q = st.text_input("", placeholder="Filter…", label_visibility="collapsed")
    sel_pri  = st.multiselect("Priority",         ["High","Medium","Low"])
    sel_ha   = st.multiselect("Health Authority", ["FDA","EMA","ICH"])
    sel_ta   = st.multiselect("Therapeutic Area", ["Oncology","Gene Therapy","Cell Therapy","Rare Disease","Autoimmune"])
    if st.button("↺  Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    _t = datetime.now(timezone(timedelta(hours=-3))).strftime("%H:%M")
    st.markdown(f'<div style="font-size:10px;color:#bbb;text-align:center;margin-top:8px;font-family:JetBrains Mono,monospace;">updated {_t}</div>', unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown(f"""<div class="topbar">
  <div class="topbar-title">Regulatory Intelligence Platform</div>
  <div class="topbar-meta"><span class="live"></span>{date.today().strftime("%a, %b %d %Y")}</div>
</div>""", unsafe_allow_html=True)

# ── LOAD ──────────────────────────────────────────────────────
with st.spinner("Loading…"):
    df_upd  = load_tab("Updates")
    df_news = load_tab("News")
    df_comp = load_tab("Competitors")
    df_arc  = load_tab("Archive")

tab_home, tab_reg, tab_nws, tab_cmp, tab_srch, tab_arc_t, tab_fav = st.tabs([
    "Home", "Regulatory", "News", "Competitors", "Search", "Archive", "⭐ Favorites"
])

# ══════════════════════════════════════════════════════════════
# HOME — pure HTML, no Streamlit widgets
# ══════════════════════════════════════════════════════════════
with tab_home:
    def hcard(row):
        title   = clean(row.get("Title", ""), 150) or "Untitled"
        url     = str(row.get("URL", "")).strip()
        summary = clean(row.get("AI Summary", row.get("Summary", "")), 150)
        pri     = str(row.get("Priority", "")).strip()
        pub     = clean(row.get("Published Date", row.get("Date", "")), 16)
        ta      = clean(row.get("Therapeutic Area", ""), 60)
        ha      = clean(row.get("Health Authority", row.get("Source", "")), 60)
        src     = clean(row.get("Source", ""), 60)
        pc      = pclass(pri)
        ttl     = f'<a href="{url}" target="_blank">{title}</a>' if url else title
        tags = pbadge(pri)
        if ta  and ta  not in ("-",):            tags += f' <span class="tag tag-gold">{ta}</span>'
        if ha  and ha  not in ("-",) and ha!=src: tags += f' <span class="tag">{ha}</span>'
        if src and src not in ("-",):            tags += f' <span class="tag">{src}</span>'
        return f"""<div class="hcard hcard-{pc}">
  <div class="hcard-ttl">{ttl}</div>
  <div class="hcard-sum">{summary}</div>
  <div class="hcard-foot"><span class="hcard-dt">{pub}</span>{tags}</div>
</div>"""

    def col_html(df_):
        if df_ is None or df_.empty:
            return '<div class="empty" style="padding:14px;font-size:11px;">No items.</div>'
        return "".join(hcard(r) for _, r in df_.iterrows())

    high_parts = []
    for df_ in [df_upd, df_news]:
        if not df_.empty and "Priority" in df_.columns:
            high_parts.append(df_[df_["Priority"].fillna("").str.strip().str.lower()=="high"])
    df_high = pd.concat(high_parts) if high_parts else pd.DataFrame()

    st.markdown(f"""<div class="hgrid">
  <div class="hcol">
    <div class="hcol-hdr">🚨 High Priority</div>
    <div class="hcol-scroll">{col_html(df_high)}</div>
  </div>
  <div class="hcol">
    <div class="hcol-hdr">Regulatory Updates</div>
    <div class="hcol-scroll">{col_html(df_upd)}</div>
  </div>
  <div class="hcol">
    <div class="hcol-hdr">Latest News</div>
    <div class="hcol-scroll">{col_html(df_news)}</div>
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# REGULATORY
# ══════════════════════════════════════════════════════════════
with tab_reg:
    st.markdown('<div class="sec-hdr">Regulatory Updates</div>', unsafe_allow_html=True)
    df_f = filter_df(df_upd, search_q, sel_ha, sel_ta, sel_pri)
    st.markdown(f'<div class="sec-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="empty">No items match your filters.</div>', unsafe_allow_html=True)
    else:
        for i, (_, row) in enumerate(df_f.iterrows()):
            render_card(row, key=f"reg{i}")

# ══════════════════════════════════════════════════════════════
# NEWS
# ══════════════════════════════════════════════════════════════
with tab_nws:
    st.markdown('<div class="sec-hdr">Industry News & Publications</div>', unsafe_allow_html=True)
    df_f = filter_df(df_news, search_q, sel_ha, sel_ta, sel_pri)
    st.markdown(f'<div class="sec-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    group = st.toggle("Group by source", value=False)
    if df_f.empty:
        st.markdown('<div class="empty">No items match your filters.</div>', unsafe_allow_html=True)
    elif group and "Source" in df_f.columns:
        for src in df_f["Source"].unique():
            sdf = df_f[df_f["Source"]==src]
            with st.expander(f"{src} — {len(sdf)} items"):
                for i, (_, row) in enumerate(sdf.iterrows()):
                    render_card(row, key=f"nsrc{hash(src)}{i}", show_save=True)
    else:
        for i, (_, row) in enumerate(df_f.iterrows()):
            render_card(row, key=f"nws{i}")

# ══════════════════════════════════════════════════════════════
# COMPETITORS
# ══════════════════════════════════════════════════════════════
with tab_cmp:
    st.markdown('<div class="sec-hdr">Competitive Intelligence</div>', unsafe_allow_html=True)
    df_f = df_comp.copy()
    if search_q and not df_f.empty:
        q = search_q.lower()
        df_f = df_f[df_f.apply(lambda r: q in " ".join(r.astype(str).values).lower(), axis=1)]
    st.markdown(f'<div class="sec-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="empty">No competitor intelligence available.</div>', unsafe_allow_html=True)
    else:
        for i, (_, row) in enumerate(df_f.iterrows()):
            title   = clean(row.get("Title",    ""), 200) or "Untitled"
            url     = str(row.get("URL",        "")).strip()
            summary = clean(row.get("Summary",  ""), 400)
            company = clean(row.get("Company",  ""), 60)
            cat     = clean(row.get("Category", ""), 60)
            src     = clean(row.get("Source",   ""), 60)
            dt      = clean(row.get("Date", row.get("Run Date", "")), 16)
            notes   = clean(row.get("Notes",    ""), 600)
            ttl     = f'<a href="{url}" target="_blank">{title}</a>' if url else title
            tags    = ""
            if company: tags += f'<span class="tag tag-gold">{company}</span>'
            if cat:     tags += f' <span class="tag">{cat}</span>'
            if src:     tags += f' <span class="tag">{src}</span>'
            st.markdown(f"""<div class="card card-na">
  <div class="card-hdr"><div class="card-ttl">{ttl}</div><span class="card-dt">{dt or "—"}</span></div>
  <div class="card-sum">{summary or "No summary."}</div>
  <div class="card-tags">{tags}</div>
</div>""", unsafe_allow_html=True)
            if notes:
                with st.expander("Details"): st.write(notes)

# ══════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════
with tab_srch:
    st.markdown('<div class="sec-hdr">Search All Intelligence</div>', unsafe_allow_html=True)
    q = st.text_input("", placeholder="Search across all data…", key="srch_input", label_visibility="collapsed")
    if q:
        r_u = filter_df(df_upd,  q)
        r_n = filter_df(df_news, q)
        r_c = filter_df(df_comp, q)
        total = len(r_u) + len(r_n) + len(r_c)
        st.markdown(f'<div class="sec-count">{total} results for <strong>{q}</strong></div>', unsafe_allow_html=True)
        lbl = lambda t: f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#bbb;margin:18px 0 8px;">{t}</div>'
        if not r_u.empty:
            st.markdown(lbl("Regulatory"), unsafe_allow_html=True)
            for i,(_, row) in enumerate(r_u.iterrows()): render_card(row, f"sru{i}")
        if not r_n.empty:
            st.markdown(lbl("News"), unsafe_allow_html=True)
            for i,(_, row) in enumerate(r_n.iterrows()): render_card(row, f"srn{i}")
        if not r_c.empty:
            st.markdown(lbl("Competitors"), unsafe_allow_html=True)
            for i,(_, row) in enumerate(r_c.iterrows()): render_card(row, f"src{i}", show_save=False)
        if total == 0:
            st.markdown('<div class="empty">No results found.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#bbb;text-align:center;padding:40px;font-size:12.5px;">Type to search all intelligence.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# FAVORITES
# ══════════════════════════════════════════════════════════════
with tab_fav:
    st.markdown('<div class="sec-hdr">⭐ Favorites</div>', unsafe_allow_html=True)
    st.session_state.setdefault("removed_favs", set())
    st.session_state.setdefault("saved_favs",   set())
    st.session_state.setdefault("pending_favs", [])

    df_fav = load_tab("Favorites")
    if not df_fav.empty and "Title" in df_fav.columns:
        df_fav = df_fav[~df_fav["Title"].isin(st.session_state["removed_favs"])]
    if st.session_state["pending_favs"]:
        exist = set(df_fav["Title"].tolist()) if not df_fav.empty else set()
        new   = [p for p in st.session_state["pending_favs"] if p["Title"] not in exist]
        if new:
            df_fav = pd.concat([df_fav, pd.DataFrame(new)], ignore_index=True) if not df_fav.empty else pd.DataFrame(new)

    if df_fav.empty:
        st.markdown('<div class="empty">No favorites yet. Click ☆ Save on any item.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="sec-count">{len(df_fav)} saved items</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(df_fav.iloc[::-1].iterrows()):
            title   = clean(row.get("Title",   ""), 200) or "Untitled"
            url     = str(row.get("URL",       "")).strip()
            summary = clean(row.get("AI Summary", row.get("Summary", "")), 400)
            pri     = str(row.get("Priority",  "")).strip()
            ta      = clean(row.get("Therapeutic Area", ""), 60)
            pub     = clean(row.get("Published Date", row.get("Saved At", "")), 16)
            src     = clean(row.get("Source",  ""), 60)
            pc      = pclass(pri)
            ttl     = f'<a href="{url}" target="_blank">{title}</a>' if url else title
            tags    = pbadge(pri)
            if ta  and ta  not in ("-",): tags += f' <span class="tag tag-gold">{ta}</span>'
            if src and src not in ("-",): tags += f' <span class="tag">{src}</span>'
            st.markdown(f"""<div class="card card-{pc}">
  <div class="card-hdr"><div class="card-ttl">{ttl}</div><span class="card-dt">{pub or "—"}</span></div>
  <div class="card-sum">{summary or "No summary."}</div>
  <div class="card-tags">{tags}</div>
</div>""", unsafe_allow_html=True)
            if st.button("🗑 Remove", key=f"del{i}"):
                st.session_state["removed_favs"].add(title)
                st.session_state["saved_favs"].discard(title)
                st.session_state["pending_favs"] = [p for p in st.session_state["pending_favs"] if p.get("Title") != title]
                def _del(t, sname, sec):
                    try:
                        c2 = Credentials.from_service_account_info(sec, scopes=SCOPES)
                        ws2 = gspread.authorize(c2).open(sname).worksheet("Favorites")
                        rows = ws2.get_all_values()
                        for rn,r in enumerate(rows[1:],2):
                            if r and r[0]==t: ws2.delete_rows(rn); break
                    except Exception: pass
                threading.Thread(target=_del, args=(title, SHEET_NAME, dict(st.secrets["gcp_service_account"])), daemon=True).start()
                st.rerun()

# ══════════════════════════════════════════════════════════════
# ARCHIVE
# ══════════════════════════════════════════════════════════════
with tab_arc_t:
    st.markdown('<div class="sec-hdr">Archive</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="arc-note">📦 {len(df_arc) if not df_arc.empty else 0} items · older than 7 days</div>', unsafe_allow_html=True)
    if df_arc.empty:
        st.markdown('<div class="empty">Archive is empty.</div>', unsafe_allow_html=True)
    else:
        aq = st.text_input("", placeholder="Search archive…", key="arc_q", label_visibility="collapsed")
        df_af = filter_df(df_arc, aq)
        st.markdown(f'<div class="sec-count">{len(df_af)} items</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(df_af.iterrows()):
            render_card(row, key=f"arc{i}", show_save=True)
