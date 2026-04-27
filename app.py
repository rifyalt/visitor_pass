"""
╔══════════════════════════════════════════════════════════════════╗
║     MITRA TOURS & TRAVEL — Visitor Appointment System           ║
║     Streamlit App — app.py                                      ║
║     Semua secrets dibaca dari .streamlit/secrets.toml           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import requests
import random
import string
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import os
import re

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG — harus baris pertama setelah import
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Visitor Appointment — Mitra Tours & Travel",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
# SECRETS — dibaca dari .streamlit/secrets.toml
# ══════════════════════════════════════════════════════════════════
SHEET_ID   = st.secrets["google_sheets"]["sheet_id"]
API_KEY    = st.secrets["google_sheets"]["api_key"]
SHEET_NAME = st.secrets["google_sheets"]["sheet_name"]

SHEETS_READ_URL = (
    f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
    f"/values/{SHEET_NAME}?key={API_KEY}"
)
SHEETS_APPEND_URL = (
    f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
    f"/values/{SHEET_NAME}:append?valueInputOption=USER_ENTERED&key={API_KEY}"
)

# ══════════════════════════════════════════════════════════════════
# JADWAL — ubah tanggal & sesi di sini
# ══════════════════════════════════════════════════════════════════
DATES = [
    {"key": "6 Mei 2025",  "label": "Selasa, 6 Mei 2025"},
    {"key": "13 Mei 2025", "label": "Selasa, 13 Mei 2025"},
    {"key": "20 Mei 2025", "label": "Selasa, 20 Mei 2025"},
    {"key": "27 Mei 2025", "label": "Selasa, 27 Mei 2025"},
]

SESSIONS = [
    {"id": "P1", "value": "Pagi 09.00–10.00 WIB",  "label": "🌅  Pagi   09.00 – 10.00 WIB"},
    {"id": "P2", "value": "Pagi 10.00–11.00 WIB",  "label": "🌅  Pagi   10.00 – 11.00 WIB"},
    {"id": "S1", "value": "Siang 13.30–14.30 WIB", "label": "☀️  Siang  13.30 – 14.30 WIB"},
    {"id": "S2", "value": "Siang 14.30–15.30 WIB", "label": "☀️  Siang  14.30 – 15.30 WIB"},
]

HOTEL_BRANDS = [
    "", "Accor", "Aman Resorts", "Archipelago International",
    "Banyan Group Limited", "Best Western Hotels", "Dusit International",
    "Four Seasons Hotels and Resorts", "Hilton Worldwide",
    "Hyatt Hotels Corporation", "IHG Hotels & Resorts", "Jumeirah",
    "Kempinski", "Langham Hospitality Group", "Mandarin Oriental Hotel Group",
    "Marriott International", "Meliá Hotels International",
    "MGM Resorts International", "Minor Hotels", "Oberoi Group",
    "Pan Pacific Hotels and Resorts", "Radisson Hotel Group",
    "Rosewood Hotel Group", "Shangri-La Hotels and Resorts",
    "Wyndham Hotels & Resorts", "Independen / Tidak Berantai", "Lainnya",
]

TUJUAN_OPTIONS = [
    "Perkenalan Hotel",
    "Presentasi Produk / Fasilitas",
    "Corporate Rate / Contract Rate",
    "Promo / Special Offer",
    "Kerja Sama Partnership",
    "Follow Up Existing Business",
]

# ══════════════════════════════════════════════════════════════════
# LOGO
# ══════════════════════════════════════════════════════════════════
def get_logo_b64() -> str:
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "LOGO-MITRA-putih 2.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

LOGO_B64 = get_logo_b64()
LOGO_SRC = f"data:image/png;base64,{LOGO_B64}" if LOGO_B64 else ""

# ══════════════════════════════════════════════════════════════════
# GOOGLE SHEETS — helper functions (semua request server-side)
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30)   # cache 30 detik — refresh otomatis
def _fetch_booked_slots_cached() -> tuple[dict, str]:
    """
    INTERNAL — jangan panggil langsung. Gunakan fetch_booked_slots().
    Tidak boleh ada st.* call di dalam fungsi @st.cache_data.
    Mengembalikan (booked_dict, error_message).
    """
    try:
        resp = requests.get(SHEETS_READ_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("values", [])[1:]  # skip header baris 1

        booked: dict = {}
        for row in rows:
            # Pad row jika kurang dari 16 kolom
            while len(row) < 16:
                row.append("")
            status = row[15].lower().strip()
            if status in ("ditolak", "dibatalkan"):
                continue
            date_raw = row[11].strip()
            slot_val = row[12].strip()
            if not date_raw or not slot_val:
                continue
            # Normalisasi tanggal: hilangkan "(Selasa)" dll
            date_key = re.sub(r"\s*\(.*?\)", "", date_raw).strip()
            key = f"{date_key}|{slot_val}"
            booked[key] = booked.get(key, 0) + 1
        return booked, ""
    except Exception as e:
        return {}, str(e)


def fetch_booked_slots() -> dict:
    """
    Wrapper publik — panggil fungsi cached, tampilkan error di UI jika ada.
    Aman dipanggil dari mana saja karena st.toast() ada di sini, bukan di cache.
    """
    booked, err = _fetch_booked_slots_cached()
    if err:
        st.toast(f"⚠️ Gagal memuat jadwal: {err}", icon="⚠️")
    return booked


def is_booked(booked: dict, date_key: str, session_value: str) -> bool:
    return booked.get(f"{date_key}|{session_value}", 0) >= 1


def get_alternatives(booked: dict, exc_date: str, exc_sess: str, max_n: int = 3) -> list:
    alts = []
    for d in DATES:
        for s in SESSIONS:
            if d["key"] == exc_date and s["value"] == exc_sess:
                continue
            if not is_booked(booked, d["key"], s["value"]):
                alts.append({
                    "date_key":   d["key"],
                    "date_label": d["label"],
                    "sess_value": s["value"],
                    "sess_label": s["label"],
                })
                if len(alts) >= max_n:
                    return alts
    return alts


def generate_ref() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=7))
    return f"SV-{suffix}"


def append_to_sheet(row_data: list) -> bool:
    """Tulis satu baris baru ke Google Sheets."""
    try:
        resp = requests.post(
            SHEETS_APPEND_URL,
            json={"values": [row_data]},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        st.toast(f"❌ Gagal menyimpan: {e}", icon="❌")
        return False

# ══════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
/* ── Import font ── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* ── Remove top padding ── */
.main .block-container {
  padding-top: 0 !important;
  padding-left: 1rem !important;
  padding-right: 1rem !important;
  max-width: 760px !important;
}

/* ── TOPBAR ── */
.mtr-topbar {
  background: #1D4ED8;
  margin: -1rem -1rem 0 -1rem;
  padding: 0 28px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mtr-topbar-right {
  font-size: 12px;
  color: rgba(255,255,255,.6);
  font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── HERO ── */
.mtr-hero {
  background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 55%, #0BA5EC 100%);
  margin: 0 -1rem;
  padding: 36px 32px 72px;
  position: relative;
  overflow: hidden;
}
.mtr-hero::after {
  content: '';
  position: absolute;
  right: -60px; top: -60px;
  width: 300px; height: 300px;
  border-radius: 50%;
  background: rgba(255,255,255,.04);
  pointer-events: none;
}
.mtr-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 20px;
  padding: 4px 13px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,.9);
  letter-spacing: .7px;
  text-transform: uppercase;
  margin-bottom: 14px;
}
.mtr-pulse {
  width: 7px; height: 7px;
  background: #4ADE80;
  border-radius: 50%;
  display: inline-block;
  animation: mtr-pls 1.8s ease-in-out infinite;
}
@keyframes mtr-pls {
  0%,100% { opacity:1; transform:scale(1); }
  50%      { opacity:.4; transform:scale(.75); }
}
.mtr-hero h1 {
  font-size: 28px !important;
  font-weight: 700 !important;
  color: white !important;
  letter-spacing: -.5px;
  margin-bottom: 8px !important;
  line-height: 1.25 !important;
}
.mtr-hero p {
  font-size: 14px;
  color: rgba(255,255,255,.75);
  max-width: 480px;
  line-height: 1.65;
}
.mtr-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}
.mtr-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 11.5px;
  color: rgba(255,255,255,.85);
  font-weight: 500;
}

/* ── STEP INDICATOR ── */
.mtr-steps {
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px 20px;
  margin: -36px 0 16px;
  position: relative;
  z-index: 10;
  box-shadow: 0 4px 16px rgba(30,64,175,.08);
}
.mtr-step { display:flex; align-items:center; gap:8px; flex:1; }
.mtr-step-circle {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
  flex-shrink: 0;
  border: 1.5px solid #E2E8F0;
  color: #94A3B8;
  background: #F1F5F9;
}
.mtr-step-circle.active { background:#2563EB; color:white; border-color:#2563EB; }
.mtr-step-circle.done   { background:#EFF6FF; color:#2563EB; border-color:#BFDBFE; }
.mtr-step-label { font-size:12px; color:#94A3B8; font-weight:500; white-space:nowrap; }
.mtr-step-label.active { color:#2563EB; font-weight:600; }
.mtr-step-label.done   { color:#64748B; }
.mtr-connector { flex:1; height:1.5px; background:#E2E8F0; margin:0 6px; max-width:48px; }
.mtr-connector.done { background:#BFDBFE; }

/* ── SECTION CARD ── */
.mtr-card {
  background: white;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 28px 30px;
  margin-bottom: 14px;
  box-shadow: 0 4px 16px rgba(30,64,175,.06);
}
.mtr-card-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  padding-bottom: 18px;
  border-bottom: 1px solid #F1F5F9;
  margin-bottom: 22px;
}
.mtr-card-icon {
  width: 40px; height: 40px;
  background: #EFF6FF;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.mtr-step-tag {
  display: inline-block;
  background: #EFF6FF; color: #2563EB;
  font-size: 10px; font-weight: 700;
  padding: 2px 8px; border-radius: 10px;
  letter-spacing: .5px; text-transform: uppercase;
  margin-bottom: 5px;
}
.mtr-card-title {
  font-size: 17px !important;
  font-weight: 700 !important;
  color: #0F172A !important;
  letter-spacing: -.3px;
  margin: 0 !important;
}
.mtr-card-sub { font-size:13px; color:#94A3B8; margin-top:2px; }

/* ── SECTION LABEL ── */
.mtr-sec {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: #94A3B8;
  margin: 20px 0 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.mtr-sec::after { content:''; flex:1; height:1px; background:#F1F5F9; }

/* ── INFO BOX ── */
.mtr-info {
  display: flex;
  gap: 10px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13px;
  color: #1E40AF;
  line-height: 1.55;
  margin-bottom: 14px;
}

/* ── SLOT CARDS ── */
.mtr-date-card {
  border: 1.5px solid #E2E8F0;
  border-radius: 10px;
  margin-bottom: 10px;
  overflow: hidden;
  background: white;
}
.mtr-date-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
}
.mtr-date-name  { font-size:14px; font-weight:700; color:#0F172A; }
.mtr-date-day   { font-size:11.5px; color:#94A3B8; margin-top:1px; }
.mtr-badge-open    { background:#ECFDF5; color:#065F46; border:1px solid #6EE7B7; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }
.mtr-badge-partial { background:#FFFBEB; color:#92400E; border:1px solid #FCD34D; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }
.mtr-badge-full    { background:#FEF2F2; color:#991B1B; border:1px solid #FECACA; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }

/* ── ALERT ── */
.mtr-alert-block {
  background:#FEF2F2; border:1px solid #FECACA; border-left:3px solid #EF4444;
  border-radius:8px; padding:13px 15px; margin-bottom:12px; font-size:13px; color:#7F1D1D;
}
.mtr-alert-ok {
  background:#ECFDF5; border:1px solid #6EE7B7; border-left:3px solid #10B981;
  border-radius:8px; padding:13px 15px; margin-bottom:12px; font-size:13px; color:#065F46;
}
.mtr-alert-title { font-weight:700; margin-bottom:4px; font-size:13.5px; }

/* ── SELECTED BAR ── */
.mtr-sel-bar {
  background: #2563EB;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}
.mtr-sel-tag  { font-size:10.5px; font-weight:600; letter-spacing:.4px; text-transform:uppercase; color:rgba(255,255,255,.65); margin-bottom:3px; }
.mtr-sel-val  { font-size:13.5px; font-weight:700; color:white; }

/* ── REVIEW TABLE ── */
.mtr-review-row {
  display: flex;
  border: 1px solid #F1F5F9;
  border-radius: 7px;
  overflow: hidden;
  margin-bottom: 7px;
}
.mtr-review-label {
  width: 130px; flex-shrink:0;
  background: #F8FAFC;
  padding: 10px 13px;
  font-size: 11.5px; font-weight:600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: .3px;
}
.mtr-review-val {
  padding: 10px 14px;
  font-size: 13.5px; color: #1E293B;
  font-weight: 500; flex:1;
}

/* ── SUCCESS ── */
.mtr-success {
  text-align: center;
  padding: 48px 20px;
}
.mtr-success-icon {
  width: 72px; height: 72px;
  margin: 0 auto 20px;
  background: #ECFDF5;
  border: 2px solid #6EE7B7;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 30px;
}
.mtr-ref {
  display: inline-block;
  background: #F1F5F9; border:1px solid #E2E8F0;
  border-radius: 6px; padding: 7px 18px;
  font-size: 13px; color: #64748B;
  font-family: monospace; letter-spacing: 2px;
  margin: 12px 0 16px;
}
.mtr-succ-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px; max-width: 400px;
  margin: 16px auto 0; text-align:left;
}
.mtr-succ-item {
  background: #F8FAFC; border:1px solid #E2E8F0;
  border-radius: 7px; padding: 10px 13px;
}
.mtr-succ-label { font-size:10.5px; text-transform:uppercase; letter-spacing:.5px; color:#94A3B8; font-weight:600; margin-bottom:3px; }
.mtr-succ-val   { font-size:13.5px; font-weight:700; color:#0F172A; }

/* ── Streamlit widget overrides ── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] select {
  border: 1.5px solid #E2E8F0 !important;
  border-radius: 7px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13.5px !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: #3B82F6 !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,.1) !important;
}
div[data-testid="stCheckbox"] label { font-size: 13.5px !important; }
div[data-testid="stRadio"] label    { font-size: 13.5px !important; }

/* ── Primary button ── */
div[data-testid="stButton"] > button[kind="primary"] {
  background-color: #2563EB !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  padding: 10px 24px !important;
  transition: all .15s !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
  background-color: #1D4ED8 !important;
  box-shadow: 0 4px 14px rgba(37,99,235,.35) !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
  border: 1.5px solid #E2E8F0 !important;
  border-radius: 8px !important;
  color: #64748B !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  background: white !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "step": 1,
        # Step 1 — Hotel
        "nama_hotel": "",
        "alamat_hotel": "",
        "brand_hotel": "",
        # Step 2 — PIC
        "nama_pic": "",
        "jabatan": "",
        "no_hp": "",
        "email": "",
        "peserta": "1 orang (PIC saja)",
        # Step 3 — Jadwal
        "sel_date_key": None,
        "sel_date_label": None,
        "sel_sess_value": None,
        "sel_sess_label": None,
        "tujuan": [],
        "durasi": None,
        "catatan": "",
        # Result
        "ref_number": "",
        "submitted": False,
        # Conflict
        "conflict_type": None,   # None | "blocking" | "ok"
        "conflict_msg": "",
        "alternatives": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ══════════════════════════════════════════════════════════════════
def render_topbar():
    logo_img = f'<img src="{LOGO_SRC}" alt="Mitra Tours & Travel" style="height:30px;width:auto;object-fit:contain;filter:brightness(0) invert(1);">' if LOGO_SRC else '<span style="font-size:15px;font-weight:700;color:white">Mitra Tours & Travel</span>'
    st.markdown(f"""
