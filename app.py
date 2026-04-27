"""
Mitra Tours & Travel — Visitor Appointment System
app.py  |  Mobile-Friendly Version
- Google Sheets read (slot check)
- Google Apps Script write
- Email notifikasi via GAS ke d4t4m1tr4@gmail.com
"""

import streamlit as st
import requests
import random
import string
import re
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Kunjungan Sales — Mitra Tours",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CONFIG ────────────────────────────────────────────────────────
GAS_ENDPOINT = "https://script.google.com/macros/s/AKfycbzm4Mnax-z0oq7Wao7Gz9C_tw4CgKLlyl0GfSTJGeIHAfhzSilZtQvr947Ym-1p2DqwkA/exec"
SHEET_ID     = "1AQz-w3sLjGVdOsneDmdTFHFW6Nx7Z337Kjw2zzqFoXI"
API_KEY      = "AIzaSyA1Mau8yZxao0MD5Mx_Dt027EuMbrUN9oo"
SHEET_NAME   = "Sheet1"
NOTIF_EMAIL  = "d4t4m1tr4@gmail.com"

SHEETS_READ_URL = (
    f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
    f"/values/{SHEET_NAME}?key={API_KEY}"
)

DATES = [
    {"key": "6 Mei 2025",  "label": "Selasa, 6 Mei 2025"},
    {"key": "13 Mei 2025", "label": "Selasa, 13 Mei 2025"},
    {"key": "20 Mei 2025", "label": "Selasa, 20 Mei 2025"},
    {"key": "27 Mei 2025", "label": "Selasa, 27 Mei 2025"},
]

SESSIONS = [
    {"id": "P1", "value": "Pagi 09.00-10.00 WIB",  "label": "Pagi  09.00 - 10.00 WIB"},
    {"id": "P2", "value": "Pagi 10.00-11.00 WIB",  "label": "Pagi  10.00 - 11.00 WIB"},
    {"id": "S1", "value": "Siang 13.30-14.30 WIB", "label": "Siang 13.30 - 14.30 WIB"},
    {"id": "S2", "value": "Siang 14.30-15.30 WIB", "label": "Siang 14.30 - 15.30 WIB"},
]

HOTEL_BRANDS = [
    "", 
    "Accor",
    "Aman Resorts",
    "Archipelago International",
    "ARTOTEL Group",
    "Aryaduta",
    "Ascott Limited",
    "Azana Hotels",
    "Banyan Group Limited",
    "Best Western Hotels",
    "Cross Hotels & Resorts",
    "Dafam Hotel Management",
    "Dusit International",
    "Four Seasons Hotels and Resorts",
    "Hilton Worldwide",
    "Horison Hotels Group",
    "Hotel Indonesia Group",
    "Hyatt Hotels Corporation",
    "IHG Hotels & Resorts",
    "Jambuluwuk Hotels & Resorts",
    "Jumeirah",
    "Kempinski",
    "Mandarin Oriental Hotel Group",
    "Marriott International",
    "Meliá Hotels International",
    "Minor Hotels",
    "Oberoi Group",
    "Pan Pacific Hotels and Resorts",
    "Parador Hotels & Resorts",
    "Radisson Hotel Group",
    "Santika Indonesia Hotels & Resorts",
    "Shangri-La Hotels and Resorts",
    "Swiss-Belhotel International",
    "The Ascott Limited",
    "Waringin Hospitality Hotel Group",
    "Wyndham Hotels & Resorts",
    "Independen / Tidak Berantai", "Lainnya",
]

TUJUAN_OPTIONS = [
    "Perkenalan Hotel",
    "Presentasi Produk / Fasilitas",
    "Corporate Rate / Contract Rate",
    "Promo / Special Offer",
    "Kerja Sama Partnership",
    "Follow Up Existing Business",
]

# ── GOOGLE SHEETS READ ────────────────────────────────────────────
@st.cache_data(ttl=30)
def _fetch_booked_cached() -> tuple:
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
        st.toast(f"Gagal memuat jadwal: {err}", icon="⚠️")
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

def generate_ref() -> str:
    return "SV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))

