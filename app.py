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

# --- SİSTEM AYARLARI ---
st.set_page_config(page_title="GKD Akademik Raporlama", layout="wide")

def font_yukle():
    if os.path.exists("arial.ttf"):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Tr', 'arial.ttf'))
            return "Arial_Tr"
        except: return "Helvetica"
    return "Helvetica"

FONT = font_yukle()
DB_FILE = "akademik_veri_havuzu.csv"

# --- AKADEMİK ÇEYREK HESAPLAMA ---
def get_quarter_label(date):
    month = date.month
    if 1 <= month <= 3: q = "Q1"
    elif 4 <= month <= 6: q = "Q2"
    elif 7 <= month <= 9: q = "Q3"
    else: q = "Q4"
    return f"{date.year}_{q}"

# --- VERİ TABANI İŞLEMLERİ ---
def veri_kaydet(df):
    if not os.path.isfile(DB_FILE):
        df.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        df.to_csv(DB_FILE, mode='a', header=False, index=False, encoding='utf-16')

def veri_oku():
    if os.path.isfile(DB_FILE):
        return pd.read_csv(DB_FILE, encoding='utf-16')
    return pd.DataFrame()

# --- ARAYÜZ ---
st.title("🏃 GKD Akademik Analiz & Araştırma Portalı")

with st.sidebar:
    st.header("🔬 Araştırma Veri Yönetimi")
    db = veri_oku()
    if not db.empty:
        st.write(f"Toplam Kayıt: {len(db)}")
        st.download_button("Tüm Veritabanını İndir (SPSS/Excel)", 
                           db.to_csv(index=False).encode('utf-16'), 
                           "gkd_toplu_veri.csv", "text/csv")

with st.form("ana_form"):
    st.subheader("👤 Katılımcı Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad, soyad = st.text_input("Ad"), st.text_input("Soyad")
        dogum = st.date_input("Doğum Tarihi")
    with c2:
        boy, kilo = st.number_input("Boy (cm)"), st.number_input("Kilo (kg)")
    with c3:
        ayak, el = st.selectbox("Ayak", ["Sağ", "Sol"]), st.selectbox("El", ["Sağ", "Sol"])
        baslama = st.date_input("Antrenman Başlama")

    st.divider()
    st.subheader("⏱️ Test Sonuçları (2 Deneme)")
    testler = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }
    
    input_data = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(testler.items()):
        with cols[i % 2]:
            st.write(f"**{t_ad}**")
            d1 = st.number_input("1. Deneme", key=f"{t_ad}1", format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}2", format="%.3f")
            best = (min(d1, d2) if d1>0 and d2>0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            input_data[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    submit = st.form_submit_button("ANALİZ ET VE ARŞİVE EKLE")

if submit:
    ceyrek = get_quarter_label(dogum)
    
    # 1. Veritabanına Ekle (Araştırma için tüm denemeleri saklar)
    new_entry = {"Tarih": datetime.now(), "Ad": ad, "Soyad": soyad, "Ceyrek": ceyrek}
    for t, v in input_data.items():
        new_entry[f"{t}_D1"] = v["D1"]; new_entry[f"{t}_D2"] = v["D2"]; new_entry[t] = v["Best"]
    
    veri_kaydet(pd.DataFrame([new_entry]))
    
    # 2. İstatistikleri Hesapla (Sadece aynı çeyrekteki akranlarla)
    current_db = veri_oku()
    akranlar = current_db[current_db['Ceyrek'] == ceyrek]
    
    analizler = []
    for t_ad in testler.keys():
        seri = akranlar[t_ad]
        ort, std = seri.mean(), seri.std() if len(seri)>1 else 0
        mak, mini = seri.max(), seri.min()
        skor = input_data[t_ad]["Best"]
        z = (skor - ort) / std if std > 0 else 0
        
        analizler.append({
            "Test": t_ad, "Skor": skor, "Ort": round(ort,3), 
            "Std": round(std,3), "Max": mak, "Min": mini, "Z": round(z,2)
        })

    st.success(f"Kayıt Tamamlandı. Katılımcı Grubu: {ceyrek}")
    st.table(pd.DataFrame(analizler))

    # 3. PDF RAPOR (Her Test Ayrı Görselleştirme)
    def pdf_olustur():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        
        c.setFont(FONT, 16); c.drawCentredString(w/2, h-50, "BİREYSEL AKADEMİK PERFORMANS RAPORU")
        c.setFont(FONT, 10); c.drawString(50, h-80, f"Sporcu: {ad} {soyad} | Dilim: {ceyrek}")
        c.line(50, h-85, 550, h-85)
        
        y = h - 110
        for item in analizler:
            if y < 280: c.showPage(); y = h - 50
            
            c.setFont(FONT, 12); c.drawString(50, y, f"TEST: {item['Test']}")
            y -= 15; c.setFont(FONT, 9)
            txt = f"Skor: {item['Skor']} | Ort: {item['Ort']} | Max: {item['Max']} | Min: {item['Min']} | Z: {item['Z']}"
            c.drawString(60, y, txt)
            
            # Grafik Çizimi
            plt.figure(figsize=(5, 2.5))
            plt.barh(['En Kötü', 'Akran Ort.', 'Sporcu', 'En İyi'], 
                     [item['Min'], item['Ort'], item['Skor'], item['Max']], 
                     color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
            plt.tight_layout()
            img_b = io.BytesIO(); plt.savefig(img_b, format='png', dpi=100); plt.close()
            
            y -= 130
            c.drawImage(io.BytesIO(img_b.getvalue()), 60, y, width=350, preserveAspectRatio=True)
            y -= 40; c.line(50, y, 500, y); y -= 20
            
        c.save(); buf.seek(0)
        return buf

    st.download_button("📄 Detaylı Raporu İndir (PDF)", pdf_olustur(), f"{ad}_{soyad}_Rapor.pdf")
