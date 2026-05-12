import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io
from datetime import datetime

# ReportLab Bileşenleri
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. SİSTEM AYARLARI VE FONT ---
st.set_page_config(page_title="GKD Akademik Performans", layout="wide")

def font_yukle():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ["arial.ttf", "Arial.ttf", "ARIAL.TTF"]:
        path = os.path.join(current_dir, name)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Arial_Tr', path))
                return 'Arial_Tr'
            except: continue
    return 'Helvetica'

FONT = font_yukle()
DB_FILE = "gkd_akademik_veritabani.csv"

# --- 2. VERİ YÖNETİMİ FONKSİYONLARI ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, encoding='utf-16')
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    if mevcut.empty:
        if 'Son_Guncelleme' not in yeni_df.columns:
            yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    # Ad ve Soyad üzerinden eşleştirme (Mükerrer kaydı önlemek için)
    for index, row in yeni_df.iterrows():
        ad, soyad = row['Ad'], row['Soyad']
        mask = (mevcut['Ad'].astype(str) == str(ad)) & (mevcut['Soyad'].astype(str) == str(soyad))
        
        if mask.any():
            idx = mevcut.index[mask][0]
            for col in yeni_df.columns:
                val = row[col]
                if pd.notnull(val) and val != "":
                    mevcut.loc[idx, col] = val
            mevcut.loc[idx, 'Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        else:
            row_dict = row.to_dict()
            row_dict['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
            mevcut = pd.concat([mevcut, pd.DataFrame([row_dict])], ignore_index=True)
            
    mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. PDF ÜRETME ---
def profesyonel_pdf_uret(secilen, analiz_datalari):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle('Baslik', parent=styles['Heading1'], fontName=FONT, fontSize=16, alignment=1, spaceAfter=20)
    alt_baslik_stili = ParagraphStyle('AltBaslik', parent=styles['Normal'], fontName=FONT, fontSize=11, leading=14)
    tablo_icerik_stili = ParagraphStyle('TabloIcerik', parent=styles['Normal'], fontName=FONT, fontSize=9, alignment=1)
    test_baslik_stili = ParagraphStyle('TestBaslik', parent=styles['Heading2'], fontName=FONT, fontSize=13, spaceBefore=15, color=colors.navy)

    akis = []
    akis.append(Paragraph("BİREYSEL PERFORMANS ANALİZ RAPORU", baslik_stili))
    
    info_data = [
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", alt_baslik_stili), 
         Paragraph(f"<b>Grup/Çeyrek:</b> {secilen['Ceyrek']}", alt_baslik_stili)],
        [Paragraph(f"<b>Doğum Tarihi:</b> {secilen['Dogum_Tarihi']}", alt_baslik_stili),
         Paragraph(f"<b>Başlama Tarihi:</b> {secilen['Baslama_Tarihi']}", alt_baslik_stili)],
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    akis.append(info_table)
    akis.append(Spacer(1, 15))

    tablo_verisi = [[Paragraph(f"<b>{h}</b>", tablo_icerik_stili) for h in ["Test Adı", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]]
    for r in analiz_datalari:
        tablo_verisi.append([
            Paragraph(str(r['Test']), tablo_icerik_stili),
            Paragraph(str(r['Skor']), tablo_icerik_stili),
            Paragraph(str(r['Grup Ort.']), tablo_icerik_stili),
            Paragraph(str(r['Z-Skor']), tablo_icerik_stili),
            Paragraph(str(r['Durum']), tablo_icerik_stili)
        ])
    
    ozet_tablo = Table(tablo_verisi, colWidths=[130, 60, 70, 60, 100])
    ozet_tablo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)]))
    akis.append(ozet_tablo)

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2.2))
        plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, float(r['Z-Skor']), 3.0], color=['red', 'gray', 'blue', 'green'])
        plt.xlim(-3.5, 3.5)
        plt.axvline(0, color='black', linewidth=0.8, linestyle='--')
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=100)
        plt.close()
        akis.append(KeepTogether([Paragraph(f"• {r['Test']}", test_baslik_stili), Image(img_buf, width=400, height=150)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("🔍 Sporcu Seçimi")
    if not db.empty:
        isimler = (db['Ad'].astype(str) + " " + db['Soyad'].astype(str)).tolist()
        arama = st.selectbox("Kayıtlı Öğrenciler", ["-- Yeni Kayıt --"] + isimler)
        if arama != "-- Yeni Kayıt --":
            secilen_profil = db.iloc[isimler.index(arama)]
    
    st.divider()
    st.subheader("📥 Toplu Veri Yükleme")
    yuklenen_dosya = st.file_uploader("Excel veya CSV Yükle", type=['xlsx', 'csv'])
    if yuklenen_dosya and st.button("Verileri Havuza Aktar"):
        try:
            df_yeni = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.endswith('.csv') else pd.read_excel(yuklenen_dosya)
            # Tarih ve Çeyrek düzeltme
            df_yeni['Dogum_Tarihi'] = pd.to_datetime(df_yeni['Dogum_Tarihi']).dt.strftime('%Y-%m-%d')
            def cq(t_str):
                t = datetime.strptime(t_str, '%Y-%m-%d')
                return f"{t.year}_Q{(t.month-1)//3+1}"
            df_yeni['Ceyrek'] = df_yeni['Dogum_Tarihi'].apply(cq)
            veri_kaydet_ve_merge(df_yeni)
            st.success("Aktarım Tamamlandı!"); st.rerun()
        except Exception as e: st.error(f"Hata: {e}")

# --- 5. VERİ GİRİŞ FORMU ---
with st.form("ana_veri_formu"):
    st.subheader("👤 Sporcu ve Test Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2010,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 160.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 50.0)

    test_specs = {"5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min"}
    yeni_veriler = {}
    st.write("---")
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v_best = float(secilen_profil[t_ad]) if secilen_profil is not None and t_ad in secilen_profil else 0.0
            yeni_veriler[t_ad] = st.number_input(f"{t_ad}", value=v_best, format="%.3f")

    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
        packet = {"Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), "Boy": boy, "Kilo": kilo, "Ceyrek": q}
        packet.update(yeni_veriler)
        veri_kaydet_ve_merge(pd.DataFrame([packet]))
        st.success("Veriler güncellendi!"); st.rerun()

# --- 6. ANALİZ VE RAPORLAMA ---
if secilen_profil is not None:
    st.divider()
    f_db = veri_oku()
    akranlar = f_db[f_db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    
    for t_ad, mod in test_specs.items():
        skor = float(secilen_profil[t_ad])
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        if skor > 0 and len(seri) > 1:
            ort, std = seri.mean(), seri.std()
            z_ham = (skor - ort) / std if std > 0 else 0
            z_final = round(-z_ham if mod == "min" else z_ham, 2)
            z_final = max(min(z_final, 3.0), -3.0)
            
            if z_final >= 2.0: durum = "🌟 ELİT (+2/+3)"
            elif z_final >= 1.0: durum = "✅ ÜST DÜZEY (+1/+2)"
            elif z_final > -1.0: durum = "⚪ ORTALAMA (-1/+1)"
            elif z_final > -2.0: durum = "⚠️ GELİŞTİRİLMELİ (-1/-2)"
            else: durum = "🆘 KRİTİK (-2/-3)"
            
            analiz_datalari.append({"Test": t_ad, "Skor": skor, "Grup Ort.": round(ort,2), "Z-Skor": z_final, "Durum": durum})

    if analiz_datalari:
        st.subheader("📊 Performans Analizi (+3 / -3 Skalası)")
        st.table(pd.DataFrame(analiz_datalari))
        pdf_dosyasi = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button("📄 Akademik PDF Raporu İndir", data=pdf_dosyasi, file_name=f"{ad}_{soyad}_Analiz.pdf")
