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

# --- 1. KESİN FONT YAPILANDIRMASI ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

def font_yukle_nihai():
    """Dosya adı hassasiyetine (Arial.ttf) göre fontu kaydeder."""
    # Dosya adını tam olarak sistemdeki haliyle yazıyoruz
    font_dosyasi = "Arial.ttf" 
    font_label = "Helvetica" # Varsayılan

    if os.path.exists(font_dosyasi):
        try:
            # Fontu 'Arial_Turkce' adıyla sisteme tanıtıyoruz
            pdfmetrics.registerFont(TTFont('Arial_Turkce', font_dosyasi))
            font_label = 'Arial_Turkce'
        except Exception as e:
            st.error(f"Font dosyası (Arial.ttf) okunurken hata: {e}")
    else:
        # Sunucu üzerindeki alternatif yolları tara
        alternatifler = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        for yol in alternatifler:
            if os.path.exists(yol):
                pdfmetrics.registerFont(TTFont('Arial_Turkce', yol))
                font_label = 'Arial_Turkce'
                break
        if font_label == "Helvetica":
            st.warning("⚠️ Arial.ttf bulunamadı, standart fonta dönüldü. Karakterler bozulabilir.")
            
    return font_label

SECILEN_FONT = font_yukle_nihai()

# --- 2. PDF ÜRETME (TÜRKÇE KARAKTER ZORLAMASI) ---
def pdf_olustur_nihai(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Türkçe Stil Tanımları
    # Her metni bu stil ile Paragraph içine alacağız
    tr_stil = ParagraphStyle(
        'TrStil',
        fontName=SECILEN_FONT,
        fontSize=10,
        leading=12,
        encoding='utf-8'
    )
    
    baslik_stili = ParagraphStyle(
        'BaslikStil',
        fontName=SECILEN_FONT,
        fontSize=18,
        alignment=1,
        spaceAfter=20
    )

    akis = [Paragraph("<b>BİREYSEL PERFORMANS VE GELİŞİM RAPORU</b>", baslik_stili)]
    
    # Künye Bilgileri
    info_data = [
        [Paragraph(f"<b>ID:</b> {secilen['ID']}", tr_stil), Paragraph(f"<b>Grup:</b> {secilen['Ceyrek']}", tr_stil)],
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", tr_stil), Paragraph(f"<b>Tarih:</b> {secilen['Olcum_Tarihi']}", tr_stil)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", tr_stil), Paragraph(f"<b>Başlama:</b> {secilen['Baslama_Tarihi']}", tr_stil)]
    ]
    
    t_info = Table(info_data, colWidths=[240, 240])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    akis.append(t_info)
    akis.append(Spacer(1, 20))

    # Analiz Tablosu
    tablo_verisi = [[
        Paragraph("<b>Test Adı</b>", tr_stil),
        Paragraph("<b>Skor</b>", tr_stil),
        Paragraph("<b>Ort.</b>", tr_stil),
        Paragraph("<b>Z-Skor</b>", tr_stil),
        Paragraph("<b>Durum</b>", tr_stil)
    ]]
    
    for r in analiz_datalari:
        tablo_verisi.append([
            Paragraph(str(r['Test']), tr_stil),
            Paragraph(str(r['Skor']), tr_stil),
            Paragraph(str(r['Grup Ort.']), tr_stil),
            Paragraph(str(r['Z-Skor']), tr_stil),
            Paragraph(str(r['Durum']), tr_stil)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT), # Tabloya fontu zorla
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    akis.append(t_analiz)

    # GRAFİKLER
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.5))
        # Matplotlib'de font sorunu yaşamamak için DejaVu Sans (Linux standardı) kullanıyoruz
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        
        sporcu_gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        if len(sporcu_gecmis) > 1:
            ax.plot(sporcu_gecmis['Olcum_Tarihi'], sporcu_gecmis[test_adi], marker='o', color='#1f77b4', lw=2)
            ax.set_title(f"{test_adi} Trendi", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran', 'Sporcu'], [0, z], color=['#cccccc', '#1f77b4'])
            ax.set_title(f"{test_adi} Analizi", fontsize=10)
        
        plt.tight_layout()
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100)
        plt.close(fig)
        akis.append(KeepTogether([Spacer(1, 15), Image(img_data, width=420, height=170)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 3. ARAYÜZ VE UYGULAMA ---
# (Veri okuma/kaydetme ve Streamlit form kısımları buraya eklenecek)
# Sidebar'da fontu teyit et:
st.sidebar.success(f"Aktif Font: {SECILEN_FONT}")

# Rapor indirme butonu içinde:
# pdf_data = pdf_olustur_nihai(secilen_profil, analiz_datalari, gecmis_data)
# st.download_button("PDF Raporu İndir", pdf_data, "Rapor.pdf")
