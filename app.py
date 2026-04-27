"""
╔══════════════════════════════════════════════════════════════════╗
║     MITRA TOURS & TRAVEL — Visitor Appointment System           ║
║     app.py — Streamlit + Google Apps Script                     ║
║                                                                  ║
║  WRITE  → Google Apps Script (hardcoded, langsung jalan)        ║
║  READ   → Google Sheets API v4 (untuk cek slot)                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import requests
import random
import string
from datetime import datetime
from zoneinfo import ZoneInfo
import re

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Visitor Appointment — Mitra Tours & Travel",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
# KONFIGURASI — ubah di sini jika perlu ganti koneksi
# ══════════════════════════════════════════════════════════════════
GAS_ENDPOINT = "https://script.google.com/macros/s/AKfycbzm4Mnax-z0oq7Wao7Gz9C_tw4CgKLlyl0GfSTJGeIHAfhzSilZtQvr947Ym-1p2DqwkA/exec"
SHEET_ID     = "1AQz-w3sLjGVdOsneDmdTFHFW6Nx7Z337Kjw2zzqFoXI"
API_KEY      = "AIzaSyA1Mau8yZxao0MD5Mx_Dt027EuMbrUN9oo"
SHEET_NAME   = "Sheet1"

SHEETS_READ_URL = (
    f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
    f"/values/{SHEET_NAME}?key={API_KEY}"
)

# ══════════════════════════════════════════════════════════════════
# LOGO — dari URL eksternal
# ══════════════════════════════════════════════════════════════════
LOGO_SRC = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSktXTDoA1ptcm0zfQ8kJSpBq-FIwiXa_XTqA&s"

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
    {"id": "P1", "value": "Pagi 09.00-10.00 WIB",  "label": "\U0001f305  Pagi   09.00 - 10.00 WIB"},
    {"id": "P2", "value": "Pagi 10.00-11.00 WIB",  "label": "\U0001f305  Pagi   10.00 - 11.00 WIB"},
    {"id": "S1", "value": "Siang 13.30-14.30 WIB", "label": "\u2600\ufe0f  Siang  13.30 - 14.30 WIB"},
    {"id": "S2", "value": "Siang 14.30-15.30 WIB", "label": "\u2600\ufe0f  Siang  14.30 - 15.30 WIB"},
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
# GOOGLE SHEETS — READ (cek slot tersedia)
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30)
def _fetch_booked_cached() -> tuple:
    """Pure function — tidak boleh ada st.* call di sini."""
    try:
        resp = requests.get(SHEETS_READ_URL, timeout=10)
        resp.raise_for_status()
        rows = resp.json().get("values", [])[1:]
        booked = {}
        for row in rows:
            while len(row) < 16:
                row.append("")
            status = row[15].lower().strip()
            if status in ("ditolak", "dibatalkan"):
                continue
            date_raw = row[11].strip()
            slot_val = row[12].strip()
            if not date_raw or not slot_val:
                continue
            dk  = re.sub(r"\s*\(.*?\)", "", date_raw).strip()
            key = f"{dk}|{slot_val}"
            booked[key] = booked.get(key, 0) + 1
        return booked, ""
    except Exception as e:
        return {}, str(e)


def fetch_booked_slots() -> dict:
    booked, err = _fetch_booked_cached()
    if err:
        st.toast(f"\u26a0\ufe0f Gagal memuat jadwal: {err}", icon="\u26a0\ufe0f")
    return booked


def is_booked(booked: dict, date_key: str, sess_val: str) -> bool:
    return booked.get(f"{date_key}|{sess_val}", 0) >= 1


def get_alternatives(booked: dict, exc_dk: str, exc_sv: str, max_n: int = 3) -> list:
    alts = []
    for d in DATES:
        for s in SESSIONS:
            if d["key"] == exc_dk and s["value"] == exc_sv:
                continue
            if not is_booked(booked, d["key"], s["value"]):
                alts.append({"date_key": d["key"], "date_label": d["label"],
                             "sess_value": s["value"], "sess_label": s["label"]})
                if len(alts) >= max_n:
                    return alts
    return alts


# ══════════════════════════════════════════════════════════════════
# GOOGLE APPS SCRIPT — WRITE (simpan data)
# ══════════════════════════════════════════════════════════════════
def save_to_gas(payload: dict) -> tuple:
    """
    Kirim data ke Google Apps Script endpoint.
    GAS akan menulis ke Sheets dengan service account.
    Return: (sukses: bool, ref_or_error: str)
    """
    try:
        resp = requests.post(
            GAS_ENDPOINT,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )

        # GAS kadang redirect — requests otomatis follow redirect
        if not resp.ok:
            return False, f"HTTP {resp.status_code}: {resp.text[:300]}"

        try:
            result = resp.json()
        except Exception:
            # Jika response bukan JSON (misal redirect HTML)
            return False, f"Response bukan JSON: {resp.text[:200]}"

        if result.get("success"):
            return True, result.get("ref", "")
        elif result.get("error") == "SLOT_TAKEN":
            return False, "SLOT_TAKEN"
        else:
            return False, result.get("message", result.get("error", "Unknown error dari GAS"))

    except requests.exceptions.Timeout:
        return False, "Timeout (>30 detik) — coba lagi"
    except requests.exceptions.ConnectionError as e:
        return False, f"Koneksi gagal: {e}"
    except Exception as e:
        return False, str(e)


def generate_ref() -> str:
    return "SV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))


# ══════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "step": 1,
        "nama_hotel": "", "alamat_hotel": "", "brand_hotel": "",
        "nama_pic": "", "jabatan": "", "no_hp": "", "email": "",
        "peserta": "1 orang (PIC saja)",
        "sel_date_key": None, "sel_date_label": None,
        "sel_sess_value": None, "sel_sess_label": None,
        "tujuan": [], "durasi": None, "catatan": "",
        "ref_number": "", "submitted": False,
        "conflict_type": None, "conflict_msg": "", "alternatives": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton,[data-testid="stToolbar"],[data-testid="collapsedControl"]{display:none}
.main .block-container{padding-top:0!important;padding-left:1rem!important;padding-right:1rem!important;max-width:760px!important}

.mtr-topbar{background:#1D4ED8;margin:-1rem -1rem 0;padding:0 28px;height:56px;display:flex;align-items:center;justify-content:space-between}
.mtr-topbar-right{font-size:12px;color:rgba(255,255,255,.6)}
.mtr-hero{background:linear-gradient(135deg,#1D4ED8 0%,#2563EB 55%,#0BA5EC 100%);margin:0 -1rem;padding:36px 32px 72px;position:relative;overflow:hidden}
.mtr-hero::after{content:'';position:absolute;right:-60px;top:-60px;width:300px;height:300px;border-radius:50%;background:rgba(255,255,255,.04);pointer-events:none}
.mtr-hero-badge{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.2);border-radius:20px;padding:4px 13px;font-size:11px;font-weight:600;color:rgba(255,255,255,.9);letter-spacing:.7px;text-transform:uppercase;margin-bottom:14px}
.mtr-pulse{width:7px;height:7px;background:#4ADE80;border-radius:50%;display:inline-block;animation:mtr-pls 1.8s ease-in-out infinite}
@keyframes mtr-pls{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.75)}}
.mtr-hero h1{font-size:28px!important;font-weight:700!important;color:white!important;letter-spacing:-.5px;margin-bottom:8px!important;line-height:1.25!important}
.mtr-hero p{font-size:14px;color:rgba(255,255,255,.75);max-width:480px;line-height:1.65}
.mtr-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.mtr-chip{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:4px 12px;font-size:11.5px;color:rgba(255,255,255,.85);font-weight:500}
.mtr-steps{display:flex;align-items:center;background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px 20px;margin:-36px 0 16px;position:relative;z-index:10;box-shadow:0 4px 16px rgba(30,64,175,.08)}
.mtr-step{display:flex;align-items:center;gap:8px;flex:1}
.mtr-step-circle{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0;border:1.5px solid #E2E8F0;color:#94A3B8;background:#F1F5F9}
.mtr-step-circle.active{background:#2563EB;color:white;border-color:#2563EB}
.mtr-step-circle.done{background:#EFF6FF;color:#2563EB;border-color:#BFDBFE}
.mtr-step-label{font-size:12px;color:#94A3B8;font-weight:500;white-space:nowrap}
.mtr-step-label.active{color:#2563EB;font-weight:600}
.mtr-step-label.done{color:#64748B}
.mtr-connector{flex:1;height:1.5px;background:#E2E8F0;margin:0 6px;max-width:48px}
.mtr-connector.done{background:#BFDBFE}
.mtr-card{background:white;border:1px solid #E2E8F0;border-radius:12px;padding:28px 30px;margin-bottom:14px;box-shadow:0 4px 16px rgba(30,64,175,.06)}
.mtr-card-head{display:flex;align-items:flex-start;gap:13px;padding-bottom:18px;border-bottom:1px solid #F1F5F9;margin-bottom:22px}
.mtr-card-icon{width:40px;height:40px;background:#EFF6FF;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.mtr-step-tag{display:inline-block;background:#EFF6FF;color:#2563EB;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;letter-spacing:.5px;text-transform:uppercase;margin-bottom:5px}
.mtr-card-title{font-size:17px!important;font-weight:700!important;color:#0F172A!important;letter-spacing:-.3px;margin:0!important}
.mtr-card-sub{font-size:13px;color:#94A3B8;margin-top:2px}
.mtr-sec{font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#94A3B8;margin:20px 0 10px;display:flex;align-items:center;gap:10px}
.mtr-sec::after{content:'';flex:1;height:1px;background:#F1F5F9}
.mtr-info{display:flex;gap:10px;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:12px 14px;font-size:13px;color:#1E40AF;line-height:1.55;margin-bottom:14px}
.mtr-date-card{border:1.5px solid #E2E8F0;border-radius:10px;margin-bottom:10px;overflow:hidden;background:white}
.mtr-date-head{display:flex;align-items:center;justify-content:space-between;padding:12px 16px 8px}
.mtr-date-name{font-size:14px;font-weight:700;color:#0F172A}
.mtr-badge-open{background:#ECFDF5;color:#065F46;border:1px solid #6EE7B7;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600}
.mtr-badge-partial{background:#FFFBEB;color:#92400E;border:1px solid #FCD34D;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600}
.mtr-badge-full{background:#FEF2F2;color:#991B1B;border:1px solid #FECACA;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600}
.mtr-alert-block{background:#FEF2F2;border:1px solid #FECACA;border-left:3px solid #EF4444;border-radius:8px;padding:13px 15px;margin-bottom:12px;font-size:13px;color:#7F1D1D}
.mtr-alert-ok{background:#ECFDF5;border:1px solid #6EE7B7;border-left:3px solid #10B981;border-radius:8px;padding:13px 15px;margin-bottom:12px;font-size:13px;color:#065F46}
.mtr-alert-title{font-weight:700;margin-bottom:4px;font-size:13.5px}
.mtr-sel-bar{background:#2563EB;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;margin-top:10px}
.mtr-sel-tag{font-size:10.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:rgba(255,255,255,.65);margin-bottom:3px}
.mtr-sel-val{font-size:13.5px;font-weight:700;color:white}
.mtr-review-row{display:flex;border:1px solid #F1F5F9;border-radius:7px;overflow:hidden;margin-bottom:7px}
.mtr-review-label{width:130px;flex-shrink:0;background:#F8FAFC;padding:10px 13px;font-size:11.5px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:.3px}
.mtr-review-val{padding:10px 14px;font-size:13.5px;color:#1E293B;font-weight:500;flex:1}
.mtr-success{text-align:center;padding:48px 20px}
.mtr-success-icon{width:72px;height:72px;margin:0 auto 20px;background:#ECFDF5;border:2px solid #6EE7B7;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:30px}
.mtr-ref{display:inline-block;background:#F1F5F9;border:1px solid #E2E8F0;border-radius:6px;padding:7px 18px;font-size:13px;color:#64748B;font-family:monospace;letter-spacing:2px;margin:12px 0 16px}
.mtr-succ-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:400px;margin:16px auto 0;text-align:left}
.mtr-succ-item{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:7px;padding:10px 13px}
.mtr-succ-label{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;font-weight:600;margin-bottom:3px}
.mtr-succ-val{font-size:13.5px;font-weight:700;color:#0F172A}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea{border:1.5px solid #E2E8F0!important;border-radius:7px!important;font-size:13.5px!important}
div[data-testid="stTextInput"] input:focus,div[data-testid="stTextArea"] textarea:focus{border-color:#3B82F6!important;box-shadow:0 0 0 3px rgba(59,130,246,.1)!important}
div[data-testid="stButton"]>button[kind="primary"]{background-color:#2563EB!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:14px!important;padding:10px 24px!important}
div[data-testid="stButton"]>button[kind="primary"]:hover{background-color:#1D4ED8!important;box-shadow:0 4px 14px rgba(37,99,235,.35)!important}
div[data-testid="stButton"]>button[kind="secondary"]{border:1.5px solid #E2E8F0!important;border-radius:8px!important;color:#64748B!important;background:white!important;font-weight:600!important;font-size:14px!important}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════
def render_topbar():
    st.markdown(f"""
