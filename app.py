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

# --- 1. FONT KAYDI (ARIAL.TTF KONTROLÜ) ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

def font_kaydet():
    font_dosyasi = "arial.ttf"
    font_adi = "Helvetica" # Varsayılan (hata durumunda)

    if os.path.exists(font_dosyasi):
        try:
            # Arial'i sisteme 'Arial_Tr' adıyla kaydediyoruz
            pdfmetrics.registerFont(TTFont('Arial_Tr', font_dosyasi))
            font_adi = 'Arial_Tr'
        except Exception as e:
            st.error(f"Font kaydı sırasında hata oluştu: {e}")
    else:
        # Eğer arial.ttf yoksa sistem fontlarını dene
        linux_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(linux_font):
            pdfmetrics.registerFont(TTFont('Arial_Tr', linux_font))
            font_adi = 'Arial_Tr'
        else:
            st.warning("⚠️ arial.ttf bulunamadı! Lütfen dosyayı ana dizine yükleyin.")
            
    return font_adi

SECILEN_FONT = font_kaydet()

# Matplotlib için font ayarı
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

# --- 2. VERİ YÖNETİMİ ---
DB_FILE = "gkd_akademik_veritabani.csv"

def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- 3. PDF ÜRETME (KRİTİK TÜRKÇE AYARLARI) ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Türkçe Stil Tanımları
    # 'encoding' parametresi ReportLab'in modern sürümlerinde otomatik UTF-8'dir
    baslik_stili = ParagraphStyle('B', fontName=SECILEN_FONT, fontSize=16, alignment=1, spaceAfter=20)
    normal_stil = ParagraphStyle('N', fontName=SECILEN_FONT, fontSize=10)
    
    akis = [Paragraph("BİREYSEL PERFORMANS VE GELİŞİM RAPORU", baslik_stili)]
    
    # Künye Tablosu
    info = [
        [Paragraph(f"<b>Sporcu ID:</b> {secilen['ID']}", normal_stil), 
         Paragraph(f"<b>Grup:</b> {secilen['Ceyrek']}", normal_stil)],
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", normal_stil), 
         Paragraph(f"<b>Ölçüm Tarihi:</b> {secilen['Olcum_Tarihi']}", normal_stil)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", normal_stil), 
         Paragraph(f"<b>Başlama:</b> {secilen['Baslama_Tarihi']}", normal_stil)]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    # Tablo içindeki her metni Paragraph() içine almak Türkçe karakterler için EN GÜVENLİ yoldur.
    tablo_verisi = [[
        Paragraph("<b>Test Adı</b>", normal_stil), 
        Paragraph("<b>Skor</b>", normal_stil), 
        Paragraph("<b>Grup Ort.</b>", normal_stil), 
        Paragraph("<b>Z-Skor</b>", normal_stil), 
        Paragraph("<b>Durum</b>", normal_stil)
    ]]
    
    for r in analiz_datalari:
        tablo_verisi.append([
            Paragraph(str(r['Test']), normal_stil),
            Paragraph(str(r['Skor']), normal_stil),
            Paragraph(str(r['Grup Ort.']), normal_stil),
            Paragraph(str(r['Z-Skor']), normal_stil),
            Paragraph(str(r['Durum']), normal_stil)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[160, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,0), 'CENTER')
    ]))
    akis.append(t_analiz)

    # Grafikler... (Önceki kodla aynı şekilde eklenebilir)
    # [Buradaki grafik kodlarını kısa tutmak için atladım, PDF akışını tamamlar]

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ARAYÜZ ---
db = veri_oku()
st.sidebar.info(f"Aktif Font: {SECILEN_FONT}")

# Önemli: Raporu indirirken mutlaka Paragraph() ile sarmalanmış veriyi kullanıyoruz.
if st.button("Örnek Rapor Üret (Test)"):
    if not db.empty:
        test_sporcu = db.iloc[0].to_dict()
        # Test amaçlı dummy veri
        analiz_test = [{"Test": "Şınav Çekme", "Skor": "20", "Grup Ort.": "18", "Z-Skor": "1.2", "Durum": "İyi"}]
        pdf = pdf_olustur(test_sporcu, analiz_test, db)
        st.download_button("PDF İndir", pdf, "test_raporu.pdf")