<div class="mtr-topbar">
  <div>{logo_img}</div>
  <div class="mtr-topbar-right">Sales Visit Appointment System</div>
</div>
""", unsafe_allow_html=True)


def render_hero():
    logo_img = f'<img src="{LOGO_SRC}" alt="Mitra Tours & Travel" style="height:44px;width:auto;object-fit:contain;filter:brightness(0) invert(1);margin-bottom:16px;display:block;">' if LOGO_SRC else ""
    st.markdown(f"""
<div class="mtr-hero">
  {logo_img}
  <div class="mtr-hero-badge"><span class="mtr-pulse"></span> Sistem Kunjungan Aktif</div>
  <h1>Buat Janji Kunjungan Sales</h1>
  <p>Ajukan jadwal kunjungan ke kantor kami. Setiap slot hanya untuk <strong>satu hotel</strong> — sistem mendeteksi konflik secara real-time dari Google Sheets.</p>
  <div class="mtr-chips">
    <span class="mtr-chip">✓ Cek slot real-time</span>
    <span class="mtr-chip">📅 Hanya hari Selasa</span>
    <span class="mtr-chip">🔒 Anti double booking</span>
    <span class="mtr-chip">📱 Konfirmasi WhatsApp</span>
  </div>
</div>
""", unsafe_allow_html=True)


def render_steps(current: int):
    def circle(i):
        if i < current:
            return f'<div class="mtr-step-circle done">✓</div>'
        elif i == current:
            return f'<div class="mtr-step-circle active">{i}</div>'
        return f'<div class="mtr-step-circle">{i}</div>'

    def label_cls(i):
        if i < current:   return "done"
        if i == current:  return "active"
        return ""

    labels = ["Hotel", "Kontak", "Jadwal", "Konfirmasi"]
    html = '<div class="mtr-steps">'
    for i, lbl in enumerate(labels, 1):
        html += f'<div class="mtr-step">{circle(i)}<span class="mtr-step-label {label_cls(i)}">{lbl}</span></div>'
        if i < 4:
            conn_cls = "done" if i < current else ""
            html += f'<div class="mtr-connector {conn_cls}"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def card_header(icon: str, tag: str, title: str, subtitle: str):
    st.markdown(f"""
