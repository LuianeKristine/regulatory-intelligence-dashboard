import streamlit as st
import pandas as pd
import re
from datetime import datetime, date, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import threading

st.set_page_config(
    page_title="Regulatory Intelligence Platform",
    page_icon="\u2695\ufe0f",
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
  --chg: #1d4ed8;
  --chg-bg: #eff6ff;
  --chg-bd: #bfdbfe;
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
.card-changed::before { background:var(--chg); }
.card-hdr { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:5px; }
.card-ttl { font-size:13px; font-weight:500; color:var(--text-1); line-height:1.45; }
.card-ttl a { color:var(--text-1); text-decoration:none; }
.card-ttl a:hover { color:#2563eb; }
.card-dt  { font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--text-3); white-space:nowrap; flex-shrink:0; padding-top:1px; }
.card-sum { font-size:12px; color:var(--text-2); line-height:1.6; margin-bottom:8px; }
.card-raw { font-size:11px; color:var(--text-3); line-height:1.55; margin-bottom:8px; font-style:italic; border-left:2px solid var(--border); padding-left:8px; }
.card-tags { display:flex; flex-wrap:wrap; gap:3px; align-items:center; }
.card-pdf  { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; padding:2px 7px; border-radius:4px; background:#fef2f2; color:#991b1b; border:1px solid #fecaca; text-decoration:none; }
.card-pdf:hover { background:#fee2e2; }

.tag { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:500; padding:2px 6px; border-radius:4px; border:1px solid var(--border); background:var(--surface-2); color:var(--text-2); }
.tag-gold { background:var(--gold-bg); color:var(--gold); border-color:var(--gold-bd); }
.tag-chg  { background:var(--chg-bg);  color:var(--chg);  border-color:var(--chg-bd); }
.badge-high { background:var(--high-bg); color:var(--high); border:1px solid var(--high-bd); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }
.badge-med  { background:var(--med-bg);  color:var(--med);  border:1px solid var(--med-bd);  padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }
.badge-low  { background:var(--low-bg);  color:var(--low);  border:1px solid var(--low-bd);  padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }
.badge-chg  { background:var(--chg-bg);  color:var(--chg);  border:1px solid var(--chg-bd);  padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; }

.chg-banner { background:var(--chg-bg); border:1px solid var(--chg-bd); border-radius:var(--r); padding:10px 14px; margin-bottom:14px; font-size:12px; color:var(--chg); display:flex; align-items:center; gap:8px; }

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

[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarNavCollapseButton"],
button[data-testid="stBaseButton-headerNoPadding"],
button[aria-label="Close sidebar"],
button[aria-label="Open sidebar"] { display:none !important; visibility:hidden !important; }
section[data-testid="stSidebar"] > div > div > button,
section[data-testid="stSidebar"] > div > button { display:none !important; }
.st-emotion-cache-1egp75f, .eyeqlp52,
div[data-testid="collapsedControl"] { display:none !important; }

@media (max-width: 768px) {
  .hgrid { grid-template-columns: 1fr !important; }
  .block-container { padding: .8rem !important; }
  .stTabs [data-baseweb="tab"] { padding: 7px 10px !important; font-size: 11.5px !important; }
  .topbar-title { font-size: .9rem !important; }
}
@media (max-width: 480px) {
  .stTabs [data-baseweb="tab"] { padding: 6px 7px !important; font-size: 11px !important; }
  .card { padding: 11px 12px !important; }
}
</style>
""", unsafe_allow_html=True)

# \u2500\u2500 CONSTANTS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
SHEET_NAME = "Raw Intelligence"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# \u2500\u2500 DATA \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
@st.cache_resource(ttl=300)
def get_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_tab(tab_name):
    try:
        gc = get_client()
        ws = gc.open(SHEET_NAME).worksheet(tab_name)
        raw = ws.get_all_values()
        if not raw:
            return pd.DataFrame()
        headers = raw[0]
        seen_h = {}
        clean_h = []
        for h in headers:
            h = str(h).strip() or "col"
            if h in seen_h:
                seen_h[h] += 1
                clean_h.append(f"{h}_{seen_h[h]}")
            else:
                seen_h[h] = 0
                clean_h.append(h)
        rows = raw[1:]
        df = pd.DataFrame(rows, columns=clean_h) if rows else pd.DataFrame(columns=clean_h)
        if tab_name == "Favorites" and not df.empty and "Deleted" in df.columns:
            df = df[df["Deleted"].fillna("") != "deleted"]
        return df
    except Exception as e:
        st.error(f"Could not load '{tab_name}': {e}")
        return pd.DataFrame()

# \u2500\u2500 HELPERS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def clean(text, max_len=400):
    t = str(text or "")
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'!\[.*?\]\(.*?\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'[#*_`>~]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return (t[:max_len] + "\u2026") if len(t) > max_len else t

def safe_html(text):
    """Convert non-ASCII chars to HTML entities — prevents UnicodeEncodeError in Python 3.14."""
    if not text: return ""
    return str(text).encode('ascii', 'xmlcharrefreplace').decode('ascii')

# ── RELEVANCE FILTER ──────────────────────────────────────────────────────────
IRRELEVANT_RE = re.compile(
    r"search[- ]for\b|/search\?|search_api|views_fulltext|items_per_page|"
    r"\bsearch\s+results\b|search\s+fda\b|"
    r"drug[- ]trials?[- ]snapshot|trials?\s+snapshot|"
    r"meeting[- ]minute|meeting\s+highlight|committee[- ]roster|staff[- ]list|"
    r"data[- ]file|glossar|\bfaq\b|frequently[- ]asked|"
    r"\bcontact\b|\babout[- ]us\b|how[- ]to[- ]submit|subscribe|newsletter|"
    r"\bsitemap\b|\bprivacy\b|\bdisclaimer\b",
    re.IGNORECASE
)

RELEVANT_RE = re.compile(
    r"approv|authoris|authoriz|new\s+drug|new\s+treatment|new\s+therapy|indication|"
    r"label\s+change|label\s+update|prescribing|safety\s+alert|recall|withdrawn|"
    r"EPAR|NDA|BLA|sNDA|sBLA|guideline|guidance|"
    r"cell\s+therapy|gene\s+therapy|CAR-T|CRISPR|AAV|ATMP|"
    r"oncol|cancer|tumor|lymphoma|leukemia|autoimmune|rheumatoid|lupus|sclerosis|"
    r"rare\s+disease|orphan|biologic|biosimilar|immunotherapy",
    re.IGNORECASE
)

def is_relevant(row):
    title  = str(row.get("Title","")).strip()
    url    = str(row.get("URL","")).strip()
    src    = str(row.get("Source","")).strip().upper()
    dtype  = str(row.get("Doc Type","")).strip()

    if len(title) < 5:              return False
    if IRRELEVANT_RE.search(title): return False
    if IRRELEVANT_RE.search(url):   return False

    # ICH and EMA: always relevant (curated list)
    if src in ("ICH", "EMA"):       return True

    # FDA Drug Approvals and press: always relevant
    if src == "FDA" and dtype.lower() in ("drug approval", "press announcement",
        "otp event/meeting", "otp learn", "oce publication"): return True

    # Everything else: must match relevant terms in title or summary
    summary = str(row.get("AI Summary", ""))
    if RELEVANT_RE.search(title + " " + summary): return True

    # If no summary yet (just added), let it through
    if not summary.strip(): return True

    return False

def filter_relevant(df):
    if df is None or df.empty: return df
    df = df[df.apply(is_relevant, axis=1)]
    if "Title" in df.columns:
        df = df.drop_duplicates(subset=["Title"], keep="first")
    return df

def pclass(p):
    p = str(p).strip().lower()
    return p if p in ("high","medium","low") else "na"

def pbadge(p):
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
    if df is None or df.empty: return df
    if search:
        q = search.lower()
        df = df[df.apply(lambda r: q in " ".join(r.astype(str).values).lower(), axis=1)]
    if ha_f:
        col = "Health Authority" if "Health Authority" in df.columns else "Source"
        if col in df.columns:
            pat = "|".join(re.escape(h) for h in ha_f)
            df = df[df[col].fillna("").str.contains(pat, case=False)]
    if ta_f and "Therapeutic Area" in df.columns:
        pat = "|".join(re.escape(t) for t in ta_f)
        df = df[df["Therapeutic Area"].fillna("").str.contains(pat, case=False)]
    if pri_f and "Priority" in df.columns:
        df = df[df["Priority"].fillna("").str.lower().isin([p.lower() for p in pri_f])]
    return df

def sort_df(df):
    if df.empty: return df
    pri_order = {"high": 0, "medium": 1, "low": 2, "": 3}
    if "Priority" in df.columns:
        df = df.copy()
        df["_pri_sort"] = df["Priority"].fillna("").str.strip().str.lower().map(
            lambda p: pri_order.get(p, 3)
        )
    else:
        df = df.copy()
        df["_pri_sort"] = 3

    date_col = "Published Date" if "Published Date" in df.columns else ("Date" if "Date" in df.columns else None)
    if date_col:
        df["_date_sort"] = pd.to_datetime(df[date_col].fillna(""), errors="coerce")
        df = df.sort_values(["_pri_sort", "_date_sort"], ascending=[True, False])
        df = df.drop(columns=["_pri_sort", "_date_sort"])
    else:
        df = df.sort_values("_pri_sort", ascending=True)
        df = df.drop(columns=["_pri_sort"])
    return df

def render_card(row, key, show_save=True, show_change_badge=False):
    title    = safe_html(clean(row.get("Title",   ""), 200) or "Untitled")
    url      = str(row.get("URL", "")).strip()
    pdf_url  = str(row.get("PDF URL", row.get("pdf_url", ""))).strip()
    summary  = safe_html(clean(row.get("AI Summary", row.get("Summary", "")), 400))
    raw_exc  = safe_html(clean(row.get("Raw Text Excerpt", row.get("raw_excerpt", "")), 300))
    pri      = str(row.get("Priority", "")).strip()
    pub      = safe_html(clean(row.get("Published Date", row.get("Date", "")), 16))
    last_mod = safe_html(clean(row.get("Last Modified", ""), 16))
    src      = safe_html(clean(row.get("Source", ""), 60))
    ta       = safe_html(clean(row.get("Therapeutic Area", ""), 60))
    impl     = safe_html(clean(row.get("Implications", ""), 600))
    actions  = safe_html(clean(row.get("Action Items",  ""), 600))
    chg_date = safe_html(clean(row.get("Change Detected", row.get("Change Detected Date", "")), 16))

    # Date display: published + last modified
    if last_mod and last_mod != pub:
        date_display = f'<span class="card-dt">Published: {pub or "—"}</span><span class="card-dt" style="margin-left:10px;color:var(--chg);">Updated: {last_mod}</span>'
    else:
        date_display = f'<span class="card-dt">{pub or "—"}</span>'

    pc   = pclass(pri)
    card_class = "card-changed" if show_change_badge else f"card-{pc}"
    ttl  = f'<a href="{url}" target="_blank">{title}</a>' if url else title
    tags = build_tags(row)

    # PDF link badge
    pdf_badge = f' <a href="{pdf_url}" target="_blank" class="card-pdf">&#x1F4C4; PDF</a>' if pdf_url else ""

    # Change badge
    chg_badge = f' <span class="badge-chg">UPDATED {chg_date}</span>' if show_change_badge and chg_date else (
                f' <span class="badge-chg">UPDATED</span>' if show_change_badge else "")

    # Raw excerpt block (shown only if present)
    raw_block = f'<div class="card-raw">"{raw_exc}"</div>' if raw_exc else ""

    _card_html = (
        '<div class="card ' + card_class + '">'
        '<div class="card-hdr">'
        '<div class="card-ttl">' + ttl + '</div>'
        '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex-shrink:0;">' + date_display + '</div>'
        '</div>'
        '<div class="card-sum">' + (summary or "No summary available.") + '</div>'
        + raw_block +
        '<div class="card-tags">' + tags + pdf_badge + chg_badge + '</div>'
        '</div>'
    )
    st.markdown(_card_html, unsafe_allow_html=True)

    if impl or actions:
        with st.expander("Analysis"):
            if impl:    st.write(f"**Implications:** {impl}")
            if actions: st.write(f"**Actions:** {actions}")

    if show_save:
        already = title in st.session_state.get("saved_favs", set())
        if st.button("\u2b50 Saved" if already else "\u2606 Save", key=f"sav_{key}", disabled=already):
            st.session_state.setdefault("saved_favs",   set()).add(title)
            st.session_state.setdefault("pending_favs", []).append({
                "Title": title, "URL": url, "PDF URL": pdf_url, "Source": src,
                "Published Date": pub, "Priority": pri,
                "Therapeutic Area": ta, "AI Summary": summary,
                "Saved At": datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
                "Deleted": "",
            })
            def _write(t, u, pu, s, p, pr, ta_, sm, dt, sname, sec):
                try:
                    c2 = Credentials.from_service_account_info(sec, scopes=SCOPES)
                    gspread.authorize(c2).open(sname).worksheet("Favorites").append_row(
                        [t, u, pu, s, p, pr, ta_, sm, dt, ""])
                except Exception: pass
            threading.Thread(target=_write, args=(
                title, url, pdf_url, src, pub, pri, ta, summary,
                datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
                SHEET_NAME, dict(st.secrets["gcp_service_account"])), daemon=True).start()
            st.rerun()

# \u2500\u2500 SIDEBAR \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
with st.sidebar:
    st.markdown("""<div style="padding:2px 0 18px;border-bottom:1px solid #eee;margin-bottom:14px;">
      <div style="font-size:1rem;font-weight:700;letter-spacing:-.02em;font-family:'Inter',sans-serif;">RI</div>
      <div style="font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.1em;margin-top:2px;font-family:'Inter',sans-serif;">Regulatory Intelligence</div>
    </div>""", unsafe_allow_html=True)
    search_q = st.text_input("", placeholder="Filter\u2026", label_visibility="collapsed")
    sel_pri  = st.multiselect("Priority",         ["High","Medium","Low"])
    sel_ha   = st.multiselect("Health Authority", ["FDA","EMA","ICH"])
    sel_ta   = st.multiselect("Therapeutic Area", ["Oncology","Gene Therapy","Cell Therapy","Rare Disease","Autoimmune"])
    if st.button("\u21ba  Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    _t = datetime.now(timezone(timedelta(hours=-3))).strftime("%H:%M")
    st.markdown(f'<div style="font-size:10px;color:#bbb;text-align:center;margin-top:8px;font-family:JetBrains Mono,monospace;">updated {_t}</div>', unsafe_allow_html=True)

# \u2500\u2500 HEADER \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
st.markdown(f"""<div class="topbar">
  <div class="topbar-title">Regulatory Intelligence Platform</div>
  <div class="topbar-meta"><span class="live"></span>{date.today().strftime("%a, %b %d %Y")}</div>
</div>""", unsafe_allow_html=True)

# \u2500\u2500 LOAD \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
with st.spinner("Loading\u2026"):
    df_upd   = filter_relevant(load_tab("Updates"))
    df_news  = filter_relevant(load_tab("News"))
    df_arc   = load_tab("Archive")
    df_appr  = load_tab("Drug Approvals")
    df_adcom = load_tab("Advisory Committees")

tab_home, tab_fda, tab_appr, tab_adcom, tab_srch, tab_arc_t, tab_fav = st.tabs([
    "🏠 Home", "🇺🇸 FDA", "💊 Drug Approvals", "🏛️ Advisory Committees",
    "🔍 Search", "Archive", "⭐ Favorites"
])

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# HOME
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_home:
    st.markdown('<div style="padding:40px;text-align:center;color:var(--text-3);font-size:13px;">Select a tab to explore regulatory intelligence.</div>', unsafe_allow_html=True)
# REGULATORY
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_fda:
    st.markdown('<div class="sec-hdr">🇺🇸 FDA Updates & News</div>', unsafe_allow_html=True)
    # Load FDA docs without relevance filter
    df_upd_raw = load_tab("Updates")
    if not df_upd_raw.empty:
        if "Health Authority" in df_upd_raw.columns:
            fda_df = df_upd_raw[df_upd_raw["Health Authority"].fillna("").str.upper().str.contains("FDA")]
        else:
            fda_df = df_upd_raw[df_upd_raw["Source"].fillna("").str.upper().str.contains("FDA")]
    else:
        fda_df = pd.DataFrame()
    # Also include FDA news only
    df_news_raw = load_tab("News")
    if not df_news_raw.empty:
        src_col = "Health Authority" if "Health Authority" in df_news_raw.columns else "Source"
        fda_news = df_news_raw[df_news_raw[src_col].fillna("").str.upper().str.contains("FDA")]
    else:
        fda_news = pd.DataFrame()
    fda_combined = pd.concat([fda_df, fda_news], ignore_index=True) if not fda_news.empty else fda_df
    df_f = sort_df(filter_df(fda_combined, search_q, None, sel_ta, sel_pri))
    st.markdown(f'<div class="sec-count">{len(df_f)} items</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.markdown('<div class="empty">No FDA documents yet.</div>', unsafe_allow_html=True)
    else:
        for i, (_, row) in enumerate(df_f.iterrows()):
            render_card(row, key=f"fda{i}")

# ══════════════════════════════════════════════════════════════════════════════
# DRUG APPROVALS
# ══════════════════════════════════════════════════════════════════════════════
with tab_appr:
    st.markdown('<div class="sec-hdr">💊 Cell & Gene Therapy — Drug Approvals</div>', unsafe_allow_html=True)
    if df_appr.empty:
        st.markdown('<div class="empty">No drug approvals yet. Run the FDA Extended Scanner to populate.</div>', unsafe_allow_html=True)
    else:
        df_af = df_appr.copy()
        if search_q:
            q = search_q.lower()
            df_af = df_af[df_af.apply(lambda r: q in " ".join(r.astype(str).values).lower(), axis=1)]
        if sel_ta and "Therapeutic Area" in df_af.columns:
            df_af = df_af[df_af["Therapeutic Area"].fillna("").str.contains("|".join(sel_ta), case=False)]
        st.markdown(f'<div class="sec-count">{len(df_af)} approvals</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(df_af.iterrows()):
            drug       = clean(row.get("Drug Name",           ""), 200) or "Unnamed Drug"
            appr_url   = str(row.get("Approval URL",          "")).strip()
            letter_url  = str(row.get("Approval Letter URL",  "")).strip()
            clinical_url = str(row.get("Clinical Review URL", "")).strip()
            appr_date  = clean(row.get("Approval Date",       ""), 16)
            last_doc   = clean(row.get("Last Document Update",""), 16)
            summary    = clean(row.get("AI Summary",          ""), 500)
            clinical   = clean(row.get("Clinical Data Summary",""), 600)
            reg_impact = clean(row.get("Regulatory Impact",   ""), 600)
            pri        = str(row.get("Priority", "High")).strip()
            ta         = clean(row.get("Therapeutic Area",    ""), 60)
            pc         = pclass(pri)

            ttl       = f'<a href="{appr_url}" target="_blank">{drug}</a>' if appr_url else drug
            tags      = pbadge(pri)
            if ta and ta not in ("-",): tags += f' <span class="tag tag-gold">{ta}</span>'
            tags += ' <span class="tag">FDA</span>'
            letter_badge   = f' <a href="{letter_url}" target="_blank" class="card-pdf">📄 Approval Letter</a>' if letter_url else ""
            clinical_badge = f' <a href="{clinical_url}" target="_blank" class="card-pdf">🔬 Clinical Review</a>' if clinical_url else ""

            # Date line: approval date + last doc update
            date_line = ""
            if appr_date: date_line += f"Approved: <strong>{appr_date}</strong>"
            if last_doc:  date_line += f"&nbsp;&nbsp;·&nbsp;&nbsp;Last doc: <strong>{last_doc}</strong>"

            st.markdown(f"""<div class="card card-{pc}">
  <div class="card-hdr">
    <div class="card-ttl">{ttl}</div>
    <span class="card-dt" style="font-size:10px;color:var(--text-3);">{date_line}</span>
  </div>
  <div class="card-sum">{summary or "No summary available."}</div>
  <div class="card-tags">{tags}{letter_badge}{clinical_badge}</div>
</div>""", unsafe_allow_html=True)

            if clinical or reg_impact:
                with st.expander("Clinical Data & Regulatory Impact"):
                    if clinical:    st.write(f"**Clinical Data:** {clinical}")
                    if reg_impact:  st.write(f"**Regulatory Impact:** {reg_impact}")

# ══════════════════════════════════════════════════════════════════════════════
# ADVISORY COMMITTEES
# ══════════════════════════════════════════════════════════════════════════════
with tab_adcom:
    st.markdown('<div class="sec-hdr">🏛️ Advisory Committee Meetings</div>', unsafe_allow_html=True)
    if df_adcom.empty:
        st.markdown('<div class="empty">No advisory committee meetings yet. Run the FDA Extended Scanner to populate.</div>', unsafe_allow_html=True)
    else:
        df_ac = df_adcom.copy()
        if search_q:
            q = search_q.lower()
            df_ac = df_ac[df_ac.apply(lambda r: q in " ".join(r.astype(str).values).lower(), axis=1)]
        if sel_ta and "Therapeutic Area" in df_ac.columns:
            df_ac = df_ac[df_ac["Therapeutic Area"].fillna("").str.contains("|".join(sel_ta), case=False)]

        # Sort by meeting date desc
        if "Meeting Date" in df_ac.columns:
            df_ac["_dsort"] = pd.to_datetime(df_ac["Meeting Date"].fillna(""), errors="coerce")
            df_ac = df_ac.sort_values("_dsort", ascending=False).drop(columns=["_dsort"])

        st.markdown(f'<div class="sec-count">{len(df_ac)} meetings</div>', unsafe_allow_html=True)

        for i, (_, row) in enumerate(df_ac.iterrows()):
            committee  = clean(row.get("Committee",          ""), 100)
            title      = clean(row.get("Meeting Title",      ""), 200) or committee or "Advisory Committee Meeting"
            meet_url   = str(row.get("Meeting URL",          "")).strip()
            meet_date  = clean(row.get("Meeting Date",       ""), 16)
            docs_avail = clean(row.get("Documents Available",""), 300)
            last_doc   = clean(row.get("Latest Doc Added",   ""), 16)
            summary    = clean(row.get("AI Summary",         ""), 500)
            pri        = str(row.get("Priority", "High")).strip()
            ta         = clean(row.get("Therapeutic Area",   ""), 60)
            pc         = pclass(pri)

            ttl  = f'<a href="{meet_url}" target="_blank">{title}</a>' if meet_url else title
            tags = pbadge(pri)
            if ta        and ta        not in ("-",): tags += f' <span class="tag tag-gold">{ta}</span>'
            if committee and committee not in ("-",): tags += f' <span class="tag">{committee}</span>'

            # Date line
            date_line = ""
            if meet_date: date_line += f"Meeting: <strong>{meet_date}</strong>"
            if last_doc:  date_line += f"&nbsp;&nbsp;·&nbsp;&nbsp;Latest doc: <strong>{last_doc}</strong>"

            # Documents available as small tags
            docs_html = ""
            if docs_avail and docs_avail not in ("-", "None"):
                doc_list = [d.strip() for d in docs_avail.split(",") if d.strip()]
                docs_html = " ".join(f'<span class="tag">{d}</span>' for d in doc_list)
                docs_html = f'<div style="margin:6px 0 4px;display:flex;flex-wrap:wrap;gap:3px;">{docs_html}</div>'

            st.markdown(f"""<div class="card card-{pc}">
  <div class="card-hdr">
    <div class="card-ttl">{ttl}</div>
    <span class="card-dt" style="font-size:10px;color:var(--text-3);">{date_line}</span>
  </div>
  <div class="card-sum">{summary or "No summary available."}</div>
  {docs_html}
  <div class="card-tags">{tags}</div>
</div>""", unsafe_allow_html=True)


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# COMPETITORS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_srch:
    st.markdown('<div class="sec-hdr">Search All Intelligence</div>', unsafe_allow_html=True)
    q = st.text_input("", placeholder="Search across all data\u2026", key="srch_input", label_visibility="collapsed")
    if q:
        r_u = filter_df(df_upd,  q)
        r_n = filter_df(df_news, q)
        total = len(r_u) + len(r_n)
        st.markdown(f'<div class="sec-count">{total} results for <strong>{q}</strong></div>', unsafe_allow_html=True)
        lbl = lambda t: f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#bbb;margin:18px 0 8px;">{t}</div>'
        if not r_u.empty:
            st.markdown(lbl("Regulatory"), unsafe_allow_html=True)
            for i,(_, row) in enumerate(r_u.iterrows()): render_card(row, f"sru{i}")
        if not r_n.empty:
            st.markdown(lbl("News"), unsafe_allow_html=True)
            for i,(_, row) in enumerate(r_n.iterrows()): render_card(row, f"srn{i}")
        if total == 0:
            st.markdown('<div class="empty">No results found.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#bbb;text-align:center;padding:40px;font-size:12.5px;">Type to search all intelligence.</div>', unsafe_allow_html=True)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# FAVORITES
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_fav:
    st.markdown('<div class="sec-hdr">\u2b50 Favorites</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="empty">No favorites yet. Click \u2606 Save on any item.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="sec-count">{len(df_fav)} saved items</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(df_fav.iloc[::-1].iterrows()):
            title   = clean(row.get("Title",   ""), 200) or "Untitled"
            url     = str(row.get("URL",       "")).strip()
            pdf_url = str(row.get("PDF URL",   "")).strip()
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
            pdf_badge = f' <a href="{pdf_url}" target="_blank" class="card-pdf">&#x1F4C4; PDF</a>' if pdf_url else ""
            st.markdown(f"""<div class="card card-{pc}">
  <div class="card-hdr"><div class="card-ttl">{ttl}</div><span class="card-dt">{pub or "\u2014"}</span></div>
  <div class="card-sum">{summary or "No summary."}</div>
  <div class="card-tags">{tags}{pdf_badge}</div>
</div>""", unsafe_allow_html=True)
            if st.button("Remove", key=f"del{i}"):
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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# ARCHIVE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_arc_t:
    st.markdown('<div class="sec-hdr">Archive</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="arc-note">&#x1F4E6; {len(df_arc) if not df_arc.empty else 0} items \u00b7 historical regulatory documents and archived news</div>', unsafe_allow_html=True)
    if df_arc.empty:
        st.markdown('<div class="empty">Archive is empty.</div>', unsafe_allow_html=True)
    else:
        aq = st.text_input("", placeholder="Search archive\u2026", key="arc_q", label_visibility="collapsed")
        df_af = filter_df(df_arc, aq)
        st.markdown(f'<div class="sec-count">{len(df_af)} items</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(df_af.iterrows()):
            render_card(row, key=f"arc{i}", show_save=True)
