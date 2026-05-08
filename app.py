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

# --- 2. VERİ YÖNETİMİ ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, encoding='utf-16')
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    if mevcut.empty:
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    ad, soyad = yeni_df['Ad'].iloc[0], yeni_df['Soyad'].iloc[0]
    mask = (mevcut['Ad'].astype(str) == str(ad)) & (mevcut['Soyad'].astype(str) == str(soyad))
    
    if mask.any():
        idx = mevcut.index[mask][0]
        for col in yeni_df.columns:
            val = yeni_df[col].iloc[0]
            if pd.notnull(val) and val != 0 and val != "":
                if col in mevcut.columns and mevcut[col].dtype != yeni_df[col].dtype:
                    mevcut[col] = mevcut[col].astype(object)
                mevcut.loc[idx, col] = val
        mevcut.loc[idx, 'Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        pd.concat([mevcut, yeni_df], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. PDF ÜRETME FONKSİYONU ---
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
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", alt_baslik_stili), 
         Paragraph(f"<b>El/Ayak:</b> {secilen['El']} / {secilen['Ayak']}", alt_baslik_stili)]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    akis.append(info_table)
    akis.append(Spacer(1, 10))

    tablo_verisi = [[Paragraph(f"<b>{h}</b>", tablo_icerik_stili) for h in ["Test Adı", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]]
    for r in analiz_datalari:
        z = r['Z-Skor']
        durum = "Üstün" if z > 1.5 else "İyi" if z > 0.5 else "Ortalama" if z > -0.5 else "Geliştirilmeli" if z > -1.5 else "Zayıf"
        tablo_verisi.append([
            Paragraph(str(r['Test']), tablo_icerik_stili),
            Paragraph(str(r['Skor']), tablo_icerik_stili),
            Paragraph(str(r['Grup Ort.']), tablo_icerik_stili),
            Paragraph(str(z), tablo_icerik_stili),
            Paragraph(durum, tablo_icerik_stili)
        ])
    
    ozet_tablo = Table(tablo_verisi, colWidths=[130, 60, 70, 60, 70])
    ozet_tablo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    akis.append(ozet_tablo)
    akis.append(Spacer(1, 20))

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2.5))
        plt.barh(['En Kötü', 'Ortalama', 'Sporcu', 'En İyi'], [float(r['En Kötü']), float(r['Grup Ort.']), float(r['Skor']), float(r['En İyi'])], color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=110)
        plt.close()
        img_buf.seek(0)
        akis.append(KeepTogether([Paragraph(f"• {r['Test']} Analizi (Z-Skor: {r['Z-Skor']})", test_baslik_stili), Image(img_buf, width=380, height=160), Spacer(1, 15)]))

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
    st.subheader("📊 Araştırmacı Menüsü")
    if not db.empty:
        try:
            research_db = db.copy()
            research_db['Sporcu_ID'] = research_db.groupby(['Ad', 'Soyad']).ngroup() + 1000
            research_db = research_db.drop(columns=[c for c in ['Ad', 'Soyad', 'Son_Guncelleme'] if c in research_db.columns])
            towrite = io.BytesIO()
            research_db.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📈 Araştırma Veri Setini İndir", towrite.getvalue(), f"veriseti_{datetime.now().strftime('%Y%m%d')}.xlsx")
        except:
            st.error("Excel çıktısı için 'openpyxl' yükleyin.")

with st.form("ana_veri_formu"):
    st.subheader("👤 Sporcu Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2010,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
        v_baslama = datetime.strptime(str(secilen_profil['Baslama_Tarihi']), '%Y-%m-%d') if secilen_profil is not None and str(secilen_profil['Baslama_Tarihi']) != 'nan' else datetime.now()
        baslama = st.date_input("Antrenmana Başlama Tarihi", value=v_baslama)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 160.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 50.0)
        ayak = st.selectbox("Ayak", ["Sağ", "Sol"], index=0 if secilen_profil is None or secilen_profil['Ayak']=="Sağ" else 1)
        el = st.selectbox("El", ["Sağ", "Sol"], index=0 if secilen_profil is None or secilen_profil['El']=="Sağ" else 1)

    st.divider()
    test_specs = {"5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min", "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"}
    yeni_veriler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v_d1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None else 0.0
            v_d2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v_d1, format="%.3f")
            d2 = st.number_input(f"{t_ad} D2", value=v_d2, format="%.3f")
            best = (min(d1, d2) if d1>0 and d2>0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    if st.form_submit_button("VERİLERİ KAYDET"):
        q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
        packet = {"Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum, "Baslama_Tarihi": baslama, "Boy": boy, "Kilo": kilo, "Ayak": ayak, "El": el, "Ceyrek": q}
        for t, v in yeni_veriler.items():
            packet[f"{t}_D1"] = v["D1"]; packet[f"{t}_D2"] = v["D2"]; packet[t] = v["Best"]
        veri_kaydet_ve_merge(pd.DataFrame([packet]))
        st.success("Kaydedildi!"); st.rerun()

# --- 5. ANALİZ VE RAPORLAMA ---
if secilen_profil is not None:
    st.divider()
    f_db = veri_oku()
    akranlar = f_db[f_db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    for t_ad, mod in test_specs.items():
        skor = float(secilen_profil[t_ad])
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        if skor > 0 and not seri.empty:
            ort = seri.mean()
            std = seri.std() if len(seri)>1 else 0
            en_iyi, en_kotu = (seri.min(), seri.max()) if mod == "min" else (seri.max(), seri.min())
            analiz_datalari.append({"Test": t_ad, "Skor": skor, "Grup Ort.": round(ort,3), "Z-Skor": round((skor-ort)/std if std>0 else 0, 2), "En İyi": en_iyi, "En Kötü": en_kotu})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        pdf_dosyasi = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button(label="📄 Yorumlu PDF İndir", data=pdf_dosyasi, file_name=f"{ad}_{soyad}_Analiz.pdf", key="pdf_down")
