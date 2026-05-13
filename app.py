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

# --- 1. FONT VE SİSTEM AYARLARI ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

def font_sisteme_kaydet():
    """Ana dizindeki arial.ttf dosyasını sisteme entegre eder."""
    font_dosya_adi = "arial.ttf"
    
    # 1. Öncelik: Kullanıcının ana dizine koyduğu arial.ttf
    if os.path.exists(font_dosya_adi):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Turkce', font_dosya_adi))
            return 'Arial_Turkce'
        except Exception as e:
            st.error(f"Arial fontu kaydedilirken hata: {e}")
    
    # 2. Öncelik: Linux Sunucu Standart Fontu (Yedek Plan)
    linux_yolu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.exists(linux_yolu):
        pdfmetrics.registerFont(TTFont('Arial_Turkce', linux_yolu))
        return 'Arial_Turkce'
    
    return 'Helvetica'

# Global font değişkeni
FONT_ADI = font_sisteme_kaydet()

# Matplotlib için font ayarı (Türkçe karakterlerin grafiklerde çıkması için)
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

# --- 3. PDF ÜRETME MOTORU (ZORLANMIŞ TÜRKÇE) ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Fontu her Paragraph nesnesinde zorunlu kılan stil seti
    pdf_stili = ParagraphStyle(
        'Standard',
        fontName=FONT_ADI,
        fontSize=10,
        leading=12,
        alignment=0 # Sola yaslı
    )
    
    baslik_stili = ParagraphStyle(
        'Baslik',
        fontName=FONT_ADI,
        fontSize=18,
        alignment=1, # Ortalanmış
        spaceAfter=20
    )

    akis = [Paragraph("<b>BİREYSEL PERFORMANS ANALİZ RAPORU</b>", baslik_stili)]
    
    # Künye Tablosu (Metinler Paragraph içinde gönderiliyor)
    info_tablo_verisi = [
        [Paragraph(f"<b>ID:</b> {secilen['ID']}", pdf_stili), Paragraph(f"<b>Grup:</b> {secilen['Ceyrek']}", pdf_stili)],
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", pdf_stili), Paragraph(f"<b>Tarih:</b> {secilen['Olcum_Tarihi']}", pdf_stili)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", pdf_stili), Paragraph(f"<b>Başlama:</b> {secilen['Baslama_Tarihi']}", pdf_stili)]
    ]
    
    t_info = Table(info_tablo_verisi, colWidths=[240, 240])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT_ADI),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    akis.append(t_info)
    akis.append(Spacer(1, 20))

    # Analiz Tablosu
    # Başlıklar
    tablo_verisi = [[
        Paragraph("<b>Test Adı</b>", pdf_stili),
        Paragraph("<b>Skor</b>", pdf_stili),
        Paragraph("<b>Ort.</b>", pdf_stili),
        Paragraph("<b>Z-Skor</b>", pdf_stili),
        Paragraph("<b>Durum</b>", pdf_stili)
    ]]
    
    # Veri Satırları
    for r in analiz_datalari:
        tablo_verisi.append([
            Paragraph(str(r['Test']), pdf_stili),
            Paragraph(str(r['Skor']), pdf_stili),
            Paragraph(str(r['Grup Ort.']), pdf_stili),
            Paragraph(str(r['Z-Skor']), pdf_stili),
            Paragraph(str(r['Durum']), pdf_stili)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), FONT_ADI),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    akis.append(t_analiz)

    # GRAFİKLER
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.5))
        sporcu_gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(sporcu_gecmis) > 1:
            ax.plot(sporcu_gecmis['Olcum_Tarihi'], sporcu_gecmis[test_adi], marker='o', color='#E63946', lw=2)
            ax.set_title(f"{test_adi} Gelişim Grafiği", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran Ort.', 'Sporcu'], [0, z], color=['#A8DADC', '#457B9D'])
            ax.set_xlim(-3.5, 3.5)
            ax.axvline(0, color='black', lw=1)
            ax.set_title(f"{test_adi} Kıyaslama Analizi", fontsize=10)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=100)
        plt.close(fig)
        akis.append(KeepTogether([Spacer(1, 15), Image(img_buf, width=400, height=160)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ARAYÜZ (SIDEBAR VE FORM) ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("⚙️ Yönetim")
    st.info(f"Kullanılan Font: {FONT_ADI}") # Fontun başarılı yüklendiğini buradan teyit edebilirsiniz.
    
    if not db.empty:
        u_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in u_list.iterrows()]
        secim = st.selectbox("Sporcu Seç", options)
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

# --- 5. FORM VE ANALİZ DÖNGÜSÜ (ÖNCEKİ KODUNUZU BURAYA EKLEYİN) ---
# ... (Form girişleri, test_specs, hesaplamalar vs. önceki kodla aynıdır) ...
# Önemli olan PDF üretme butonunda pdf_olustur fonksiyonunu çağırmaktır.

if secilen_profil is not None:
    # Örnek analiz verisi oluşturma (Sizin hesaplama kodunuz buraya gelecek)
    test_sonuclari = [
        {"Test": "5m Sprint (sn)", "Skor": "1.250", "Grup Ort.": "1.300", "Z-Skor": "0.5", "Durum": "✅ ÜST"},
        {"Test": "LSKT Sağ (sn)", "Skor": "4.120", "Grup Ort.": "4.500", "Z-Skor": "1.2", "Durum": "🌟 ELİT"}
    ]
    
    if st.button("📄 PDF RAPORU OLUŞTUR"):
        pdf_cikti = pdf_olustur(secilen_profil, test_sonuclari, db[db['ID'] == secilen_profil['ID']])
        st.download_button(
            label="💾 PDF Dosyasını Bilgisayarına İndir",
            data=pdf_cikti,
            file_name=f"Rapor_{secilen_profil['Ad']}_{secilen_profil['Soyad']}.pdf",
            mime="application/pdf"
        )