# ── GAS WRITE + EMAIL NOTIF ───────────────────────────────────────
def save_to_gas(payload: dict) -> tuple:
    try:
        payload["notifEmail"] = NOTIF_EMAIL
        resp = requests.post(GAS_ENDPOINT, json=payload, timeout=30,
                             headers={"Content-Type": "application/json"})
        if not resp.ok:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        try:
            result = resp.json()
        except Exception:
            return False, f"Response bukan JSON: {resp.text[:150]}"
        if result.get("success"):
            return True, result.get("ref", "")
        elif result.get("error") == "SLOT_TAKEN":
            return False, "SLOT_TAKEN"
        else:
            return False, result.get("message", result.get("error", "Unknown error"))
    except requests.exceptions.Timeout:
        return False, "Timeout — coba lagi"
    except Exception as e:
        return False, str(e)

# ── SESSION STATE ─────────────────────────────────────────────────
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

# ── CSS ───────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton,[data-testid="stToolbar"],[data-testid="collapsedControl"]{display:none}

/* Mobile-first container */
.main .block-container{
  padding:0 0.75rem 2rem!important;
  max-width:600px!important;
}

/* Hero */
.hero{
  background:linear-gradient(135deg,#1D4ED8 0%,#2563EB 60%,#0EA5E9 100%);
  margin:0 -0.75rem;
  padding:24px 20px 60px;
  position:relative;overflow:hidden;
}
.hero::after{
  content:'';position:absolute;right:-50px;top:-50px;
  width:180px;height:180px;border-radius:50%;
  background:rgba(255,255,255,0.05);pointer-events:none;
}
.hero-title{
  font-size:24px!important;font-weight:700!important;
  color:#fff!important;letter-spacing:-.5px;
  margin-bottom:6px!important;line-height:1.25!important;
}
.hero-sub{font-size:13px;color:rgba(255,255,255,.75);line-height:1.6;margin-bottom:14px}
.hero-badge{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);
  border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;
  color:rgba(255,255,255,.9);letter-spacing:.5px;text-transform:uppercase;
  margin-bottom:12px;
}
.pulse{width:6px;height:6px;background:#4ADE80;border-radius:50%;
  display:inline-block;animation:pls 1.8s ease-in-out infinite}
@keyframes pls{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.75)}}

