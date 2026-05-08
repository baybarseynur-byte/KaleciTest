import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# --- 1. AYARLAR VE FONT ---
st.set_page_config(page_title="GKD Akademik Çeyrek Analiz", layout="wide")

def font_yukle():
    if os.path.exists("arial.ttf"):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Tr', 'arial.ttf'))
            return "Arial_Tr"
        except: return "Helvetica"
    return "Helvetica"

FONT = font_yukle()
DB_FILE = "akademik_veritabani.csv"

# --- 2. ÇEYREK (QUARTER) HESAPLAMA FONKSİYONU ---
def get_quarter(date):
    month = date.month
    if 1 <= month <= 3: return "Q1"
    elif 4 <= month <= 6: return "Q2"
    elif 7 <= month <= 9: return "Q3"
    else: return "Q4"

# --- 3. VERİ YÖNETİMİ ---
def veri_kaydet(df):
    if not os.path.isfile(DB_FILE):
        df.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        df.to_csv(DB_FILE, mode='a', header=False, index=False, encoding='utf-16')

def veri_oku():
    if os.path.isfile(DB_FILE):
        return pd.read_csv(DB_FILE, encoding='utf-16')
    return pd.DataFrame()

# --- 4. ARAYÜZ ---
st.title("🔬 GKD Akademik Performans & Çeyrek Dilim Analizi")

with st.sidebar:
    st.header("📂 Araştırma Veri Havuzu")
    db_current = veri_oku()
    st.write(f"Sistemdeki Toplam Denek: {len(db_current)}")
    if not db_current.empty:
        st.download_button("Toplu Veriyi İndir (Excel/SPSS Uyumlu)", 
                           db_current.to_csv(index=False).encode('utf-16'), 
                           "gkd_akademik_veritabani.csv", "text/csv")

with st.form("akademik_form"):
    st.subheader("👤 Katılımcı Kimlik ve Gelişim Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad, soyad = st.text_input("Ad"), st.text_input("Soyad")
        dogum_tarihi = st.date_input("Doğum Tarihi")
    with c2:
        boy, kilo = st.number_input("Boy (cm)", format="%.1f"), st.number_input("Kilo (kg)", format="%.2f")
    with c3:
        ayak, el = st.selectbox("Ayak", ["Sağ", "Sol"]), st.selectbox("El", ["Sağ", "Sol"])
        ant_baslama = st.date_input("Antrenman Başlama Tarihi")

    st.divider()
    st.subheader("⏱️ Test Ölçümleri (2 Deneme)")
    
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    test_data = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            st.markdown(f"**{t_ad}**")
            d1 = st.number_input("1. Deneme", key=f"{t_ad}_d1", format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}_d2", format="%.3f")
            best = (min(d1, d2) if d1>0 and d2>0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            test_data[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    submit = st.form_submit_button("VERİYİ ÇEYREK DİLİMİNE GÖRE ANALİZ ET VE KAYDET", use_container_width=True)

if submit:
    # Çeyrek Ataması
    q_label = f"{dogum_tarihi.year}_{get_quarter(dogum_tarihi)}"
    
    # Veri Hazırlama
    entry = {
        "Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum_tarihi, "Boy": boy, "Kilo": kilo,
        "Ayak": ayak, "El": el, "Ant_Baslama": ant_baslama, "Grup_Ceyrek": q_label,
        "Kayit_Zamani": datetime.now()
    }
    for t, v in test_data.items():
        entry[f"{t}_D1"] = v["D1"]; entry[f"{t}_D2"] = v["D2"]; entry[t] = v["Best"]
    
    veri_kaydet(pd.DataFrame([entry]))
    
    # Akran Analizi (Sadece aynı çeyrektekilerle kıyasla)
    full_db = veri_oku()
    akran_db = full_db[full_db['Grup_Ceyrek'] == q_label]
    
    analiz_listesi = []
    for t_ad in test_specs.keys():
        seri = akran_db[t_ad]
        ort, std = seri.mean(), (seri.std() if len(seri) > 1 else 0)
        mak, min_v = seri.max(), seri.min()
        z = (test_data[t_ad]["Best"] - ort) / std if std > 0 else 0
        
        analiz_listesi.append({
            "Test": t_ad, "Skor": test_data[t_ad]["Best"], "Akran Ort.": round(ort,3),
            "Std.Sapma": round(std,3), "Max": mak, "Min": min_v, "Z-Skor": round(z,2)
        })

    st.info(f"📍 Katılımcı **{q_label}** çeyrek dilimine atanmıştır. İstatistikler bu gruptaki akranlarına göredir.")
    st.table(pd.DataFrame(analiz_listesi))

    # --- PDF RAPORLAMA (Her Test Ayrı Bölüm) ---
    def generate_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        w, h = A4
        
        c.setFont(FONT, 18); c.drawCentredString(w/2, h-40, "AKADEMİK PERFORMANS ANALİZ RAPORU")
        c.setFont(FONT, 10); c.drawString(50, h-70, f"Katılımcı: {ad} {soyad} | Dilim: {q_label} | Tarih: {datetime.now().strftime('%d.%m.%Y')}")
        c.line(50, h-75, 550, h-75)

        y = h - 100
        for stat in analiz_listesi:
            if y < 300: c.showPage(); y = h - 50
            
            c.setFont(FONT + "-Bold" if "Arial" in FONT else "Helvetica-Bold", 12)
            c.drawString(50, y, f"TEST: {stat['Test']}")
            y -= 15
            c.setFont(FONT, 9)
            stat_txt = f"Skor: {stat['Skor']} | Akran Ort: {stat['Akran Ort.']} | Std: {stat['Std.Sapma']} | Maks: {stat['Max']} | Min: {stat['Min']} | Z: {stat['Z-Skor']}"
            c.drawString(60, y, stat_txt)
            
            # Grafik
            plt.figure(figsize=(5, 2.5))
            plt.barh(['En Kötü', 'Akran Ort.', 'Katılımcı', 'En İyi'], 
                     [stat['Min'], stat['Akran Ort.'], stat['Skor'], stat['Max']], 
                     color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
            plt.tight_layout()
            img_buf = io.BytesIO(); plt.savefig(img_buf, format='png', dpi=100); plt.close()
            
            y -= 130
            c.drawImage(io.BytesIO(img_buf.getvalue()), 60, y, width=350, preserveAspectRatio=True)
            y -= 30; c.line(50, y, 500, y); y -= 20

        c.save(); buffer.seek(0)
        return buffer

    st.download_button("📄 Detaylı Akran Raporu İndir (PDF)", generate_pdf(), f"{ad}_{soyad}_Ceyrek_Raporu.pdf")