<div class="mtr-topbar">
  <img src="{LOGO_SRC}" alt="Mitra Tours & Travel" style="height:30px;width:auto;object-fit:contain;filter:brightness(0) invert(1);">
  <span class="mtr-topbar-right">Sales Visit Appointment System</span>
</div>""", unsafe_allow_html=True)


def render_hero():
    st.markdown(f"""
<div class="mtr-hero">
  <img src="{LOGO_SRC}" alt="Mitra Tours & Travel" style="height:44px;width:auto;object-fit:contain;filter:brightness(0) invert(1);margin-bottom:16px;display:block;">
  <div class="mtr-hero-badge"><span class="mtr-pulse"></span> Sistem Kunjungan Aktif</div>
  <h1>Buat Janji Kunjungan Sales</h1>
  <p>Ajukan jadwal kunjungan ke kantor kami. Setiap slot hanya untuk <strong>satu hotel</strong> — sistem mendeteksi konflik secara real-time dari Google Sheets.</p>
  <div class="mtr-chips">
    <span class="mtr-chip">\u2713 Cek slot real-time</span>
    <span class="mtr-chip">\U0001f4c5 Hanya hari Selasa</span>
    <span class="mtr-chip">\U0001f512 Anti double booking</span>
    <span class="mtr-chip">\U0001f4f1 Konfirmasi WhatsApp</span>
  </div>
