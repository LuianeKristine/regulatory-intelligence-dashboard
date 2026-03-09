"""
Regulatory Intelligence — Daily Email Digest
Roda todo dia às 08:00 (BRT) via cron ou GitHub Actions.
Lê o Google Sheets, filtra itens das últimas 24h e envia email via SendGrid.
"""

import os
import json
import gspread
import pandas as pd
from datetime import datetime, timedelta, timezone
from google.oauth2.service_account import Credentials
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ── CONFIG ────────────────────────────────────────────────────
SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]   # set as env var
FROM_EMAIL       = os.environ["FROM_EMAIL"]          # email verificado no SendGrid
TO_EMAIL         = os.environ["TO_EMAIL"]            # destinatário(s) — separe por vírgula
SHEET_NAME       = "Raw Intelligence"
SCOPES           = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Fuso horário BRT (UTC-3)
BRT = timezone(timedelta(hours=-3))

# Abas a monitorar: (nome_aba, coluna_de_data, label_no_email)
TABS = [
    ("Updates",     "Published Date", "🏛️ Regulatory Updates"),
    ("News",        "Published Date", "📰 Industry News"),
    ("Competitors", "Date",           "🔍 Competitor Intelligence"),
    ("Archive",     "Published Date", "📦 Archive"),
]

# ── GOOGLE SHEETS ─────────────────────────────────────────────
def get_sheet_client():
    # Aceita JSON como string (env var) ou como arquivo
    creds_raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if creds_raw:
        creds_info = json.loads(creds_raw)
    else:
        # fallback: arquivo local
        with open("service_account.json") as f:
            creds_info = json.load(f)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)

def load_tab(gc, tab_name):
    try:
        ws = gc.open(SHEET_NAME).worksheet(tab_name)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"[WARN] Could not load '{tab_name}': {e}")
        return pd.DataFrame()

# ── FILTER NEW ITEMS ──────────────────────────────────────────
def filter_new(df, date_col, cutoff):
    """Return rows where date_col is within the last 24h."""
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["_parsed_date"] = pd.to_datetime(df[date_col].fillna(""), errors="coerce")
    # Keep rows with a valid date >= cutoff
    new = df[df["_parsed_date"] >= cutoff].copy()
    # Sort: HIGH first, then most recent
    pri_order = {"high": 0, "medium": 1, "low": 2}
    if "Priority" in new.columns:
        new["_pri"] = new["Priority"].fillna("").str.strip().str.lower().map(
            lambda p: pri_order.get(p, 3)
        )
        new = new.sort_values(["_pri", "_parsed_date"], ascending=[True, False])
        new = new.drop(columns=["_pri"])
    new = new.drop(columns=["_parsed_date"])
    return new

# ── EMAIL BUILDER ─────────────────────────────────────────────
PRIORITY_COLORS = {
    "high":   ("#991b1b", "#fef2f2", "#fecaca"),
    "medium": ("#92400e", "#fffbeb", "#fde68a"),
    "low":    ("#166534", "#f0fdf4", "#bbf7d0"),
}

def priority_badge(p):
    pc = str(p).strip().lower()
    color, bg, border = PRIORITY_COLORS.get(pc, ("#6b6b66", "#f3f3f2", "#e4e4e2"))
    label = pc.upper() if pc in PRIORITY_COLORS else ""
    if not label:
        return ""
    return (
        f'<span style="font-family:monospace;font-size:10px;font-weight:700;'
        f'padding:2px 6px;border-radius:4px;background:{bg};color:{color};'
        f'border:1px solid {border};margin-right:4px;">{label}</span>'
    )

def ta_badge(ta):
    if not ta or str(ta).strip() in ("-", ""):
        return ""
    return (
        f'<span style="font-family:monospace;font-size:10px;font-weight:500;'
        f'padding:2px 6px;border-radius:4px;background:#fef3c7;color:#92400e;'
        f'border:1px solid #fde68a;margin-right:4px;">{ta}</span>'
    )

def source_badge(src):
    if not src or str(src).strip() in ("-", ""):
        return ""
    return (
        f'<span style="font-family:monospace;font-size:10px;font-weight:500;'
        f'padding:2px 6px;border-radius:4px;background:#f3f3f2;color:#6b6b66;'
        f'border:1px solid #e4e4e2;">{src}</span>'
    )