<div class="mtr-card-head">
  <div class="mtr-card-icon">{icon}</div>
  <div>
    <div class="mtr-step-tag">{tag}</div>
    <div class="mtr-card-title">{title}</div>
    <div class="mtr-card-sub">{subtitle}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def sec_label(text: str):
    st.markdown(f'<div class="mtr-sec">{text}</div>', unsafe_allow_html=True)


def info_box(text: str):
    st.markdown(f'<div class="mtr-info"><span>ℹ️</span><div>{text}</div></div>', unsafe_allow_html=True)


def alert_box(kind: str, title: str, body: str, alts: list = None):
    css = "mtr-alert-block" if kind == "blocking" else "mtr-alert-ok"
    html = f'<div class="{css}"><div class="mtr-alert-title">{title}</div><div>{body}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    if alts:
        st.markdown("**Pilih slot alternatif:**")
        for alt in alts:
            btn_label = f"→ {alt['date_label']}  ·  {alt['sess_label']}"
            if st.button(btn_label, key=f"alt_{alt['date_key']}_{alt['sess_value']}", use_container_width=True):
                st.session_state.sel_date_key   = alt["date_key"]
                st.session_state.sel_date_label = alt["date_label"]
                st.session_state.sel_sess_value = alt["sess_value"]
                st.session_state.sel_sess_label = alt["sess_label"]
                st.session_state.conflict_type  = "ok"
                st.session_state.conflict_msg   = f"✅ Slot dipilih: {alt['date_label']} · {alt['sess_label']}"
                st.session_state.alternatives   = []
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════════
def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email.strip()))