</div>""", unsafe_allow_html=True)


def render_steps(current: int):
    def circ(i):
        if i < current:   return '<div class="mtr-step-circle done">\u2713</div>'
        if i == current:  return f'<div class="mtr-step-circle active">{i}</div>'
        return f'<div class="mtr-step-circle">{i}</div>'
    labels = ["Hotel", "Kontak", "Jadwal", "Konfirmasi"]
    html = '<div class="mtr-steps">'
    for i, lbl in enumerate(labels, 1):
        lc = "active" if i == current else ("done" if i < current else "")
        html += f'<div class="mtr-step">{circ(i)}<span class="mtr-step-label {lc}">{lbl}</span></div>'
        if i < 4:
            html += f'<div class="mtr-connector {"done" if i < current else ""}"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def card_header(icon, tag, title, subtitle):
    st.markdown(f"""
<div class="mtr-card-head">
  <div class="mtr-card-icon">{icon}</div>
  <div>
    <div class="mtr-step-tag">{tag}</div>
    <div class="mtr-card-title">{title}</div>
    <div class="mtr-card-sub">{subtitle}</div>
  </div>
</div>""", unsafe_allow_html=True)


def sec_label(text):
    st.markdown(f'<div class="mtr-sec">{text}</div>', unsafe_allow_html=True)


def info_box(text):
    st.markdown(f'<div class="mtr-info"><span>\u2139\ufe0f</span><div>{text}</div></div>', unsafe_allow_html=True)


def alert_box(kind, title, body, alts=None):
    css = "mtr-alert-block" if kind == "blocking" else "mtr-alert-ok"
    st.markdown(f'<div class="{css}"><div class="mtr-alert-title">{title}</div><div>{body}</div></div>',
                unsafe_allow_html=True)
    if alts:
        st.markdown("**\U0001f4cc Slot alternatif tersedia:**")
        for alt in alts:
            if st.button(f"\u2192 {alt['date_label']}  ·  {alt['sess_label']}",
                         key=f"alt_{alt['date_key']}_{alt['sess_value']}",
                         use_container_width=True):
                st.session_state.sel_date_key   = alt["date_key"]
                st.session_state.sel_date_label = alt["date_label"]
                st.session_state.sel_sess_value = alt["sess_value"]
                st.session_state.sel_sess_label = alt["sess_label"]
                st.session_state.conflict_type  = "ok"
                st.session_state.conflict_msg   = f"Slot dipilih: {alt['date_label']} · {alt['sess_label']}"
                st.session_state.alternatives   = []
                st.rerun()


# ══════════════════════════════════════════════════════════════════
# VALIDASI
# ══════════════════════════════════════════════════════════════════
def validate_email(email):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email.strip()))

def validate_step1():
    ok = True
    if not st.session_state.nama_hotel.strip():
        st.error("\u274c Nama hotel wajib diisi"); ok = False
    if not st.session_state.alamat_hotel.strip():
        st.error("\u274c Alamat hotel wajib diisi"); ok = False
    return ok

def validate_step2():
    ok = True
    if not st.session_state.nama_pic.strip():
        st.error("\u274c Nama PIC wajib diisi"); ok = False
    if not st.session_state.jabatan.strip():
        st.error("\u274c Jabatan wajib diisi"); ok = False
    if not st.session_state.no_hp.strip():
        st.error("\u274c Nomor WhatsApp wajib diisi"); ok = False
    if not st.session_state.email.strip():
        st.error("\u274c Email wajib diisi"); ok = False
    elif not validate_email(st.session_state.email):
        st.error("\u274c Format email tidak valid"); ok = False
    return ok

def validate_step3(booked):
    ok = True
    if not st.session_state.sel_date_key or not st.session_state.sel_sess_value:
        st.error("\u274c Pilih tanggal dan slot waktu kunjungan"); ok = False
    elif is_booked(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value):
        alts = get_alternatives(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value)
        st.session_state.conflict_type  = "blocking"
        st.session_state.conflict_msg   = "Slot yang dipilih sudah terisi hotel lain."
        st.session_state.alternatives   = alts
        st.session_state.sel_date_key   = None
        st.session_state.sel_date_label = None
        st.session_state.sel_sess_value = None
        st.session_state.sel_sess_label = None
        ok = False
    if not st.session_state.tujuan:
        st.error("\u274c Pilih minimal satu tujuan kunjungan"); ok = False
    if not st.session_state.durasi:
        st.error("\u274c Estimasi durasi wajib dipilih"); ok = False
    return ok


# ══════════════════════════════════════════════════════════════════
# STEP 1 — HOTEL
# ══════════════════════════════════════════════════════════════════
def render_step1():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("\U0001f3e8", "Langkah 1 dari 3", "Informasi Hotel", "Data properti hotel atau perusahaan Anda")
    st.session_state.nama_hotel = st.text_input(
        "Nama Hotel / Property *", value=st.session_state.nama_hotel,
        placeholder="Contoh: Grand Hyatt Jakarta", key="inp_nama_hotel")
    st.session_state.alamat_hotel = st.text_area(
        "Alamat Hotel *", value=st.session_state.alamat_hotel,
        placeholder="Alamat lengkap hotel...", height=90, key="inp_alamat")
    opts = HOTEL_BRANDS
    idx  = opts.index(st.session_state.brand_hotel) if st.session_state.brand_hotel in opts else 0
    st.session_state.brand_hotel = st.selectbox(
        "Brand / Chain Hotel", options=opts, index=idx, key="inp_brand",
        format_func=lambda x: "\u2014 Pilih Brand / Chain \u2014" if x == "" else x)
    st.markdown("</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Lanjut \u2192", type="primary", use_container_width=True, key="btn1"):
            if validate_step1():
                st.session_state.step = 2; st.rerun()


# ══════════════════════════════════════════════════════════════════
# STEP 2 — PIC
# ══════════════════════════════════════════════════════════════════
def render_step2():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("\U0001f464", "Langkah 2 dari 3", "Data PIC & Kontak", "Penanggung jawab kunjungan")
    st.session_state.nama_pic = st.text_input(
        "Nama PIC Utama *", value=st.session_state.nama_pic,
        placeholder="Nama lengkap", key="inp_nama_pic")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.jabatan = st.text_input(
            "Jabatan *", value=st.session_state.jabatan,
            placeholder="Sales Manager, GM, dll", key="inp_jabatan")
    with c2:
        st.session_state.no_hp = st.text_input(
            "Nomor WhatsApp *", value=st.session_state.no_hp,
            placeholder="08xx-xxxx-xxxx", key="inp_no_hp")
    st.session_state.email = st.text_input(
        "Alamat Email *", value=st.session_state.email,
        placeholder="nama@hotel.com", key="inp_email")
    sec_label("Jumlah Peserta")
    p_opts = ["1 orang (PIC saja)", "2 orang", "3 orang", "4 orang", "5 orang"]
    cur_p  = p_opts.index(st.session_state.peserta) if st.session_state.peserta in p_opts else 0
    st.session_state.peserta = st.radio(
        "Peserta", options=p_opts, index=cur_p, horizontal=True,
        label_visibility="collapsed", key="inp_peserta")
    st.markdown("</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u2190 Kembali", key="btn2_back", use_container_width=True):
            st.session_state.step = 1; st.rerun()
    with c2:
        if st.button("Lanjut \u2192", type="primary", key="btn2_next", use_container_width=True):
            if validate_step2():
                _fetch_booked_cached.clear()
                st.session_state.step = 3; st.rerun()


# ══════════════════════════════════════════════════════════════════
# STEP 3 — JADWAL
# ══════════════════════════════════════════════════════════════════
def render_step3():
    booked = fetch_booked_slots()

    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("\U0001f4c5", "Langkah 3 dari 3", "Pilih Jadwal Kunjungan",
                "Slot terisi ditandai otomatis dari Google Sheets")
    info_box("Kunjungan hanya setiap <strong>Selasa</strong> dalam 4 slot. Setiap slot hanya untuk <strong>1 hotel</strong>.")

    if st.session_state.conflict_type == "blocking":
        alert_box("blocking", "\u26d4 Slot tidak tersedia!",
                  st.session_state.conflict_msg, st.session_state.alternatives)
    elif st.session_state.conflict_type == "ok":
        alert_box("ok", "\u2705 Slot tersedia!", st.session_state.conflict_msg)

    sec_label("Pilih Tanggal & Slot Waktu")

    for dt in DATES:
        free  = [s for s in SESSIONS if not is_booked(booked, dt["key"], s["value"])]
        taken = [s for s in SESSIONS if is_booked(booked, dt["key"], s["value"])]
        all_full = len(free) == 0
        badge_cls = "mtr-badge-full" if all_full else ("mtr-badge-partial" if taken else "mtr-badge-open")
        badge_txt = "Penuh" if all_full else (f"{len(free)} slot tersisa" if taken else f"{len(free)} slot tersedia")

        st.markdown(f"""
