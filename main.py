from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import threading

app = FastAPI(title="RIP - Regulatory Intelligence API")

# ── CORS (permite o HTML do GitHub Pages chamar a API) ──────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, troque pelo seu domínio GitHub Pages
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── CONFIG ───────────────────────────────────────────────────────────────────
SHEET_NAME = "Raw Intelligence"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Credenciais: coloque o JSON da service account em GCP_SERVICE_ACCOUNT (env var)
# ou num arquivo credentials.json na mesma pasta
def get_credentials():
    raw = os.environ.get("GCP_SERVICE_ACCOUNT")
    if raw:
        return json.loads(raw)
    with open("credentials.json") as f:
        return json.load(f)

def get_client():
    creds = Credentials.from_service_account_info(get_credentials(), scopes=SCOPES)
    return gspread.authorize(creds)

def load_tab(tab_name: str) -> list[dict]:
    try:
        gc = get_client()
        ws = gc.open(SHEET_NAME).worksheet(tab_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame()
        if tab_name == "Favorites" and not df.empty and "Deleted" in df.columns:
            df = df[df["Deleted"].fillna("") != "deleted"]
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load '{tab_name}': {e}")

# ── MODELS ────────────────────────────────────────────────────────────────────
class FavoriteItem(BaseModel):
    Title: str
    URL: Optional[str] = ""
    Source: Optional[str] = ""
    Published_Date: Optional[str] = ""
    Priority: Optional[str] = ""
    Therapeutic_Area: Optional[str] = ""
    AI_Summary: Optional[str] = ""

class RemoveFavorite(BaseModel):
    title: str

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "service": "RIP API"}

@app.get("/api/updates")
def get_updates():
    return load_tab("Updates")

@app.get("/api/news")
def get_news():
    return load_tab("News")

@app.get("/api/competitors")
def get_competitors():
    return load_tab("Competitors")

@app.get("/api/archive")
def get_archive():
    return load_tab("Archive")

@app.get("/api/favorites")
def get_favorites():
    return load_tab("Favorites")

@app.post("/api/favorites")
def save_favorite(item: FavoriteItem):
    try:
        gc = get_client()
        ss = gc.open(SHEET_NAME)
        try:
            ws = ss.worksheet("Favorites")
        except Exception:
            ws = ss.add_worksheet("Favorites", rows=1000, cols=20)
            ws.append_row(["Title","URL","Source","Published Date","Priority",
                           "Therapeutic Area","AI Summary","Saved At","Deleted"])
        BR_TZ = timezone(timedelta(hours=-3))
        saved_at = datetime.now(BR_TZ).strftime("%Y-%m-%d %H:%M")
        ws.append_row([
            item.Title, item.URL, item.Source, item.Published_Date,
            item.Priority, item.Therapeutic_Area, item.AI_Summary,
            saved_at, ""
        ])
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/favorites")
def remove_favorite(body: RemoveFavorite):
    def _remove():
        try:
            gc = get_client()
            ws = gc.open(SHEET_NAME).worksheet("Favorites")
            all_rows = ws.get_all_values()
            for row_num, r in enumerate(all_rows[1:], start=2):
                if r and r[0] == body.title:
                    ws.update_cell(row_num, 9, "deleted")
                    break
        except Exception:
            pass
    threading.Thread(target=_remove, daemon=True).start()
    return {"status": "removed"}