def validate_step1() -> bool:
    ok = True
    if not st.session_state.nama_hotel.strip():
        st.error("❌ Nama hotel wajib diisi", icon=None)
        ok = False
    if not st.session_state.alamat_hotel.strip():
        st.error("❌ Alamat hotel wajib diisi", icon=None)
        ok = False
    return ok


def validate_step2() -> bool:
    ok = True
    if not st.session_state.nama_pic.strip():
        st.error("❌ Nama PIC wajib diisi")
        ok = False
    if not st.session_state.jabatan.strip():
        st.error("❌ Jabatan wajib diisi")
        ok = False
    if not st.session_state.no_hp.strip():
        st.error("❌ Nomor WhatsApp wajib diisi")
        ok = False
    if not st.session_state.email.strip():
        st.error("❌ Email wajib diisi")
        ok = False
    elif not validate_email(st.session_state.email):
        st.error("❌ Format email tidak valid")
        ok = False
    return ok


def validate_step3(booked: dict) -> bool:
    ok = True
    if not st.session_state.sel_date_key or not st.session_state.sel_sess_value:
        st.error("❌ Pilih tanggal dan slot waktu kunjungan")
        ok = False
    elif is_booked(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value):
        alts = get_alternatives(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value)
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = f"Slot {st.session_state.sel_sess_label} pada {st.session_state.sel_date_label} baru saja diisi hotel lain."
        st.session_state.alternatives  = alts
        st.session_state.sel_date_key   = None
        st.session_state.sel_date_label = None
        st.session_state.sel_sess_value = None
        st.session_state.sel_sess_label = None
        ok = False
    if not st.session_state.tujuan:
        st.error("❌ Pilih minimal satu tujuan kunjungan")
        ok = False
    if not st.session_state.durasi:
        st.error("❌ Estimasi durasi wajib dipilih")
        ok = False
    return ok