<div class="mtr-date-card">
  <div class="mtr-date-head">
    <div><div class="mtr-date-name">{dt["label"]}</div></div>
    <span class="{badge_cls}">{badge_txt}</span>
  </div>
</div>""", unsafe_allow_html=True)

        if all_full:
            st.caption("Semua slot pada tanggal ini sudah penuh.")
        else:
            cols = st.columns(2)
            for i, sess in enumerate(SESSIONS):
                is_taken  = is_booked(booked, dt["key"], sess["value"])
                is_picked = (st.session_state.sel_date_key == dt["key"] and
                             st.session_state.sel_sess_value == sess["value"])
                with cols[i % 2]:
                    if is_taken:
                        st.markdown(
                            f'<div style="border:1.5px solid #FECACA;background:#FEF2F2;border-radius:8px;'
                            f'padding:10px 13px;margin-bottom:8px;opacity:.75;">' +
                            f'<div style="font-size:11px;font-weight:700;color:#991B1B;text-transform:uppercase;margin-bottom:4px;">Penuh</div>' +
                            f'<div style="font-size:14px;font-weight:700;color:#9CA3AF;text-decoration:line-through;">{sess["label"]}</div></div>',
                            unsafe_allow_html=True)
                    else:
                        ps = "border:2px solid #2563EB;background:#EFF6FF;" if is_picked else "border:1.5px solid #6EE7B7;background:#ECFDF5;"
                        lc = "#1D4ED8" if is_picked else "#065F46"
                        tc = "#1E40AF" if is_picked else "#0F172A"
                        st.markdown(
                            f'<div style="{ps}border-radius:8px;padding:10px 13px;margin-bottom:8px;">' +
                            f'<div style="font-size:11px;font-weight:700;color:{lc};text-transform:uppercase;margin-bottom:4px;">{"\u2713 Dipilih" if is_picked else "Tersedia"}</div>' +
                            f'<div style="font-size:14px;font-weight:700;color:{tc};">{sess["label"]}</div></div>',
                            unsafe_allow_html=True)
                        if st.button("\u2713 Pilih" if is_picked else "Pilih",
                                     key=f"slot_{dt['key']}_{sess['id']}",
                                     use_container_width=True):
                            _fetch_booked_cached.clear()
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
                                st.session_state.conflict_msg   = f"<strong>{dt['label']}</strong> · <strong>{sess['label']}</strong> siap di-booking."
                                st.session_state.alternatives   = []
                            st.rerun()

    if st.session_state.sel_date_key and st.session_state.sel_sess_value:
        st.markdown(f"""
