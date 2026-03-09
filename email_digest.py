"""
Regulatory Intelligence — Daily Email Digest
Usa Gmail SMTP (gratuito, 500 emails/dia).
Roda todo dia às 08:00 BRT via GitHub Actions.
"""

import os
import re
import json
import smtplib
import gspread
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from google.oauth2.service_account import Credentials

# ── CONFIG ────────────────────────────────────────────────────
GMAIL_USER     = os.environ["GMAIL_USER"]      # seu@gmail.com
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]  # App Password do Google
TO_EMAIL       = os.environ["TO_EMAIL"]        # destinatário(s), vírgula pra múltiplos
SHEET_NAME     = "Raw Intelligence"
SCOPES         = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

BRT  = timezone(timedelta(hours=-3))
TABS = [
    ("Updates",     "Published Date", "🏛️ Regulatory Updates"),
    ("News",        "Published Date", "📰 Industry News"),
    ("Competitors", "Date",           "🔍 Competitor Intelligence"),
    ("Archive",     "Published Date", "📦 Archive"),
]

# ── GOOGLE SHEETS ─────────────────────────────────────────────
def get_sheet_client():
    creds_raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if creds_raw:
        creds_info = json.loads(creds_raw)
    else:
        with open("service_account.json") as f:
            creds_info = json.load(f)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)

def load_tab(gc, tab_name):
    try:
        ws   = gc.open(SHEET_NAME).worksheet(tab_name)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"[WARN] Could not load '{tab_name}': {e}")
        return pd.DataFrame()

# ── FILTER & SORT ─────────────────────────────────────────────
def filter_new(df, date_col, cutoff):
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["_dt"] = pd.to_datetime(df[date_col].fillna(""), errors="coerce")
    new = df[df["_dt"] >= cutoff].copy()
    if new.empty:
        return new
    pri_order = {"high": 0, "medium": 1, "low": 2}
    if "Priority" in new.columns:
        new["_pri"] = new["Priority"].fillna("").str.strip().str.lower().map(
            lambda p: pri_order.get(p, 3))
        new = new.sort_values(["_pri", "_dt"], ascending=[True, False])
        new = new.drop(columns=["_pri"])
    return new.drop(columns=["_dt"])

# ── EMAIL HTML ────────────────────────────────────────────────
def clean(text, max_len=200):
    t = str(text or "")
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'[#*_`>~]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return (t[:max_len] + "…") if len(t) > max_len else t

def priority_badge(p):
    pc = str(p).strip().lower()
    styles = {
        "high":   ("background:#fef2f2;color:#991b1b;border:1px solid #fecaca;", "HIGH"),
        "medium": ("background:#fffbeb;color:#92400e;border:1px solid #fde68a;", "MED"),
        "low":    ("background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;", "LOW"),
    }
    if pc not in styles: return ""
    style, label = styles[pc]
    return f'<span style="font-family:monospace;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;{style}margin-right:4px;">{label}</span>'

def ta_badge(ta):
    if not ta or ta.strip() in ("-", ""): return ""
    return f'<span style="font-family:monospace;font-size:10px;font-weight:500;padding:2px 6px;border-radius:4px;background:#fef3c7;color:#92400e;border:1px solid #fde68a;margin-right:4px;">{ta}</span>'

def src_badge(src):
    if not src or src.strip() in ("-", ""): return ""
    return f'<span style="font-family:monospace;font-size:10px;padding:2px 6px;border-radius:4px;background:#f3f3f2;color:#6b6b66;border:1px solid #e4e4e2;">{src}</span>'