# ══════════════════════════════════════════════════════════════════
# STEP 1 — HOTEL INFO
# ══════════════════════════════════════════════════════════════════
def render_step1():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("🏨", "Langkah 1 dari 3", "Informasi Hotel", "Data properti hotel atau perusahaan Anda")

    st.session_state.nama_hotel = st.text_input(
        "Nama Hotel / Property *",
        value=st.session_state.nama_hotel,
        placeholder="Contoh: Grand Hyatt Jakarta",
        key="inp_nama_hotel",
    )
    st.session_state.alamat_hotel = st.text_area(
        "Alamat Hotel *",
        value=st.session_state.alamat_hotel,
        placeholder="Alamat lengkap hotel / properti Anda...",
        height=90,
        key="inp_alamat_hotel",
    )
    brand_opts = HOTEL_BRANDS
    cur_idx = brand_opts.index(st.session_state.brand_hotel) if st.session_state.brand_hotel in brand_opts else 0
    selected_brand = st.selectbox(
        "Brand / Chain Hotel",
        options=brand_opts,
        index=cur_idx,
        key="inp_brand_hotel",
        format_func=lambda x: "— Pilih Brand / Chain —" if x == "" else x,
    )
    st.session_state.brand_hotel = selected_brand

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Lanjut →", type="primary", use_container_width=True, key="btn1"):
            if validate_step1():
                st.session_state.step = 2
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# STEP 2 — PIC & CONTACT
# ══════════════════════════════════════════════════════════════════
def render_step2():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("👤", "Langkah 2 dari 3", "Data PIC & Kontak", "Informasi penanggung jawab kunjungan")

    st.session_state.nama_pic = st.text_input(
        "Nama PIC Utama *",
        value=st.session_state.nama_pic,
        placeholder="Nama lengkap",
        key="inp_nama_pic",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.session_state.jabatan = st.text_input(
            "Jabatan / Posisi *",
            value=st.session_state.jabatan,
            placeholder="Sales Manager, GM, dll",
            key="inp_jabatan",
        )
    with c2:
        st.session_state.no_hp = st.text_input(
            "Nomor WhatsApp *",
            value=st.session_state.no_hp,
            placeholder="08xx-xxxx-xxxx",
            key="inp_no_hp",
        )

    st.session_state.email = st.text_input(
        "Alamat Email *",
        value=st.session_state.email,
        placeholder="nama@hotel.com",
        key="inp_email",
    )

    sec_label("Jumlah Peserta")
    peserta_opts = ["1 orang (PIC saja)", "2 orang", "3 orang", "4 orang", "5 orang"]
    cur_p = peserta_opts.index(st.session_state.peserta) if st.session_state.peserta in peserta_opts else 0
    st.session_state.peserta = st.radio(
        "Jumlah Peserta",
        options=peserta_opts,
        index=cur_p,
        horizontal=True,
        label_visibility="collapsed",
        key="inp_peserta",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Kembali", key="btn2_back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("Lanjut →", type="primary", key="btn2_next", use_container_width=True):
            if validate_step2():
                st.session_state.step = 3
                # Clear cache so schedule is fresh
                _fetch_booked_slots_cached.clear()
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# STEP 3 — SCHEDULE
# ══════════════════════════════════════════════════════════════════
def render_step3():
    booked = fetch_booked_slots()

    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("📅", "Langkah 3 dari 3", "Pilih Jadwal Kunjungan", "Slot terisi ditandai otomatis — real-time dari Google Sheets")

    info_box("Kunjungan hanya diterima setiap <strong>Selasa</strong> dalam 4 slot waktu. Setiap slot hanya untuk <strong>1 hotel</strong>.")

    # ── Conflict alert ──
    if st.session_state.conflict_type == "blocking":
        alert_box(
            "blocking",
            "⛔ Slot tidak tersedia!",
            st.session_state.conflict_msg,
            st.session_state.alternatives,
        )
    elif st.session_state.conflict_type == "ok":
        alert_box("ok", "✅ Slot tersedia!", st.session_state.conflict_msg)

    sec_label("Pilih Tanggal & Slot Waktu")

    # ── Slot grid ──
    for dt in DATES:
        sess_free  = [s for s in SESSIONS if not is_booked(booked, dt["key"], s["value"])]
        sess_taken = [s for s in SESSIONS if is_booked(booked, dt["key"], s["value"])]
        all_full   = len(sess_free) == 0
        badge_cls  = "mtr-badge-full" if all_full else ("mtr-badge-partial" if sess_taken else "mtr-badge-open")
        badge_txt  = "Penuh" if all_full else (f"{len(sess_free)} slot tersisa" if sess_taken else f"{len(sess_free)} slot tersedia")

        st.markdown(f"""
<div class="mtr-date-card">
  <div class="mtr-date-head">
    <div>
      <div class="mtr-date-name">{dt['label']}</div>
    </div>
    <span class="{badge_cls}">{badge_txt}</span>
  </div>
</div>
""", unsafe_allow_html=True)

        if all_full:
            st.markdown(
                '<p style="font-size:12.5px;color:#94A3B8;padding:0 16px 10px">Semua slot pada tanggal ini sudah penuh.</p>',
                unsafe_allow_html=True,
            )
        else:
            cols = st.columns(2)
            for i, sess in enumerate(SESSIONS):
                taken = is_booked(booked, dt["key"], sess["value"])
                is_picked = (
                    st.session_state.sel_date_key == dt["key"]
                    and st.session_state.sel_sess_value == sess["value"]
                )
                col = cols[i % 2]
                with col:
                    if taken:
                        st.markdown(
                            f'<div style="border:1.5px solid #FECACA;background:#FEF2F2;border-radius:8px;padding:10px 13px;margin-bottom:8px;opacity:.7;">'
                            f'<div style="font-size:11px;font-weight:700;color:#991B1B;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px;">Penuh</div>'
                            f'<div style="font-size:14px;font-weight:700;color:#9CA3AF;text-decoration:line-through;">{sess["label"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        picked_style = (
                            "border:2px solid #2563EB;background:#EFF6FF;"
                            if is_picked
                            else "border:1.5px solid #6EE7B7;background:#ECFDF5;"
                        )
                        label_color = "#1D4ED8" if is_picked else "#065F46"
                        time_color  = "#1E40AF" if is_picked else "#0F172A"
                        st.markdown(
                            f'<div style="{picked_style}border-radius:8px;padding:10px 13px;margin-bottom:8px;">'
                            f'<div style="font-size:11px;font-weight:700;color:{label_color};text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px;">{"✓ Dipilih" if is_picked else "Tersedia"}</div>'
                            f'<div style="font-size:14px;font-weight:700;color:{time_color};">{sess["label"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        btn_text = f"{'✓ ' if is_picked else ''}Pilih"
                        if st.button(
                            btn_text,
                            key=f"slot_{dt['key']}_{sess['id']}",
                            use_container_width=True,
                        ):
                            # Re-check saat klik
                            _fetch_booked_slots_cached.clear()
                            fresh = fetch_booked_slots()
                            if is_booked(fresh, dt["key"], sess["value"]):
                                alts = get_alternatives(fresh, dt["key"], sess["value"])
                                st.session_state.conflict_type = "blocking"
                                st.session_state.conflict_msg  = f"Slot {sess['label']} pada {dt['label']} baru saja diisi hotel lain."
                                st.session_state.alternatives  = alts
                            else:
                                st.session_state.sel_date_key   = dt["key"]
                                st.session_state.sel_date_label = dt["label"]
                                st.session_state.sel_sess_value = sess["value"]
                                st.session_state.sel_sess_label = sess["label"]
                                st.session_state.conflict_type  = "ok"
                                st.session_state.conflict_msg   = f"<strong>{dt['label']}</strong> · <strong>{sess['label']}</strong> masih kosong dan siap di-booking."
                                st.session_state.alternatives   = []
                            st.rerun()

    # ── Selected bar ──
    if st.session_state.sel_date_key and st.session_state.sel_sess_value:
        st.markdown(f"""
<div class="mtr-sel-bar">
  <div>
    <div class="mtr-sel-tag">Jadwal dipilih</div>
    <div class="mtr-sel-val">{st.session_state.sel_date_label}  ·  {st.session_state.sel_sess_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        if st.button("✕ Batalkan pilihan", key="clear_slot"):
            st.session_state.sel_date_key   = None
            st.session_state.sel_date_label = None
            st.session_state.sel_sess_value = None
            st.session_state.sel_sess_label = None
            st.session_state.conflict_type  = None
            st.session_state.alternatives   = []
            st.rerun()

    # ── Tujuan ──
    st.markdown("<hr style='border:none;border-top:1px solid #F1F5F9;margin:18px 0'>", unsafe_allow_html=True)
    sec_label("Tujuan Kunjungan")

    tujuan_selected = []
    cols = st.columns(2)
    for i, tuj in enumerate(TUJUAN_OPTIONS):
        with cols[i % 2]:
            checked = tuj in st.session_state.tujuan
            if st.checkbox(tuj, value=checked, key=f"tuj_{i}"):
                tujuan_selected.append(tuj)
    st.session_state.tujuan = tujuan_selected

    # ── Durasi ──
    sec_label("Estimasi Durasi")
    durasi_opts = ["15 Menit", "30 Menit", "45 Menit"]
    cur_d = durasi_opts.index(st.session_state.durasi) if st.session_state.durasi in durasi_opts else 0
    st.session_state.durasi = st.radio(
        "Durasi",
        options=durasi_opts,
        index=cur_d,
        horizontal=True,
        label_visibility="collapsed",
        key="inp_durasi",
    )

    # ── Catatan ──
    sec_label("Catatan Tambahan")
    st.session_state.catatan = st.text_area(
        "Catatan",
        value=st.session_state.catatan,
        placeholder="Informasi tambahan yang ingin disampaikan (opsional)...",
        height=80,
        label_visibility="collapsed",
        key="inp_catatan",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Kembali", key="btn3_back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("Review Data →", type="primary", key="btn3_next", use_container_width=True):
            fresh_booked = fetch_booked_slots()
            if validate_step3(fresh_booked):
                st.session_state.step = 4
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# STEP 4 — REVIEW & SUBMIT
# ══════════════════════════════════════════════════════════════════
def render_step4():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("📋", "Konfirmasi", "Review Permohonan", "Periksa kembali sebelum mengirim")

    rows = [
        ("Hotel",    st.session_state.nama_hotel),
        ("Alamat",   st.session_state.alamat_hotel),
        ("Brand",    st.session_state.brand_hotel or "—"),
        ("Nama PIC", st.session_state.nama_pic),
        ("Jabatan",  st.session_state.jabatan),
        ("WhatsApp", st.session_state.no_hp),
        ("Email",    st.session_state.email),
        ("Peserta",  st.session_state.peserta),
        ("Tanggal",  st.session_state.sel_date_label or "—"),
        ("Slot",     st.session_state.sel_sess_label or "—"),
        ("Durasi",   st.session_state.durasi or "—"),
        ("Tujuan",   ", ".join(st.session_state.tujuan) or "—"),
    ]
    if st.session_state.catatan:
        rows.append(("Catatan", st.session_state.catatan))

    review_html = ""
    for label, val in rows:
        review_html += f'<div class="mtr-review-row"><div class="mtr-review-label">{label}</div><div class="mtr-review-val">{val}</div></div>'
    st.markdown(review_html, unsafe_allow_html=True)

    info_box("Dengan mengirimkan formulir ini, Anda menyetujui data yang diisi adalah benar dan bersedia dihubungi via WhatsApp atau Email untuk konfirmasi jadwal kunjungan.")

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Edit Data", key="btn4_back", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("✉️  Kirim Permohonan", type="primary", key="btn4_submit", use_container_width=True):
            do_submit()


def do_submit():
    # ── Final slot check sebelum tulis ──
    _fetch_booked_slots_cached.clear()
    fresh = fetch_booked_slots()

    dk = st.session_state.sel_date_key
    sv = st.session_state.sel_sess_value

    if is_booked(fresh, dk, sv):
        alts = get_alternatives(fresh, dk, sv)
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = (
            f"Slot {st.session_state.sel_sess_label} pada "
            f"{st.session_state.sel_date_label} baru saja dipesan hotel lain saat Anda submit."
        )
        st.session_state.alternatives  = alts
        st.session_state.sel_date_key   = None
        st.session_state.sel_date_label = None
        st.session_state.sel_sess_value = None
        st.session_state.sel_sess_label = None
        st.session_state.step = 3
        st.error("❌ Slot sudah terisi — pilih jadwal lain")
        st.rerun()
        return

    # ── Tulis ke Sheets ──
    ref = generate_ref()
    wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    ts  = wib.strftime("%d/%m/%Y %H:%M:%S")

    row_data = [
        ts,
        ref,
        st.session_state.nama_hotel,
        st.session_state.alamat_hotel,
        st.session_state.brand_hotel or "—",
        st.session_state.nama_pic,
        st.session_state.jabatan,
        st.session_state.no_hp,
        st.session_state.email,
        st.session_state.peserta,
        ", ".join(st.session_state.tujuan),
        st.session_state.sel_date_key + " (Selasa)",
        st.session_state.sel_sess_value,
        st.session_state.durasi or "",
        st.session_state.catatan or "",
        "Menunggu Konfirmasi",
    ]

    with st.spinner("Menyimpan permohonan..."):
        ok = append_to_sheet(row_data)

    if ok:
        st.session_state.ref_number = ref
        st.session_state.submitted  = True
        st.session_state.step       = 5
        _fetch_booked_slots_cached.clear()
        st.rerun()
    else:
        st.error("❌ Gagal menyimpan permohonan. Coba lagi.")

# ══════════════════════════════════════════════════════════════════
# STEP 5 — SUCCESS
# ══════════════════════════════════════════════════════════════════
def render_success():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    st.markdown(f"""
<div class="mtr-success">
  <div class="mtr-success-icon">✓</div>
  <h2 style="font-size:20px;font-weight:700;color:#0F172A;letter-spacing:-.3px;margin-bottom:6px">Permohonan Berhasil Dikirim!</h2>
  <p style="font-size:14px;color:#64748B;max-width:400px;margin:0 auto;line-height:1.65">
    Terima kasih! Permohonan kunjungan Anda sudah kami terima.<br>
    Konfirmasi akan dikirimkan dalam 1–2 hari kerja.
  </p>
  <div class="mtr-ref">{st.session_state.ref_number}</div>
  <p style="font-size:12.5px;color:#94A3B8;margin-bottom:0">Simpan nomor referensi ini untuk keperluan tindak lanjut.</p>
  <div class="mtr-succ-grid">
    <div class="mtr-succ-item"><div class="mtr-succ-label">Nama PIC</div><div class="mtr-succ-val">{st.session_state.nama_pic}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Hotel</div><div class="mtr-succ-val">{st.session_state.nama_hotel}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Tanggal</div><div class="mtr-succ-val">{st.session_state.sel_date_label}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Slot</div><div class="mtr-succ-val">{st.session_state.sel_sess_label}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("+ Ajukan Kunjungan Baru", key="btn_reset", use_container_width=False):
        # Reset semua state kecuali yang sudah clear
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    init_state()
    inject_css()

    render_topbar()
    render_hero()

    # Container utama
    with st.container():
        current_step = st.session_state.step

        if current_step < 5:
            render_steps(current_step)

        if current_step == 1:
            render_step1()
        elif current_step == 2:
            render_step2()
        elif current_step == 3:
            render_step3()
        elif current_step == 4:
            render_step4()
        elif current_step == 5:
            render_success()

    # Footer
    st.markdown("""
<div style="text-align:center;padding:20px 0 32px;font-size:12px;color:#94A3B8">
  VisitorPass · Mitra Tours &amp; Travel &nbsp;·&nbsp; Data tersimpan di Google Sheets
</div>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()