<div class="mtr-sel-bar">
  <div>
    <div class="mtr-sel-tag">Jadwal dipilih</div>
    <div class="mtr-sel-val">{st.session_state.sel_date_label}&nbsp; · &nbsp;{st.session_state.sel_sess_label}</div>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button("\u2715 Batalkan pilihan", key="clear_slot"):
            st.session_state.sel_date_key = st.session_state.sel_date_label = None
            st.session_state.sel_sess_value = st.session_state.sel_sess_label = None
            st.session_state.conflict_type = None; st.session_state.alternatives = []
            st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid #F1F5F9;margin:18px 0'>", unsafe_allow_html=True)
    sec_label("Tujuan Kunjungan")
    tujuan_selected = []
    cols = st.columns(2)
    for i, tuj in enumerate(TUJUAN_OPTIONS):
        with cols[i % 2]:
            if st.checkbox(tuj, value=(tuj in st.session_state.tujuan), key=f"tuj_{i}"):
                tujuan_selected.append(tuj)
    st.session_state.tujuan = tujuan_selected

    sec_label("Estimasi Durasi")
    d_opts = ["15 Menit", "30 Menit", "45 Menit"]
    cur_d  = d_opts.index(st.session_state.durasi) if st.session_state.durasi in d_opts else 0
    st.session_state.durasi = st.radio(
        "Durasi", options=d_opts, index=cur_d, horizontal=True,
        label_visibility="collapsed", key="inp_durasi")

    sec_label("Catatan Tambahan")
    st.session_state.catatan = st.text_area(
        "Catatan", value=st.session_state.catatan,
        placeholder="Informasi tambahan (opsional)...", height=80,
        label_visibility="collapsed", key="inp_catatan")

    st.markdown("</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u2190 Kembali", key="btn3_back", use_container_width=True):
            st.session_state.step = 2; st.rerun()
    with c2:
        if st.button("Review Data \u2192", type="primary", key="btn3_next", use_container_width=True):
            fresh_b = fetch_booked_slots()
            if validate_step3(fresh_b):
                st.session_state.step = 4; st.rerun()