def render_item(row):
    title   = str(row.get("Title",   "")).strip() or "Untitled"
    url     = str(row.get("URL",     "")).strip()
    summary = str(row.get("AI Summary", row.get("Summary", ""))).strip()
    pri     = str(row.get("Priority", "")).strip()
    ta      = str(row.get("Therapeutic Area", "")).strip()
    src     = str(row.get("Source",  "")).strip()
    pub     = str(row.get("Published Date", row.get("Date", ""))).strip()[:16]

    title_html = (
        f'<a href="{url}" style="color:#1a1a18;text-decoration:none;font-weight:600;">{title}</a>'
        if url else f'<strong>{title}</strong>'
    )
    # summary: strip markdown/html, max 200 chars
    import re
    s = re.sub(r'<[^>]+>', ' ', summary)
    s = re.sub(r'[#*_`>~]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = (s[:200] + "…") if len(s) > 200 else s

    badges = priority_badge(pri) + ta_badge(ta) + source_badge(src)

    left_color = {
        "high": "#991b1b", "medium": "#d97706", "low": "#16a34a"
    }.get(pri.lower(), "#e4e4e2")

    return f"""
    <tr><td style="padding:0 0 8px 0;">
      <div style="background:#fff;border:1px solid #e4e4e2;border-radius:7px;
                  padding:14px 16px;border-left:3px solid {left_color};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px;">
          <div style="font-size:13px;line-height:1.45;flex:1;">{title_html}</div>
          <div style="font-family:monospace;font-size:10px;color:#a3a39e;
                      white-space:nowrap;padding-left:12px;padding-top:2px;">{pub}</div>
        </div>
        <div style="font-size:12px;color:#6b6b66;line-height:1.6;margin-bottom:8px;">{s}</div>
        <div>{badges}</div>
      </div>
    </td></tr>"""

def build_section(label, df):
    if df.empty:
        return ""
    items_html = "".join(render_item(row) for _, row in df.iterrows())
    return f"""
    <tr><td style="padding:24px 0 8px 0;">
      <div style="font-size:14px;font-weight:700;color:#1a1a18;
                  border-bottom:2px solid #1a1a18;padding-bottom:6px;margin-bottom:2px;">
        {label} <span style="font-size:11px;font-weight:400;color:#a3a39e;">({len(df)} new)</span>
      </div>
    </td></tr>
    {items_html}"""

def build_email_html(sections, now_str, total):
    sections_html = "".join(sections)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8f8f7;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f7;padding:32px 16px;">
    <tr><td>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="max-width:640px;margin:0 auto;background:#fff;
                    border:1px solid #e4e4e2;border-radius:10px;overflow:hidden;">

        <!-- HEADER -->
        <tr><td style="background:#1a1a18;padding:22px 28px;">
          <div style="font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;">
            RI <span style="font-weight:300;opacity:.6;font-size:14px;">Regulatory Intelligence</span>
          </div>
          <div style="font-size:11px;color:#a3a39e;margin-top:4px;font-family:monospace;">
            Daily Digest · {now_str} · {total} new item{"s" if total != 1 else ""}
          </div>
        </td></tr>

        <!-- BODY -->
        <tr><td style="padding:8px 28px 28px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            {sections_html}
          </table>
        </td></tr>

        <!-- FOOTER -->
        <tr><td style="background:#f3f3f2;padding:16px 28px;border-top:1px solid #e4e4e2;">
          <div style="font-size:10.5px;color:#a3a39e;font-family:monospace;">
            Regulatory Intelligence Platform · Auto-generated digest<br>
            Items from the last 24 hours · Sorted by priority then date
          </div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

# ── SEND ──────────────────────────────────────────────────────
def send_email(html_content, subject, recipients):
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    for to_addr in recipients:
        msg = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_addr.strip(),
            subject=subject,
            html_content=html_content,
        )
        response = sg.send(msg)
        print(f"[INFO] Sent to {to_addr} — status {response.status_code}")

# ── MAIN ──────────────────────────────────────────────────────
def main():
    now     = datetime.now(BRT)
    cutoff  = now - timedelta(hours=24)
    now_str = now.strftime("%a, %b %d %Y · %H:%M BRT")
    print(f"[INFO] Running digest for {now_str} (cutoff: {cutoff})")

    gc = get_sheet_client()
    sections = []
    total    = 0

    for tab_name, date_col, label in TABS:
        df   = load_tab(gc, tab_name)
        new  = filter_new(df, date_col, cutoff)
        print(f"[INFO] {tab_name}: {len(new)} new items")
        if not new.empty:
            sections.append(build_section(label, new))
            total += len(new)

    if total == 0:
        print("[INFO] No new items — skipping email.")
        return

    subject = f"RI Daily Digest — {total} new item{'s' if total != 1 else ''} · {now.strftime('%b %d')}"
    html    = build_email_html(sections, now_str, total)

    recipients = [e for e in TO_EMAIL.split(",") if e.strip()]
    send_email(html, subject, recipients)
    print(f"[INFO] Done — {total} items sent to {recipients}")

if __name__ == "__main__":
    main()
