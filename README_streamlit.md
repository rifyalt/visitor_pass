# 🏢 Mitra Tours & Travel — Visitor Appointment (Streamlit)

Sistem formulir kunjungan tamu berbasis **Streamlit** dengan integrasi Google Sheets.  
Semua secrets aman di server — tidak ada API key yang terekspos ke browser.

---

## 🚀 Jalankan Lokal

```bash
# 1. Clone / copy folder ini
cd mitra-visitor-app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Isi secrets
# Edit .streamlit/secrets.toml dengan SHEET_ID & API_KEY Anda

# 4. Jalankan
streamlit run app.py
```

Buka browser → http://localhost:8501

---

## ☁️ Deploy ke Streamlit Cloud

1. Push repo ke GitHub (**pastikan `.streamlit/secrets.toml` ada di `.gitignore`**)
2. Buka [share.streamlit.io](https://share.streamlit.io) → New app
3. Pilih repo → file: `app.py`
4. Di **Settings → Secrets**, paste isi `secrets.toml`:
   ```toml
   [google_sheets]
   sheet_id   = "ID_ANDA"
   api_key    = "API_KEY_ANDA"
   sheet_name = "Sheet1"
   ```
5. Deploy ✅

---

## 📁 Struktur File

```
mitra-visitor-app/
├── app.py                    ← Aplikasi utama (satu-satunya file Python)
├── requirements.txt          ← Dependencies
├── assets/
│   └── logo.png              ← Logo Mitra Tours & Travel
├── .streamlit/
│   ├── secrets.toml          ← 🔴 RAHASIA — jangan di-commit
│   └── config.toml           ← Tema & konfigurasi Streamlit
├── .gitignore
└── README.md
```

---

## ⚙️ Konfigurasi Jadwal

Edit langsung di `app.py`, cari konstanta `DATES` dan `SESSIONS`:

```python
DATES = [
    {"key": "6 Mei 2025",  "label": "Selasa, 6 Mei 2025"},
    # tambah tanggal Selasa baru di sini...
]

SESSIONS = [
    {"id": "P1", "value": "Pagi 09.00–10.00 WIB", "label": "🌅 Pagi 09.00–10.00"},
    # tambah/ubah slot waktu di sini...
]
```

---

## 🗂️ Struktur Google Sheets (kolom A–P)

| Kol | Isi |
|-----|-----|
| A | Timestamp |
| B | No. Referensi |
| C | Nama Hotel |
| D | Alamat Hotel |
| E | Brand/Chain |
| F | Nama PIC |
| G | Jabatan |
| H | No. WhatsApp |
| I | Email |
| J | Jumlah Peserta |
| K | Tujuan Kunjungan |
| L | Tanggal |
| M | Slot Waktu |
| N | Durasi |
| O | Catatan |
| P | Status |

Status yang diakui: `Menunggu Konfirmasi`, `Dikonfirmasi`, `Ditolak`, `Dibatalkan`.  
Slot dengan status **Ditolak/Dibatalkan** otomatis dibuka kembali.

---

## 🔐 Keamanan

- Secrets **tidak pernah dikirim ke browser** — semua request ke Google Sheets dilakukan dari server Python
- Cache 30 detik (`@st.cache_data(ttl=30)`) untuk efisiensi API calls
- Verifikasi slot dilakukan 3× (saat klik, saat review, saat submit) untuk mencegah race condition

---

*Mitra Tours & Travel — Visitor Appointment System v2.0 Streamlit Edition*