# ══════════════════════════════════════════════════════════════════
# STEP 4 — REVIEW & SUBMIT
# ══════════════════════════════════════════════════════════════════
def render_step4():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    card_header("\U0001f4cb", "Konfirmasi", "Review Permohonan", "Periksa kembali sebelum mengirim")

    rows = [
        ("Hotel",    st.session_state.nama_hotel),
        ("Alamat",   st.session_state.alamat_hotel),
        ("Brand",    st.session_state.brand_hotel or "\u2014"),
        ("Nama PIC", st.session_state.nama_pic),
        ("Jabatan",  st.session_state.jabatan),
        ("WhatsApp", st.session_state.no_hp),
        ("Email",    st.session_state.email),
        ("Peserta",  st.session_state.peserta),
        ("Tanggal",  st.session_state.sel_date_label or "\u2014"),
        ("Slot",     st.session_state.sel_sess_label or "\u2014"),
        ("Durasi",   st.session_state.durasi or "\u2014"),
        ("Tujuan",   ", ".join(st.session_state.tujuan) or "\u2014"),
    ]
    if st.session_state.catatan:
        rows.append(("Catatan", st.session_state.catatan))

    html = "".join(f'<div class="mtr-review-row"><div class="mtr-review-label">{l}</div><div class="mtr-review-val">{v}</div></div>' for l, v in rows)
    st.markdown(html, unsafe_allow_html=True)
    info_box("Dengan mengirimkan formulir ini, Anda menyetujui data yang diisi adalah benar dan bersedia dihubungi via WhatsApp atau Email untuk konfirmasi jadwal kunjungan.")
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u2190 Edit Data", key="btn4_back", use_container_width=True):
            st.session_state.step = 3; st.rerun()
    with c2:
        if st.button("\u2709\ufe0f  Kirim Permohonan", type="primary", key="btn4_submit", use_container_width=True):
            do_submit()


