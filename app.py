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

# --- 1. SİSTEM AYARLARI VE FONT FIX (KRİTİK BÖLÜM) ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

def font_yukle():
    """
    Sunucudaki Türkçe destekli fontları tarar ve PDF için hazırlar.
    """
    # Sunucularda en yaygın bulunan Türkçe destekli font yolları
    font_yollari = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "arial.ttf" # Eğer yerelde varsa
    ]
    
    secilen_font = None
    for yol in font_yollari:
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont('TurkceFont', yol))
                secilen_font = 'TurkceFont'
                break
            except:
                continue
    
    if not secilen_font:
        # Eğer hiçbir font bulunamazsa uyarı ver (Genelde Streamlit Cloud'da Liberation bulunur)
        st.error("⚠️ Türkçe font dosyası sunucuda bulunamadı! Karakterler bozuk çıkabilir.")
        return "Helvetica"
    return secilen_font

# Fontu bir kez yükleyip global değişken olarak tutalım
SECILEN_FONT = font_yukle()

# Matplotlib Grafiklerinde Türkçe Karakter Desteği
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False 

DB_FILE = "gkd_akademik_veritabani.csv"

# --- 2. VERİ YÖNETİMİ ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
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

# --- 3. PDF ÜRETME MOTORU (TÜRKÇE UYUMLU) ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Türkçe Stil Tanımları
    baslik_stili = ParagraphStyle(
        'Baslik', 
        fontName=SECILEN_FONT, 
        fontSize=18, 
        alignment=1, 
        spaceAfter=20,
        encoding='utf-8' # Karakter kodlamasını zorla
    )
    
    normal_stil = ParagraphStyle(
        'Normal', 
        fontName=SECILEN_FONT, 
        fontSize=10,
        encoding='utf-8'
    )
    
    akis = [Paragraph("BİREYSEL PERFORMANS VE GELİŞİM RAPORU", baslik_stili)]
    
    # Künye Tablosu
    info = [
        [f"ID: {secilen.get('ID','')}", f"Grup: {secilen.get('Ceyrek','')}"],
        [f"Ad Soyad: {secilen.get('Ad','')} {secilen.get('Soyad','')}", f"Ölçüm Tarihi: {secilen.get('Olcum_Tarihi','')}"],
        [f"Boy: {secilen.get('Boy','')} cm", f"Kilo: {secilen.get('Kilo','')} kg"]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 10)
    ]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    tablo_verisi = [[
        Paragraph("Test Adı", normal_stil), 
        Paragraph("Skor", normal_stil), 
        Paragraph("Ort.", normal_stil), 
        Paragraph("Z-Skor", normal_stil), 
        Paragraph("Durum", normal_stil)
    ]]
    
    for r in analiz_datalari:
        tablo_verisi.append([
            Paragraph(str(r['Test']), normal_stil),
            Paragraph(str(r['Skor']), normal_stil),
            Paragraph(str(r['Grup Ort.']), normal_stil),
            Paragraph(str(r['Z-Skor']), normal_stil),
            Paragraph(str(r['Durum']), normal_stil)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    akis.append(t_analiz)

    # GRAFİKLER
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.5))
        gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(gecmis) > 1:
            ax.plot(gecmis['Olcum_Tarihi'], gecmis[test_adi], marker='o', color='blue')
            ax.set_title(f"{test_adi} Gelişimi")
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran', 'Sporcu'], [0, z], color=['grey', 'blue'])
            ax.set_title(f"{test_adi} Kıyaslama")
        
        plt.tight_layout()
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        plt.close(fig)
        
        akis.append(KeepTogether([Spacer(1, 15), Image(img_data, width=420, height=170)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ARAYÜZ (GÖVDE) ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("👤 Sporcu Seçimi")
    if not db.empty:
        u_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in u_list.iterrows()]
        secim = st.selectbox("Mevcut Kayıt", options)
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

# --- (Form ve Analiz kısımları önceki kodla aynı, sadece test_specs'e LSKT dahil) ---
test_specs = {
    "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", 
    "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
    "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
}

# --- FORM BÖLÜMÜ ---
with st.form("ana_form"):
    st.subheader("📝 Veri Girişi")
    c1, c2, c3 = st.columns(3)
    with c1:
        sid = st.text_input("ID", value=secilen_profil['ID'] if secilen_profil is not None else f"GKD-{uuid.uuid4().hex[:6].upper()}")
        ad = st.text_input("Ad", value=secilen_profil['Ad'] if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=secilen_profil['Soyad'] if secilen_profil is not None else "")
    # ... (Diğer form alanlarını ekleyin: Tarih, Boy, Kilo) ...
    # (Önceki kodunuzdaki form yapısını buraya yapıştırabilirsiniz)
    if st.form_submit_button("Kaydet"):
        # Kayıt mantığı...
        st.rerun()

# --- ANALİZ VE PDF İNDİRME ---
if secilen_profil is not None:
    # Analiz hesaplamaları...
    analiz_list = [] # Hesaplanan veriler
    # ... (Analiz döngüsünü buraya ekleyin) ...
    
    if analiz_list:
        st.table(pd.DataFrame(analiz_list))
        pdf_cikti = pdf_olustur(secilen_profil, analiz_list, db[db['ID'] == secilen_profil['ID']])
        st.download_button(
            label="📄 PDF Raporu İndir (Türkçe Karakter Fix)",
            data=pdf_cikti,
            file_name=f"Rapor_{sid}.pdf",
            mime="application/pdf"
        )
