import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io, uuid
from datetime import datetime

# ReportLab Bileşenleri
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. SİSTEM VE FONT AYARLARI (KESİN ÇÖZÜM) ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

def font_yukle():
    """Linux sunucularda bulunan standart Türkçe destekli fontu yükler."""
    # Streamlit Cloud (Ubuntu/Debian) üzerinde bulunan standart font yolları
    font_yollari = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    
    font_adi = "Helvetica" # Varsayılan
    
    for yol in font_yollari:
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont('Turkce_Font', yol))
                font_adi = 'Turkce_Font'
                break
            except:
                continue
    return font_adi

SECILEN_FONT = font_yukle()

# Matplotlib için font ayarı (Grafik başlıkları için)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Liberation Sans', 'Arial']

# --- 2. VERİ YÖNETİMİ ---
DB_FILE = "gkd_akademik_veritabani.csv"

def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            # UTF-16 Excel uyumu için en güvenli yoldur
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_guncelle(yeni_df):
    mevcut = veri_oku()
    if mevcut.empty:
        mevcut = yeni_df
    else:
        for _, row in yeni_df.iterrows():
            mask = (mevcut['ID'].astype(str) == str(row['ID'])) & \
                   (mevcut['Olcum_Tarihi'].astype(str) == str(row['Olcum_Tarihi']))
            if mask.any():
                idx = mevcut.index[mask][0]
                for col in yeni_df.columns: mevcut.at[idx, col] = row[col]
            else:
                mevcut = pd.concat([mevcut, pd.DataFrame([row])], ignore_index=True)
    mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. PDF ÜRETME MOTORU ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Türkçe Stil Tanımları
    baslik_stili = ParagraphStyle('B', fontName=SECILEN_FONT, fontSize=16, alignment=1, spaceAfter=20)
    normal_stil = ParagraphStyle('N', fontName=SECILEN_FONT, fontSize=10)
    
    akis = [Paragraph("BİREYSEL PERFORMANS VE GELİŞİM RAPORU", baslik_stili)]
    
    # Künye Tablosu
    info = [
        [f"Sporcu ID: {secilen['ID']}", f"Grup: {secilen['Ceyrek']}"],
        [f"Ad Soyad: {secilen['Ad']} {secilen['Soyad']}", f"Ölçüm Tarihi: {secilen['Olcum_Tarihi']}"],
        [f"Boy/Kilo: {secilen['Boy']}cm / {secilen['Kilo']}kg", f"Başlama: {secilen['Baslama_Tarihi']}"]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5)
    ]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    tablo_verisi = [["Test Adı", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        tablo_verisi.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t_analiz = Table(tablo_verisi, colWidths=[160, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT), # Hücrelere fontu zorla
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9)
    ]))
    akis.append(t_analiz)

    # GRAFİKLER
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.5))
        gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(gecmis) > 1:
            ax.plot(gecmis['Olcum_Tarihi'], gecmis[test_adi], marker='o', color='#1f77b4', lw=2)
            ax.set_title(f"{test_adi} Gelişim Trendi", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran Ort.', 'Sporcu'], [0, z], color=['#cccccc', '#1f77b4'])
            ax.axvline(0, color='black', lw=0.8)
            ax.set_title(f"{test_adi} Kıyaslama (Z-Skor)", fontsize=10)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        img_stream = io.BytesIO()
        plt.savefig(img_stream, format='png', dpi=120)
        plt.close(fig)
        akis.append(KeepTogether([Spacer(1, 15), Image(img_stream, width=420, height=170)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. STREAMLIT ARAYÜZÜ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.title("👤 Sporcu Seçimi")
    if not db.empty:
        u_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in u_list.iterrows()]
        secim = st.selectbox("Mevcut Kayıtlar", options)
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

# Ana Form ve Analiz Mantığı...
# (Buradaki form yapısı ve analiz hesaplamaları önceki kodunuzla aynı kalabilir)
# Sadece PDF indirme butonunda 'pdf_olustur' fonksiyonunu çağırın.

st.info(f"Sistem Fontu: {SECILEN_FONT}") # Hangi fontun aktif olduğunu ekranda görün

# Form örneği (Kısaltılmış)
with st.form("kayit_formu"):
    st.subheader("📝 Performans Veri Girişi")
    # ... form alanları ...
    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        # Kayıt işlemleri...
        st.rerun()

if secilen_profil is not None:
    # Analiz sonuçlarını hesapla ve analiz_datalari listesine ekle...
    # (Önceki analiz döngünüzü buraya koyun)
    analiz_datalari = [] 
    
    # PDF Butonu
    if analiz_datalari:
        pdf_dosyasi = pdf_olustur(secilen_profil, analiz_datalari, db[db['ID'] == secilen_profil['ID']])
        st.download_button(
            label="📄 PDF Raporu İndir (Karakter Sorunu Giderildi)",
            data=pdf_dosyasi,
            file_name=f"Rapor_{secilen_profil['Ad']}_{secilen_profil['Soyad']}.pdf",
            mime="application/pdf"
        )