def do_submit():
    # ── Verifikasi slot terakhir ──
    _fetch_booked_cached.clear()
    fresh = fetch_booked_slots()
    dk = st.session_state.sel_date_key
    sv = st.session_state.sel_sess_value

    if is_booked(fresh, dk, sv):
        alts = get_alternatives(fresh, dk, sv)
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = f"Slot {st.session_state.sel_sess_label} pada {st.session_state.sel_date_label} baru saja dipesan hotel lain."
        st.session_state.alternatives  = alts
        for k in ("sel_date_key","sel_date_label","sel_sess_value","sel_sess_label"):
            st.session_state[k] = None
        st.session_state.step = 3
        st.rerun(); return

    # ── Kirim ke Google Apps Script ──
    wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    ref = generate_ref()

    payload = {
        "ref":         ref,
        "timestamp":   wib.strftime("%d/%m/%Y %H:%M:%S"),
        "namaHotel":   st.session_state.nama_hotel,
        "alamatHotel": st.session_state.alamat_hotel,
        "brand":       st.session_state.brand_hotel or "\u2014",
        "namaPIC":     st.session_state.nama_pic,
        "jabatan":     st.session_state.jabatan,
        "noHP":        st.session_state.no_hp,
        "email":       st.session_state.email,
        "peserta":     st.session_state.peserta,
        "tujuan":      ", ".join(st.session_state.tujuan),
        "tanggal":     dk + " (Selasa)",
        "slot":        sv,
        "durasi":      st.session_state.durasi or "",
        "catatan":     st.session_state.catatan or "",
    }

    with st.spinner("\U0001f4e4 Menyimpan permohonan..."):
        ok, result = save_to_gas(payload)

    if ok:
        st.session_state.ref_number = result or ref
        st.session_state.submitted  = True
        st.session_state.step       = 5
        _fetch_booked_cached.clear()
        st.rerun()
    elif result == "SLOT_TAKEN":
        _fetch_booked_cached.clear()
        fresh2 = fetch_booked_slots()
        alts   = get_alternatives(fresh2, dk, sv)
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = f"Slot {st.session_state.sel_sess_label} pada {st.session_state.sel_date_label} baru saja dipesan saat Anda submit."
        st.session_state.alternatives  = alts
        for k in ("sel_date_key","sel_date_label","sel_sess_value","sel_sess_label"):
            st.session_state[k] = None
        st.session_state.step = 3; st.rerun()
    else:
        st.error(f"\u274c **Gagal menyimpan:** {result}")


