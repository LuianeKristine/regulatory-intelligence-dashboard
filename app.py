import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json, re, datetime, os

st.set_page_config(
    page_title="Regulatory Intelligence",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
}
section[data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #1e2d40;
}
section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

.reg-header {
    display: flex; align-items: center; gap: 14px;
    padding: 1.2rem 0 1rem;
    border-bottom: 1px solid #1e2d40;
    margin-bottom: 1.5rem;
}
.reg-header h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.25rem; font-weight: 500;
    color: #e2e8f0; margin: 0; letter-spacing: 0.03em;
}
.reg-header .subtitle {
    font-size: 0.68rem; color: #475569;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.08em; text-transform: uppercase;
}

.stats-row { display: flex; gap: 10px; margin-bottom: 1.4rem; flex-wrap: wrap; }
.stat-chip {
    background: #0d1220; border: 1px solid #1e2d40;
    border-radius: 6px; padding: 10px 18px;
    display: flex; align-items: center; gap: 10px; min-width: 130px;
}
.stat-chip .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-red    { background: #ef4444; box-shadow: 0 0 6px #ef444466; }
.dot-yellow { background: #f59e0b; box-shadow: 0 0 6px #f59e0b66; }
.dot-green  { background: #10b981; box-shadow: 0 0 6px #10b98166; }
.dot-blue   { background: #3b82f6; box-shadow: 0 0 6px #3b82f666; }
.stat-chip .count { font-family: 'IBM Plex Mono', monospace; font-size: 1.35rem; font-weight: 500; color: #e2e8f0; }
.stat-chip .label { font-size: 0.68rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; color: #475569;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin: 1.4rem 0 0.7rem;
    display: flex; align-items: center; gap: 8px;
}
.section-label::after { content: ''; flex: 1; height: 1px; background: #1e2d40; }

.reg-card {
    background: #0d1220; border: 1px solid #1e2d40;
    border-radius: 8px; padding: 15px 18px;
    margin-bottom: 9px; position: relative;
}
.reg-card:hover { border-color: #2d4a6e; }
.reg-card.card-high   { border-left: 3px solid #ef4444; }
.reg-card.card-medium { border-left: 3px solid #f59e0b; }
.reg-card.card-low    { border-left: 3px solid #10b981; }

.card-top {
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 12px; margin-bottom: 7px;
}
.card-title { font-size: 0.88rem; font-weight: 500; color: #e2e8f0; line-height: 1.4; flex: 1; }
.card-title a { color: #e2e8f0 !important; text-decoration: none; }
.card-title a:hover { color: #60a5fa !important; }

.badges { display: flex; gap: 5px; flex-wrap: wrap; align-items: center; flex-shrink: 0; }
.badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; padding: 2px 7px; border-radius: 3px;
    letter-spacing: 0.04em; font-weight: 500; white-space: nowrap;
}
.badge-high   { background: #2d1515; color: #ef4444; border: 1px solid #3d1818; }
.badge-medium { background: #2d1f0a; color: #f59e0b; border: 1px solid #3d2a0d; }
.badge-low    { background: #0a2d1f; color: #10b981; border: 1px solid #0d3d2a; }
.badge-source { background: #111827; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-type   { background: #111827; color: #94a3b8; border: 1px solid #1e2d40; }
.badge-pdf    { background: #1a0d2d; color: #a78bfa; border: 1px solid #2d1a4a; }
.badge-changed{ background: #2d1515; color: #f87171; border: 1px solid #4a1f1f; }

.pdot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }
.pdot-red    { background:#ef4444; box-shadow:0 0 4px #ef444455; }
.pdot-yellow { background:#f59e0b; box-shadow:0 0 4px #f59e0b55; }
.pdot-green  { background:#10b981; box-shadow:0 0 4px #10b98155; }

.card-summary { font-size: 0.81rem; color: #94a3b8; line-height: 1.6; margin: 5px 0; }
.card-impl    { font-size: 0.76rem; color: #64748b; line-height: 1.5; margin: 3px 0; }

.changed-banner {
    background: #160808; border: 1px solid #3d1818;
    border-radius: 5px; padding: 8px 12px;
    margin: 7px 0; font-size: 0.79rem; color: #fca5a5;
    display: flex; gap: 8px; align-items: flex-start;
}

.card-meta {
    display: flex; gap: 14px; margin-top: 8px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.64rem; color: #374151; flex-wrap: wrap;
}
.card-meta a { color: #7c3aed !important; text-decoration: none; }
.card-meta a:hover { color: #a78bfa !important; }

.alert-bar {
    background: #160808; border: 1px solid #ef4444;
    border-radius: 6px; padding: 10px 16px;
    font-size: 0.79rem; color: #fca5a5;
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 1rem;
}
.empty-state {
    text-align: center; padding: 3rem;
    color: #1e2d40; font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem;
}

.stTabs [data-baseweb="tab-list"] { gap: 0; background: transparent; border-bottom: 1px solid #1e2d40; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #475569 !important;
    border: none !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.06em; padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] { color: #e2e8f0 !important; border-bottom: 2px solid #3b82f6 !important; }

.stTextInput input {
    background: #0d1220 !important; border: 1px solid #1e2d40 !important;
    color: #e2e8f0 !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; border-radius: 6px;
}
.stTextInput input:focus { border-color: #3b82f6 !important; box-shadow: none !important; }
.stSelectbox > div > div { background: #0d1220 !important; border: 1px solid #1e2d40 !important; color: #94a3b8 !important; }
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ── SHEETS ───────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.readonly"]

@st.cache_resource(ttl=300)
def get_gc():
    key_data = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if not key_data:
        st.error("⚠️ GCP_SERVICE_ACCOUNT_JSON not configured.")
        st.stop()
    creds = Credentials.from_service_account_info(json.loads(key_data), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=180)
def load_tab(name):
    try:
        ws = get_gc().open("Raw Intelligence").worksheet(name)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

def safe(v, d=""):
    if v is None: return d
    if isinstance(v, float) and pd.isna(v): return d
    return str(v).strip()

def pinfo(p):
    p = (p or "").lower()
    if "high"   in p: return "high",   "badge-high",   "pdot pdot-red"
    if "medium" in p: return "medium", "badge-medium", "pdot pdot-yellow"
    return "low", "badge-low", "pdot pdot-green"

def render_card(row):
    title    = safe(row.get("Title","Untitled"))
    url      = safe(row.get("URL",""))
    pdf_url  = safe(row.get("PDF URL",""))
    source   = safe(row.get("Source",""))
    doc_type = safe(row.get("Doc Type",""))
    pub      = safe(row.get("Published Date", row.get("date","")))
    last_mod = safe(row.get("Last Modified",""))
    scan     = safe(row.get("Last Scan", row.get("Scan Date","")))
    summary  = safe(row.get("AI Summary","")) or safe(row.get("Summary",""))
    changed  = safe(row.get("What Changed",""))
    impl     = safe(row.get("Implications",""))
    actions  = safe(row.get("Action Items",""))
    priority = safe(row.get("Priority","Medium"))

    pclass, pbadge, pdotcls = pinfo(priority)
    title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title

    badges = f'<span class="badge {pbadge}">{priority.upper()}</span>'
    if changed and changed not in ("New document",""):
        badges += ' <span class="badge badge-changed">⚡ UPDATED</span>'
    if pdf_url:
        badges += ' <span class="badge badge-pdf">📄 PDF</span>'
    if source:
        badges += f' <span class="badge badge-source">{source}</span>'
    if doc_type:
        badges += f' <span class="badge badge-type">{doc_type}</span>'

    html = f"""<div class="reg-card card-{pclass}">
  <div class="card-top">
    <div class="card-title"><span class="{pdotcls}"></span>{title_html}</div>
    <div class="badges">{badges}</div>
  </div>"""

    if changed and changed not in ("New document",""):
        html += f'<div class="changed-banner"><span>⚡</span><div><strong>What changed:</strong> {changed}</div></div>'

    if summary:
        html += f'<div class="card-summary">{summary}</div>'

    if impl:
        short = impl[:200] + "…" if len(impl) > 200 else impl
        html += f'<div class="card-impl">⚖️ {short}</div>'

    if actions:
        first = actions.split("\n")[0].replace("•","").strip()
        if first:
            html += f'<div class="card-impl">→ {first[:160]}</div>'

    meta = []
    if pub:      meta.append(f"📅 {pub}")
    if last_mod: meta.append(f"✏️ last modified: {last_mod}")
    if scan:     meta.append(f"🔍 scanned: {scan}")
    if pdf_url:  meta.append(f'<a href="{pdf_url}" target="_blank">📄 open PDF</a>')
    if meta:
        html += f'<div class="card-meta">{"  ·  ".join(meta)}</div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def news_to_card(row):
    return {
        "Title": row.get("Title",""), "URL": row.get("URL",""),
        "PDF URL": "", "Source": row.get("Source",""), "Doc Type": "News",
        "Published Date": row.get("Published Date",""), "Last Modified": "",
        "Last Scan": row.get("Scan Date",""), "AI Summary": row.get("AI Summary",""),
        "What Changed": "", "Implications": "", "Action Items": "",
        "Priority": row.get("Priority","Medium"),
    }

def filter_df(df, q="", priority="All", source="All"):
    if df.empty: return df
    f = df.copy()
    if q:
        mask = f.apply(lambda r: q.lower() in str(r.values).lower(), axis=1)
        f = f[mask]
    if priority != "All" and "Priority" in f.columns:
        f = f[f["Priority"].str.lower() == priority.lower()]
    if source != "All" and "Source" in f.columns:
        f = f[f["Source"] == source]
    if "Priority" in f.columns:
        order = {"high":0,"medium":1,"low":2}
        f["_s"] = f["Priority"].str.lower().map(lambda x: order.get(x,1))
        f = f.sort_values("_s").drop(columns=["_s"])
    return f

# ── LOAD ─────────────────────────────────────────────────────
with st.spinner("Loading..."):
    df_docs = load_tab("Updates")
    df_news = load_tab("News")
    df_chg  = load_tab("Changes")
    df_favs = load_tab("Favorites")

for df in [df_docs, df_news, df_chg]:
    if not df.empty and "Priority" not in df.columns:
        df["Priority"] = "Medium"

def fp(df, p): return df[df["Priority"].str.lower() == p.lower()] if not df.empty and "Priority" in df.columns else pd.DataFrame()

high_docs   = fp(df_docs, "High")
med_docs    = fp(df_docs, "Medium")
high_news   = fp(df_news, "High")
n_chg       = len(df_chg)

# ── HEADER ───────────────────────────────────────────────────
st.markdown(f"""
<div class="reg-header">
  <div>
    <div class="subtitle">Pharma Regulatory Intelligence Platform</div>
    <h1>⚗️ RAW INTELLIGENCE</h1>
  </div>
  <div style="margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:#1e2d40">
    {datetime.date.today().strftime("%d %b %Y")}
  </div>
</div>""", unsafe_allow_html=True)

if n_chg > 0:
    news_note = f" + {len(high_news)} treatment news flagged HIGH." if len(high_news) else ""
    st.markdown(f'<div class="alert-bar">⚡ <strong>{n_chg} document(s) changed since last scan</strong> — all marked HIGH PRIORITY.{news_note}</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="stats-row">
  <div class="stat-chip"><div class="dot dot-red"></div><div><div class="count">{len(high_docs)+n_chg}</div><div class="label">High Priority</div></div></div>
  <div class="stat-chip"><div class="dot dot-yellow"></div><div><div class="count">{len(med_docs)}</div><div class="label">Medium</div></div></div>
  <div class="stat-chip"><div class="dot dot-red"></div><div><div class="count">{n_chg}</div><div class="label">Changes</div></div></div>
  <div class="stat-chip"><div class="dot dot-blue"></div><div><div class="count">{len(df_news)}</div><div class="label">News</div></div></div>
  <div class="stat-chip"><div class="dot dot-green"></div><div><div class="count">{len(df_docs)}</div><div class="label">Docs Monitored</div></div></div>
</div>""", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────
t_home, t_fda, t_ema, t_ich, t_chg, t_news, t_search, t_favs = st.tabs([
    "🏠 Home", "🇺🇸 FDA", "🇪🇺 EMA", "📋 ICH",
    f"⚡ Changes ({n_chg})", "📰 News", "🔍 Search", "⭐ Favorites"
])

# HOME
with t_home:
    if not df_chg.empty:
        st.markdown('<div class="section-label">⚡ Document changes detected</div>', unsafe_allow_html=True)
        for _, r in df_chg.iterrows(): render_card(r)

    shown_urls = set(df_chg["URL"].tolist()) if not df_chg.empty else set()
    high_only = high_docs[~high_docs["URL"].isin(shown_urls)] if not high_docs.empty else pd.DataFrame()
    if not high_only.empty:
        st.markdown('<div class="section-label">🔴 High priority — regulatory documents</div>', unsafe_allow_html=True)
        for _, r in high_only.iterrows(): render_card(r)

    if not high_news.empty:
        st.markdown('<div class="section-label">🔴 High priority — treatment news</div>', unsafe_allow_html=True)
        for _, r in high_news.iterrows(): render_card(news_to_card(r))

    if not med_docs.empty:
        st.markdown('<div class="section-label">🟡 Medium priority — regulatory documents</div>', unsafe_allow_html=True)
        for _, r in med_docs.iterrows(): render_card(r)

    if df_chg.empty and high_only.empty and high_news.empty and med_docs.empty:
        st.markdown('<div class="empty-state">// no high or medium priority items —<br>run the scanner to populate intelligence</div>', unsafe_allow_html=True)

# FDA
with t_fda:
    fda_df = df_docs[df_docs["Source"].str.upper() == "FDA"] if not df_docs.empty and "Source" in df_docs.columns else pd.DataFrame()
    if fda_df.empty:
        st.markdown('<div class="empty-state">// no FDA documents yet</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3,1])
        q  = c1.text_input("", placeholder="drug name, indication, doc type…", key="fda_q", label_visibility="collapsed")
        pf = c2.selectbox("", ["All","High","Medium","Low"], key="fda_p", label_visibility="collapsed")
        f  = filter_df(fda_df, q, pf)
        st.markdown(f'<div class="section-label">FDA Documents ({len(f)})</div>', unsafe_allow_html=True)
        for _, r in f.iterrows(): render_card(r)

# EMA
with t_ema:
    ema_df = df_docs[df_docs["Source"].str.upper() == "EMA"] if not df_docs.empty and "Source" in df_docs.columns else pd.DataFrame()
    if ema_df.empty:
        st.markdown('<div class="empty-state">// no EMA documents yet</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3,1])
        q  = c1.text_input("", placeholder="medicine name, EPAR, indication…", key="ema_q", label_visibility="collapsed")
        pf = c2.selectbox("", ["All","High","Medium","Low"], key="ema_p", label_visibility="collapsed")
        f  = filter_df(ema_df, q, pf)
        st.markdown(f'<div class="section-label">EMA Documents ({len(f)})</div>', unsafe_allow_html=True)
        for _, r in f.iterrows(): render_card(r)

# ICH
with t_ich:
    ich_df = df_docs[df_docs["Source"].str.upper() == "ICH"] if not df_docs.empty and "Source" in df_docs.columns else pd.DataFrame()
    if ich_df.empty:
        st.markdown('<div class="empty-state">// no ICH guidelines yet</div>', unsafe_allow_html=True)
    else:
        q = st.text_input("", placeholder="guideline code, topic…", key="ich_q", label_visibility="collapsed")
        f = filter_df(ich_df, q)
        st.markdown(f'<div class="section-label">ICH Guidelines ({len(f)})</div>', unsafe_allow_html=True)
        for _, r in f.iterrows(): render_card(r)

# CHANGES
with t_chg:
    if df_chg.empty:
        st.markdown('<div class="empty-state">// no changes detected yet —<br>changes appear here when documents are updated between scans</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-label">⚡ All detected changes ({n_chg})</div>', unsafe_allow_html=True)
        for _, r in df_chg.iterrows(): render_card(r)

# NEWS
with t_news:
    if df_news.empty:
        st.markdown('<div class="empty-state">// no news yet</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3,1])
        q   = c1.text_input("", placeholder="drug, company, topic…", key="nq", label_visibility="collapsed")
        pf  = c2.selectbox("", ["All","High","Medium","Low"], key="np", label_visibility="collapsed")
        f   = filter_df(df_news, q, pf)
        st.markdown(f'<div class="section-label">News ({len(f)})</div>', unsafe_allow_html=True)
        for _, r in f.iterrows(): render_card(news_to_card(r))

# SEARCH
with t_search:
    q = st.text_input("", placeholder="search everything — drug name, guideline, therapeutic area, keyword…", key="gq", label_visibility="collapsed")
    if q:
        results = []
        for df, kind in [(df_docs,"doc"),(df_news,"news"),(df_chg,"change")]:
            if df.empty: continue
            mask = df.apply(lambda r: q.lower() in str(r.values).lower(), axis=1)
            m = df[mask].copy(); m["_kind"] = kind
            results.append(m)
        if results:
            combined = pd.concat(results, ignore_index=True)
            st.markdown(f'<div class="section-label">Found {len(combined)} results for "{q}"</div>', unsafe_allow_html=True)
            for _, r in combined.iterrows():
                render_card(news_to_card(r) if r.get("_kind") == "news" else r)
        else:
            st.markdown(f'<div class="empty-state">// no results for "{q}"</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">// type above to search all documents, news and changes</div>', unsafe_allow_html=True)

# FAVORITES
with t_favs:
    if df_favs.empty:
        st.markdown('<div class="empty-state">// no favorites saved yet</div>', unsafe_allow_html=True)
    else:
        active = df_favs[df_favs.get("Deleted", pd.Series([""] * len(df_favs))).astype(str).str.lower() != "yes"] if not df_favs.empty else df_favs
        st.markdown(f'<div class="section-label">Saved items ({len(active)})</div>', unsafe_allow_html=True)
        for _, r in active.iterrows():
            render_card({
                "Title": r.get("Title",""), "URL": r.get("URL",""),
                "PDF URL": r.get("PDF URL",""), "Source": r.get("Source",""),
                "Doc Type": "", "Published Date": r.get("Published Date",""),
                "Last Modified": "", "Last Scan": r.get("Saved At",""),
                "AI Summary": r.get("AI Summary",""), "What Changed": "",
                "Implications": "", "Action Items": "",
                "Priority": r.get("Priority","Medium"),
            })

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚗️ Intelligence")
    st.markdown("---")
    if not df_docs.empty and "Therapeutic Area" in df_docs.columns:
        areas = ["All"] + sorted(df_docs["Therapeutic Area"].dropna().unique().tolist())
        st.selectbox("Therapeutic Area", areas, key="sb_ta")
    if not df_docs.empty and "Health Authority" in df_docs.columns:
        auths = ["All"] + sorted(df_docs["Health Authority"].dropna().unique().tolist())
        st.selectbox("Health Authority", auths, key="sb_ha")
    st.markdown("---")
    st.markdown("### 📊 Snapshot")
    total_high = len(high_docs) + n_chg + len(high_news)
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.7rem;line-height:2.2;">
    <span style="color:#ef4444">🔴 HIGH</span> &nbsp;&nbsp;&nbsp;{total_high}<br>
    <span style="color:#f59e0b">🟡 MEDIUM</span> &nbsp;{len(med_docs)}<br>
    <span style="color:#10b981">🟢 LOW</span> &nbsp;&nbsp;&nbsp;{len(fp(df_docs,"Low"))}<br>
    <span style="color:#3b82f6">📰 NEWS</span> &nbsp;&nbsp;&nbsp;{len(df_news)}<br>
    <span style="color:#f87171">⚡ CHANGED</span> {n_chg}
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown(f'<div style="font-size:0.62rem;color:#1e2d40;font-family:\'IBM Plex Mono\',monospace;margin-top:6px">updated {datetime.datetime.now().strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
