# Roblox Modern Story Studio (ClarioHub)

## Penting
Screenshot yang dikirim menampilkan `sk-clario-YOUR_API_KEY_HERE`, yang merupakan placeholder dokumentasi, bukan API key aktif. ZIP ini tidak menyimpan API key. Masukkan key asli dari Dashboard ClarioHub pada menu **Koneksi API ClarioHub** di aplikasi.

## PC
1. Ekstrak ZIP.
2. Pasang Python 3.10 atau lebih baru.
3. Di terminal pada folder hasil ekstrak:
   `pip install -r requirements.txt`
4. Jalankan: `streamlit run app.py`
5. Buka aplikasi di browser, buka Koneksi API ClarioHub, masukkan key asli, pilih model, matikan Demo mode, lalu Generate Story.

## Termux Android
```bash
pkg update
pkg install python
pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```
Buka `http://127.0.0.1:8501` di browser.

## Alternatif environment variable
Linux/macOS/Termux:
```bash
export CLARIO_API_KEY='API_KEY_ASLI'
export CLARIO_BASE_URL='https://clariohub.id/v1'
streamlit run app.py
```
Windows PowerShell:
```powershell
$env:CLARIO_API_KEY="API_KEY_ASLI"
$env:CLARIO_BASE_URL="https://clariohub.id/v1"
streamlit run app.py
```

## Fitur
- Ide otomatis atau tema opsional; tujuh kategori cerita.
- Roblox Modern 3D Blocky, target global, dialog Inggris.
- Dua prompt Google Flow masing-masing 8 detik dengan continuity lock.
- Character Bible, hook, twist, ending, CTA opsional.
- Subtitle draft SRT, judul, deskripsi, hashtag, tag.
- Riwayat lokal SQLite untuk mengurangi pengulangan.
- Demo mode untuk mengecek UI tanpa API.

## Catatan
- Base URL menggunakan `https://clariohub.id/v1` dan request OpenAI-compatible `/chat/completions` sesuai screenshot.
- Daftar model ditranskripsi dari screenshot; model yang benar-benar tersedia tergantung key/paket. Jika error, coba model lain atau cek dokumentasi ClarioHub.
- Prompt continuity tidak menjamin frame video selalu identik. Jika tersedia, pakai frame akhir Scene 1 sebagai referensi Scene 2 di Google Flow.
- Subtitle SRT hanya draft perkiraan; periksa timing setelah klip final tersedia.


## Agar API key tidak perlu dimasukkan berulang kali (Streamlit Cloud)
1. Buka aplikasi di Streamlit Cloud.
2. Masuk ke **Manage app → Settings → Secrets** (nama menu bisa sedikit berbeda).
3. Tambahkan konfigurasi TOML berikut, ganti dengan API key asli:
   ```toml
   CLARIO_API_KEY = "API_KEY_ASLI_KAMU"
   CLARIO_BASE_URL = "https://clariohub.id/v1"
   ```
4. Simpan. Aplikasi akan membaca `st.secrets` otomatis dan tidak perlu meminta key setiap kali dibuat.
5. Jangan menaruh key asli di `app.py`, GitHub, atau ZIP yang dibagikan.

Untuk penggunaan lokal, bisa gunakan environment variable seperti di bagian konfigurasi alternatif.