# ══════════════════════════════════════════════════════════════════
# STEP 5 — SUCCESS
# ══════════════════════════════════════════════════════════════════
def render_success():
    st.markdown('<div class="mtr-card">', unsafe_allow_html=True)
    st.markdown(f"""
<div class="mtr-success">
  <div class="mtr-success-icon">\u2713</div>
  <h2 style="font-size:20px;font-weight:700;color:#0F172A;letter-spacing:-.3px;margin-bottom:6px">Permohonan Berhasil Dikirim!</h2>
  <p style="font-size:14px;color:#64748B;max-width:400px;margin:0 auto;line-height:1.65">
    Terima kasih! Permohonan kunjungan Anda sudah kami terima.<br>Konfirmasi akan dikirimkan dalam 1\u20132 hari kerja.
  </p>
  <div class="mtr-ref">{st.session_state.ref_number}</div>
  <p style="font-size:12.5px;color:#94A3B8">Simpan nomor referensi ini untuk tindak lanjut.</p>
  <div class="mtr-succ-grid">
    <div class="mtr-succ-item"><div class="mtr-succ-label">Nama PIC</div><div class="mtr-succ-val">{st.session_state.nama_pic}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Hotel</div><div class="mtr-succ-val">{st.session_state.nama_hotel}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Tanggal</div><div class="mtr-succ-val">{st.session_state.sel_date_label}</div></div>
    <div class="mtr-succ-item"><div class="mtr-succ-label">Slot</div><div class="mtr-succ-val">{st.session_state.sel_sess_label}</div></div>
  </div>
</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("+ Ajukan Kunjungan Baru", key="btn_reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    init_state()
    inject_css()
    render_topbar()
    render_hero()
    with st.container():
        s = st.session_state.step
        if s < 5:
            render_steps(s)
        if   s == 1: render_step1()
        elif s == 2: render_step2()
        elif s == 3: render_step3()
        elif s == 4: render_step4()
        elif s == 5: render_success()
    st.markdown('<div style="text-align:center;padding:20px 0 32px;font-size:12px;color:#94A3B8">VisitorPass · Mitra Tours &amp; Travel &nbsp;·&nbsp; Data tersimpan di Google Sheets</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