/* Steps bar */
.steps-wrap{padding:0 4px}
.steps{
  display:flex;align-items:center;
  background:#fff;border:1px solid #E2E8F0;border-radius:14px;
  padding:14px 16px;margin-top:-30px;position:relative;z-index:10;
  box-shadow:0 4px 20px rgba(30,64,175,.1);
}
.step{display:flex;align-items:center;gap:6px;flex:1}
.step-circle{
  width:26px;height:26px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;flex-shrink:0;
}
.step-circle.active{background:#2563EB;color:#fff}
.step-circle.done{background:#DBEAFE;color:#1D4ED8;border:1.5px solid #93C5FD}
.step-circle.idle{background:#F1F5F9;color:#94A3B8;border:1.5px solid #E2E8F0}
.step-label{font-size:10.5px;font-weight:500;white-space:nowrap}
.step-label.active{color:#2563EB;font-weight:700}
.step-label.done{color:#64748B}
.step-label.idle{color:#94A3B8}
.connector{flex:1;height:1.5px;background:#E2E8F0;margin:0 4px;max-width:32px}
.connector.done{background:#93C5FD}

/* Card */
.card{
  background:#fff;border:1px solid #E8EDF3;border-radius:16px;
  padding:20px 18px;margin-bottom:12px;
  box-shadow:0 2px 12px rgba(30,64,175,.06);
}
.card-head{display:flex;align-items:center;gap:12px;padding-bottom:14px;
  border-bottom:1px solid #F1F5F9;margin-bottom:16px}
.card-icon{width:40px;height:40px;background:#EFF6FF;border-radius:10px;
  display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.step-tag{display:inline-block;background:#EFF6FF;color:#2563EB;
  font-size:9px;font-weight:700;padding:2px 8px;border-radius:8px;
  letter-spacing:.5px;text-transform:uppercase;margin-bottom:3px}
.card-title{font-size:15px!important;font-weight:700!important;
  color:#0F172A!important;letter-spacing:-.2px;margin:0!important}
.card-sub{font-size:12px;color:#94A3B8;margin-top:1px}

/* Info box */
.info-box{display:flex;gap:9px;background:#EFF6FF;border:1px solid #BFDBFE;
  border-radius:8px;padding:11px 13px;font-size:12px;color:#1E40AF;
  line-height:1.55;margin-bottom:12px}

/* Slot cards — full width on mobile */
.slot-card{
  border-radius:10px;padding:12px 14px;margin-bottom:8px;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;
}
.slot-available{border:1.5px solid #6EE7B7;background:#F0FDF4}
.slot-selected{border:2px solid #2563EB;background:#EFF6FF}
.slot-taken{border:1.5px solid #FECACA;background:#FEF2F2;opacity:.7;cursor:default}
.slot-label{font-size:13.5px;font-weight:600;color:#0F172A}
.slot-taken .slot-label{color:#9CA3AF;text-decoration:line-through}
.slot-selected .slot-label{color:#1E40AF}
.slot-badge{font-size:10px;font-weight:700;padding:3px 9px;border-radius:8px;
  text-transform:uppercase;letter-spacing:.3px}
.badge-avail{background:#DCFCE7;color:#166534}
.badge-sel{background:#DBEAFE;color:#1D4ED8}
.badge-taken{background:#FEE2E2;color:#991B1B}

/* Date header */
.date-header{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:8px;margin-top:14px}
.date-name{font-size:13px;font-weight:700;color:#1E293B}
.avail-badge{font-size:10px;font-weight:600;padding:3px 8px;border-radius:8px}
.avail-ok{background:#DCFCE7;color:#166534;border:1px solid #86EFAC}
.avail-part{background:#FEF9C3;color:#854D0E;border:1px solid #FDE047}
.avail-full{background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5}

/* Selected bar */
.sel-bar{
  background:#1D4ED8;border-radius:10px;
  padding:12px 16px;margin:10px 0;
  display:flex;align-items:center;justify-content:space-between;
}
.sel-bar-label{font-size:10px;font-weight:600;color:rgba(255,255,255,.65);
  text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px}
.sel-bar-val{font-size:13px;font-weight:700;color:#fff}

/* Alert */
.alert-block{background:#FEF2F2;border:1px solid #FECACA;border-left:3px solid #EF4444;
  border-radius:8px;padding:12px 14px;margin-bottom:10px;font-size:12.5px;color:#7F1D1D}
.alert-ok{background:#F0FDF4;border:1px solid #86EFAC;border-left:3px solid #22C55E;
  border-radius:8px;padding:12px 14px;margin-bottom:10px;font-size:12.5px;color:#14532D}
.alert-title{font-weight:700;margin-bottom:3px;font-size:13px}

/* Review */
.review-row{display:flex;border:1px solid #F1F5F9;border-radius:8px;
  overflow:hidden;margin-bottom:7px}
.review-lbl{width:110px;flex-shrink:0;background:#F8FAFC;
  padding:9px 12px;font-size:10.5px;font-weight:600;color:#94A3B8;
  text-transform:uppercase;letter-spacing:.3px}
.review-val{padding:9px 13px;font-size:13px;color:#1E293B;font-weight:500;flex:1;
  word-break:break-word}

/* Success */
.success-box{text-align:center;padding:36px 16px}
.success-icon{width:68px;height:68px;margin:0 auto 18px;background:#F0FDF4;
  border:2px solid #86EFAC;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:28px}
.ref-badge{display:inline-block;background:#F1F5F9;border:1px solid #E2E8F0;
  border-radius:6px;padding:6px 16px;font-size:12px;color:#64748B;
  font-family:monospace;letter-spacing:2px;margin:10px 0 14px}
.succ-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;
  max-width:360px;margin:14px auto 0;text-align:left}
.succ-item{background:#F8FAFC;border:1px solid #E2E8F0;
  border-radius:8px;padding:10px 12px}
.succ-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.5px;
  color:#94A3B8;font-weight:600;margin-bottom:2px}
.succ-val{font-size:13px;font-weight:700;color:#0F172A}

/* Section label */
.sec-lbl{font-size:10px;font-weight:700;letter-spacing:.7px;
  text-transform:uppercase;color:#94A3B8;margin:14px 0 8px;
  display:flex;align-items:center;gap:8px}
.sec-lbl::after{content:'';flex:1;height:1px;background:#F1F5F9}

/* Buttons */
div[data-testid="stButton"]>button[kind="primary"]{
  background:#2563EB!important;border:none!important;border-radius:10px!important;
  font-weight:600!important;font-size:14px!important;
  padding:11px 20px!important;width:100%!important;
}
div[data-testid="stButton"]>button[kind="primary"]:hover{
  background:#1D4ED8!important;
}
div[data-testid="stButton"]>button[kind="secondary"]{
  border:1.5px solid #E2E8F0!important;border-radius:10px!important;
  color:#64748B!important;background:#fff!important;
  font-weight:600!important;font-size:14px!important;width:100%!important;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea{
  border:1.5px solid #E2E8F0!important;border-radius:8px!important;
  font-size:14px!important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus{
  border-color:#3B82F6!important;
  box-shadow:0 0 0 3px rgba(59,130,246,.1)!important;
}

/* Section divider */
.sec-div{border:none;border-top:1px solid #F1F5F9;margin:14px 0}

/* Footer */
.footer{text-align:center;padding:18px 0 28px;font-size:11px;color:#94A3B8}

/* Chip tags */
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);
  border-radius:14px;padding:4px 11px;font-size:11px;color:rgba(255,255,255,.88);
  font-weight:500}
</style>""", unsafe_allow_html=True)


# ── UI HELPERS ────────────────────────────────────────────────────
def render_hero():
    st.markdown("""
<div class="hero">
  <div class="hero-badge"><span class="pulse"></span>&nbsp;Sistem Kunjungan Aktif</div>
  <div class="hero-title">Buat Janji Kunjungan Sales</div>
  <div class="hero-sub">
    Ajukan jadwal kunjungan ke kantor kami. Setiap slot hanya untuk
    <strong>satu hotel</strong> — sistem mendeteksi konflik secara real-time.
  </div>
  <div class="chips">
    <span class="chip">&#10003; Cek slot real-time</span>
    <span class="chip">&#128197; Hanya hari Selasa</span>
    <span class="chip">&#128274; Anti double booking</span>
    <span class="chip">&#128241; Konfirmasi WhatsApp</span>
  </div>
</div>""", unsafe_allow_html=True)


def render_steps(current: int):
    def circ(i):
        if i < current:
            return '<div class="step-circle done">&#10003;</div>'
        if i == current:
            return f'<div class="step-circle active">{i}</div>'
        return f'<div class="step-circle idle">{i}</div>'
    labels = ["Hotel", "Kontak", "Jadwal", "Kirim"]
    html = '<div class="steps-wrap"><div class="steps">'
    for i, lbl in enumerate(labels, 1):
        lc = "active" if i == current else ("done" if i < current else "idle")
        html += f'<div class="step">{circ(i)}<span class="step-label {lc}">{lbl}</span></div>'
        if i < 4:
            conn_cls = "done" if i < current else ""
            html += f'<div class="connector {conn_cls}"></div>'
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)


def card_head(icon, tag, title, sub=""):
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
<div class="card-head">
  <div class="card-icon">{icon}</div>
  <div>
    <div class="step-tag">{tag}</div>
    <div class="card-title">{title}</div>
    {sub_html}
  </div>
</div>""", unsafe_allow_html=True)


def sec_lbl(txt):
    st.markdown(f'<div class="sec-lbl">{txt}</div>', unsafe_allow_html=True)


def info_box(txt):
    st.markdown(
        f'<div class="info-box"><span>&#8505;&#65039;</span><div>{txt}</div></div>',
        unsafe_allow_html=True)


# ── VALIDATION ────────────────────────────────────────────────────
def valid_email(e):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e.strip()))

def validate_step1():
    ok = True
    if not st.session_state.nama_hotel.strip():
        st.error("Nama hotel wajib diisi"); ok = False
    if not st.session_state.alamat_hotel.strip():
        st.error("Alamat hotel wajib diisi"); ok = False
    return ok

def validate_step2():
    ok = True
    if not st.session_state.nama_pic.strip():
        st.error("Nama PIC wajib diisi"); ok = False
    if not st.session_state.jabatan.strip():
        st.error("Jabatan wajib diisi"); ok = False
    if not st.session_state.no_hp.strip():
        st.error("Nomor WhatsApp wajib diisi"); ok = False
    if not st.session_state.email.strip():
        st.error("Email wajib diisi"); ok = False
    elif not valid_email(st.session_state.email):
        st.error("Format email tidak valid"); ok = False
    return ok

def validate_step3(booked):
    ok = True
    if not st.session_state.sel_date_key or not st.session_state.sel_sess_value:
        st.error("Pilih tanggal dan slot waktu kunjungan"); ok = False
    elif is_booked(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value):
        alts = get_alternatives(booked, st.session_state.sel_date_key, st.session_state.sel_sess_value)
        st.session_state.conflict_type  = "blocking"
        st.session_state.conflict_msg   = "Slot yang dipilih sudah terisi hotel lain."
        st.session_state.alternatives   = alts
        for k in ("sel_date_key","sel_date_label","sel_sess_value","sel_sess_label"):
            st.session_state[k] = None
        ok = False
    if not st.session_state.tujuan:
        st.error("Pilih minimal satu tujuan kunjungan"); ok = False
    if not st.session_state.durasi:
        st.error("Estimasi durasi wajib dipilih"); ok = False
    return ok


# ── STEP 1 ────────────────────────────────────────────────────────
def render_step1():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    card_head("🏨", "Langkah 1 dari 3", "Informasi Hotel", "Data properti hotel Anda")

    st.session_state.nama_hotel = st.text_input(
        "Nama Hotel / Property *",
        value=st.session_state.nama_hotel,
        placeholder="Contoh: Grand Hyatt Jakarta",
        key="inp_nama_hotel")

    st.session_state.alamat_hotel = st.text_area(
        "Alamat Hotel *",
        value=st.session_state.alamat_hotel,
        placeholder="Alamat lengkap hotel...",
        height=80, key="inp_alamat")

    opts = HOTEL_BRANDS
    idx  = opts.index(st.session_state.brand_hotel) if st.session_state.brand_hotel in opts else 0
    st.session_state.brand_hotel = st.selectbox(
        "Brand / Chain Hotel (opsional)", options=opts, index=idx, key="inp_brand",
        format_func=lambda x: "— Pilih Brand / Chain —" if x == "" else x)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Lanjut ke Kontak →", type="primary", key="btn1"):
        if validate_step1():
            st.session_state.step = 2
            st.rerun()


# ── STEP 2 ────────────────────────────────────────────────────────
def render_step2():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    card_head("👤", "Langkah 2 dari 3", "Data PIC & Kontak", "Penanggung jawab kunjungan")

    st.session_state.nama_pic = st.text_input(
        "Nama PIC Utama *", value=st.session_state.nama_pic,
        placeholder="Nama lengkap", key="inp_nama_pic")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.jabatan = st.text_input(
            "Jabatan *", value=st.session_state.jabatan,
            placeholder="Sales Manager, GM...", key="inp_jabatan")
    with col2:
        st.session_state.no_hp = st.text_input(
            "WhatsApp *", value=st.session_state.no_hp,
            placeholder="08xx-xxxx-xxxx", key="inp_no_hp")

    st.session_state.email = st.text_input(
        "Email *", value=st.session_state.email,
        placeholder="nama@hotel.com", key="inp_email")

    sec_lbl("Jumlah Peserta")
    p_opts = ["1 orang (PIC saja)", "2 orang", "3 orang", "4 orang", "5 orang"]
    cur_p  = p_opts.index(st.session_state.peserta) if st.session_state.peserta in p_opts else 0
    st.session_state.peserta = st.radio(
        "Peserta", options=p_opts, index=cur_p, horizontal=True,
        label_visibility="collapsed", key="inp_peserta")

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Kembali", key="btn2_back"):
            st.session_state.step = 1; st.rerun()
    with col2:
        if st.button("Lanjut ke Jadwal →", type="primary", key="btn2_next"):
            if validate_step2():
                _fetch_booked_cached.clear()
                st.session_state.step = 3; st.rerun()


# ── STEP 3 ────────────────────────────────────────────────────────
def render_step3():
    booked = fetch_booked_slots()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    card_head("📅", "Langkah 3 dari 3", "Pilih Jadwal Kunjungan",
              "Slot terisi otomatis dari Google Sheets")

    info_box("Kunjungan hanya setiap <strong>Selasa</strong>. Setiap slot untuk <strong>1 hotel</strong>.")

    # Conflict alerts
    if st.session_state.conflict_type == "blocking":
        st.markdown(
            f'<div class="alert-block">'
            f'<div class="alert-title">&#9940; Slot tidak tersedia!</div>'
            f'{st.session_state.conflict_msg}</div>',
            unsafe_allow_html=True)
        if st.session_state.alternatives:
            st.markdown("**Slot alternatif:**")
            for alt in st.session_state.alternatives:
                btn_lbl = f"{alt['date_label']}  ·  {alt['sess_label']}"
                if st.button(btn_lbl, key=f"alt_{alt['date_key']}_{alt['sess_value']}"):
                    st.session_state.sel_date_key   = alt["date_key"]
                    st.session_state.sel_date_label = alt["date_label"]
                    st.session_state.sel_sess_value = alt["sess_value"]
                    st.session_state.sel_sess_label = alt["sess_label"]
                    st.session_state.conflict_type  = "ok"
                    st.session_state.conflict_msg   = f"Slot dipilih: {alt['date_label']} - {alt['sess_label']}"
                    st.session_state.alternatives   = []
                    st.rerun()

    elif st.session_state.conflict_type == "ok":
        st.markdown(
            f'<div class="alert-ok">'
            f'<div class="alert-title">&#10003; Slot tersedia!</div>'
            f'{st.session_state.conflict_msg}</div>',
            unsafe_allow_html=True)

    # Slot picker
    for dt in DATES:
        free  = [s for s in SESSIONS if not is_booked(booked, dt["key"], s["value"])]
        taken = [s for s in SESSIONS if is_booked(booked, dt["key"], s["value"])]
        all_full = len(free) == 0

        if all_full:
            badge_cls = "avail-full"; badge_txt = "Penuh"
        elif taken:
            badge_cls = "avail-part"; badge_txt = f"{len(free)} slot tersisa"
        else:
            badge_cls = "avail-ok";  badge_txt = f"{len(free)} slot tersedia"

        st.markdown(
            f'<div class="date-header">'
            f'<span class="date-name">{dt["label"]}</span>'
            f'<span class="avail-badge {badge_cls}">{badge_txt}</span>'
            f'</div>',
            unsafe_allow_html=True)

        if all_full:
            st.caption("Semua slot penuh.")
            continue

        for sess in SESSIONS:
            is_taken  = is_booked(booked, dt["key"], sess["value"])
            is_picked = (st.session_state.sel_date_key == dt["key"] and
                         st.session_state.sel_sess_value == sess["value"])
            s_lbl = sess["label"]

            if is_taken:
                st.markdown(
                    f'<div class="slot-card slot-taken">'
                    f'<span class="slot-label">{s_lbl}</span>'
                    f'<span class="slot-badge badge-taken">Penuh</span>'
                    f'</div>',
                    unsafe_allow_html=True)
            else:
                card_cls  = "slot-selected" if is_picked else "slot-available"
                badge_cls2 = "badge-sel" if is_picked else "badge-avail"
                badge_txt2 = "Dipilih" if is_picked else "Tersedia"
                btn_label  = "Dipilih ✓" if is_picked else "Pilih"

                st.markdown(
                    f'<div class="slot-card {card_cls}">'
                    f'<span class="slot-label">{s_lbl}</span>'
                    f'<span class="slot-badge {badge_cls2}">{badge_txt2}</span>'
                    f'</div>',
                    unsafe_allow_html=True)

                btn_key = f"slot_{dt['key']}_{sess['id']}"
                if st.button(btn_label, key=btn_key, use_container_width=True):
                    _fetch_booked_cached.clear()
                    fresh = fetch_booked_slots()
                    if is_booked(fresh, dt["key"], sess["value"]):
                        alts = get_alternatives(fresh, dt["key"], sess["value"])
                        st.session_state.conflict_type = "blocking"
                        s_lbl2 = sess["label"]
                        d_lbl2 = dt["label"]
                        st.session_state.conflict_msg  = f"Slot {s_lbl2} pada {d_lbl2} baru saja diisi hotel lain."
                        st.session_state.alternatives  = alts
                    else:
                        st.session_state.sel_date_key   = dt["key"]
                        st.session_state.sel_date_label = dt["label"]
                        st.session_state.sel_sess_value = sess["value"]
                        st.session_state.sel_sess_label = sess["label"]
                        st.session_state.conflict_type  = "ok"
                        d_lbl3 = dt["label"]
                        s_lbl3 = sess["label"]
                        st.session_state.conflict_msg   = f"{d_lbl3} - {s_lbl3} siap di-booking."
                        st.session_state.alternatives   = []
                    st.rerun()

    # Selected summary bar
    if st.session_state.sel_date_key and st.session_state.sel_sess_value:
        sel_dl = st.session_state.sel_date_label
        sel_sl = st.session_state.sel_sess_label
        st.markdown(
            f'<div class="sel-bar">'
            f'<div><div class="sel-bar-label">Jadwal dipilih</div>'
            f'<div class="sel-bar-val">{sel_dl} &nbsp;·&nbsp; {sel_sl}</div></div>'
            f'<div style="color:rgba(255,255,255,.6);cursor:pointer;font-size:18px">&#10005;</div>'
            f'</div>',
            unsafe_allow_html=True)
        if st.button("Batalkan pilihan", key="clear_slot"):
            st.session_state.sel_date_key = st.session_state.sel_date_label = None
            st.session_state.sel_sess_value = st.session_state.sel_sess_label = None
            st.session_state.conflict_type = None; st.session_state.alternatives = []
            st.rerun()

    st.markdown('<hr class="sec-div">', unsafe_allow_html=True)

    sec_lbl("Tujuan Kunjungan")
    tujuan_selected = []
    col1, col2 = st.columns(2)
    for i, tuj in enumerate(TUJUAN_OPTIONS):
        with (col1 if i % 2 == 0 else col2):
            if st.checkbox(tuj, value=(tuj in st.session_state.tujuan), key=f"tuj_{i}"):
                tujuan_selected.append(tuj)
    st.session_state.tujuan = tujuan_selected

    sec_lbl("Estimasi Durasi")
    d_opts = ["15 Menit", "30 Menit", "45 Menit"]
    cur_d  = d_opts.index(st.session_state.durasi) if st.session_state.durasi in d_opts else 0
    st.session_state.durasi = st.radio(
        "Durasi", options=d_opts, index=cur_d, horizontal=True,
        label_visibility="collapsed", key="inp_durasi")

    sec_lbl("Catatan Tambahan")
    st.session_state.catatan = st.text_area(
        "Catatan", value=st.session_state.catatan,
        placeholder="Informasi tambahan (opsional)...", height=80,
        label_visibility="collapsed", key="inp_catatan")

    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Kembali", key="btn3_back"):
            st.session_state.step = 2; st.rerun()
    with col2:
        if st.button("Review & Kirim →", type="primary", key="btn3_next"):
            fresh_b = fetch_booked_slots()
            if validate_step3(fresh_b):
                st.session_state.step = 4; st.rerun()


# ── STEP 4 — REVIEW & SUBMIT ──────────────────────────────────────
def render_step4():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    card_head("📋", "Konfirmasi", "Review Permohonan", "Periksa sebelum mengirim")

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

    for lbl, val in rows:
        st.markdown(
            f'<div class="review-row">'
            f'<div class="review-lbl">{lbl}</div>'
            f'<div class="review-val">{val}</div>'
            f'</div>',
            unsafe_allow_html=True)

    info_box("Dengan mengirimkan formulir ini, Anda bersedia dihubungi via WhatsApp atau Email untuk konfirmasi jadwal.")
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Edit Data", key="btn4_back"):
            st.session_state.step = 3; st.rerun()
    with col2:
        if st.button("Kirim Permohonan ✉️", type="primary", key="btn4_submit"):
            do_submit()


def do_submit():
    _fetch_booked_cached.clear()
    fresh = fetch_booked_slots()
    dk = st.session_state.sel_date_key
    sv = st.session_state.sel_sess_value

    if is_booked(fresh, dk, sv):
        alts = get_alternatives(fresh, dk, sv)
        s_lbl = st.session_state.sel_sess_label
        d_lbl = st.session_state.sel_date_label
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = f"Slot {s_lbl} pada {d_lbl} baru saja dipesan hotel lain."
        st.session_state.alternatives  = alts
        for k in ("sel_date_key","sel_date_label","sel_sess_value","sel_sess_label"):
            st.session_state[k] = None
        st.session_state.step = 3; st.rerun(); return

    wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    ref = generate_ref()

    payload = {
        "ref":         ref,
        "timestamp":   wib.strftime("%d/%m/%Y %H:%M:%S"),
        "namaHotel":   st.session_state.nama_hotel,
        "alamatHotel": st.session_state.alamat_hotel,
        "brand":       st.session_state.brand_hotel or "—",
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
        "notifEmail":  NOTIF_EMAIL,
    }

    with st.spinner("Menyimpan & mengirim notifikasi..."):
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
        s_lbl  = st.session_state.sel_sess_label
        d_lbl  = st.session_state.sel_date_label
        st.session_state.conflict_type = "blocking"
        st.session_state.conflict_msg  = f"Slot {s_lbl} pada {d_lbl} baru saja dipesan saat Anda submit."
        st.session_state.alternatives  = alts
        for k in ("sel_date_key","sel_date_label","sel_sess_value","sel_sess_label"):
            st.session_state[k] = None
        st.session_state.step = 3; st.rerun()
    else:
        st.error(f"Gagal menyimpan: {result}")


# ── STEP 5 — SUCCESS ──────────────────────────────────────────────
def render_success():
    ref   = st.session_state.ref_number
    pic   = st.session_state.nama_pic
    hotel = st.session_state.nama_hotel
    tgl   = st.session_state.sel_date_label
    slot  = st.session_state.sel_sess_label

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"""
<div class="success-box">
  <div class="success-icon">&#10003;</div>
  <h2 style="font-size:20px;font-weight:700;color:#0F172A;margin-bottom:6px">
    Permohonan Terkirim!
  </h2>
  <p style="font-size:13px;color:#64748B;line-height:1.65;margin-bottom:4px">
    Terima kasih! Permohonan kunjungan Anda sudah kami terima.<br>
    Notifikasi dikirim ke <strong>d4t4m1tr4@gmail.com</strong><br>
    Konfirmasi akan dikirimkan dalam 1-2 hari kerja.
  </p>
  <div class="ref-badge">{ref}</div>
  <p style="font-size:11.5px;color:#94A3B8;margin-bottom:0">
    Simpan nomor referensi untuk tindak lanjut.
  </p>
  <div class="succ-grid">
    <div class="succ-item"><div class="succ-lbl">Nama PIC</div><div class="succ-val">{pic}</div></div>
    <div class="succ-item"><div class="succ-lbl">Hotel</div><div class="succ-val">{hotel}</div></div>
    <div class="succ-item"><div class="succ-lbl">Tanggal</div><div class="succ-val">{tgl}</div></div>
    <div class="succ-item"><div class="succ-lbl">Slot</div><div class="succ-val">{slot}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("+ Ajukan Kunjungan Baru", key="btn_reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ── MAIN ──────────────────────────────────────────────────────────
def main():
    init_state()
    inject_css()
    render_hero()

    s = st.session_state.step
    if s < 5:
        render_steps(s)

    if   s == 1: render_step1()
    elif s == 2: render_step2()
    elif s == 3: render_step3()
    elif s == 4: render_step4()
    elif s == 5: render_success()

    st.markdown(
        '<div class="footer">VisitorPass &nbsp;·&nbsp; Mitra Tours &amp; Travel'
        '&nbsp;·&nbsp; Data tersimpan di Google Sheets</div>',
        unsafe_allow_html=True)

if __name__ == "__main__":
    main()