def render_item(row):
    title   = clean(row.get("Title",   ""), 180) or "Untitled"
    url     = str(row.get("URL",       "")).strip()
    summary = clean(row.get("AI Summary", row.get("Summary", "")))
    pri     = str(row.get("Priority",  "")).strip()
    ta      = clean(row.get("Therapeutic Area", ""), 60)
    src     = clean(row.get("Source",  ""), 60)
    pub     = clean(row.get("Published Date", row.get("Date", "")), 16)

    title_html = f'<a href="{url}" style="color:#1a1a18;text-decoration:none;font-weight:600;font-size:13px;">{title}</a>' if url else f'<strong style="font-size:13px;">{title}</strong>'
    left_color = {"high":"#991b1b","medium":"#d97706","low":"#16a34a"}.get(pri.lower(),"#e4e4e2")
    badges = priority_badge(pri) + ta_badge(ta) + src_badge(src)

    return f"""
    <tr><td style="padding:0 0 8px 0;">
      <div style="background:#fff;border:1px solid #e4e4e2;border-radius:7px;padding:14px 16px;border-left:3px solid {left_color};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px;">
          <div style="flex:1;line-height:1.45;">{title_html}</div>
          <div style="font-family:monospace;font-size:10px;color:#a3a39e;white-space:nowrap;padding-left:12px;padding-top:2px;">{pub}</div>
        </div>
        <div style="font-size:12px;color:#6b6b66;line-height:1.6;margin-bottom:8px;">{summary}</div>
        <div>{badges}</div>
      </div>
    </td></tr>"""

def build_section(label, df):
    if df.empty: return ""
    items = "".join(render_item(row) for _, row in df.iterrows())
    return f"""
    <tr><td style="padding:24px 0 8px 0;">
      <div style="font-size:14px;font-weight:700;color:#1a1a18;border-bottom:2px solid #1a1a18;padding-bottom:6px;">
        {label} <span style="font-size:11px;font-weight:400;color:#a3a39e;">({len(df)} new)</span>
      </div>
    </td></tr>
    {items}"""

def build_html(sections, now_str, total):
    body = "".join(sections)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8f8f7;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f7;padding:32px 16px;">
<tr><td>
<table width="100%" cellpadding="0" cellspacing="0"
       style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #e4e4e2;border-radius:10px;overflow:hidden;">
  <tr><td style="background:#1a1a18;padding:22px 28px;">
    <div style="font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;">
      RI <span style="font-weight:300;opacity:.6;font-size:14px;">Regulatory Intelligence</span>
    </div>
    <div style="font-size:11px;color:#a3a39e;margin-top:4px;font-family:monospace;">
      Daily Digest · {now_str} · {total} new item{"s" if total != 1 else ""}
    </div>
  </td></tr>
  <tr><td style="padding:8px 28px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0">{body}</table>
  </td></tr>
  <tr><td style="background:#f3f3f2;padding:16px 28px;border-top:1px solid #e4e4e2;">
    <div style="font-size:10.5px;color:#a3a39e;font-family:monospace;">
      Regulatory Intelligence Platform · Auto-generated digest<br>
      Items from the last 24 hours · Sorted by priority then date
    </div>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

# ── SEND VIA GMAIL SMTP ───────────────────────────────────────
def send_email(html_content, subject, recipients):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, recipients, msg.as_string())
    print(f"[INFO] Email sent to {recipients}")

# ── MAIN ──────────────────────────────────────────────────────
def main():
    now     = datetime.now(BRT)
    cutoff  = now - timedelta(hours=24)
    now_str = now.strftime("%a, %b %d %Y · %H:%M BRT")
    print(f"[INFO] Digest for {now_str} (cutoff: {cutoff})")

    gc       = get_sheet_client()
    sections = []
    total    = 0

    for tab_name, date_col, label in TABS:
        df  = load_tab(gc, tab_name)
        new = filter_new(df, date_col, cutoff)
        print(f"[INFO] {tab_name}: {len(new)} new items")
        if not new.empty:
            sections.append(build_section(label, new))
            total += len(new)

    if total == 0:
        print("[INFO] No new items — skipping email.")
        return

    subject    = f"RI Daily Digest — {total} new item{'s' if total != 1 else ''} · {now.strftime('%b %d')}"
    html       = build_html(sections, now_str, total)
    recipients = [e.strip() for e in TO_EMAIL.split(",") if e.strip()]
    send_email(html, subject, recipients)
    print(f"[INFO] Done — {total} items sent.")

if __name__ == "__main__":
    main()
