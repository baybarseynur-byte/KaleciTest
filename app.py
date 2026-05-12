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

# --- 1. SİSTEM AYARLARI ---
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
            # UTF-16 ve UTF-8 denemesi
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-16')
            except:
                df = pd.read_csv(DB_FILE, encoding='utf-8')
            
            if not df.empty:
                df.columns = df.columns.str.strip() # Sütun boşluklarını temizle
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_yeni_olcum(yeni_df):
    mevcut = veri_oku()
    yeni_df.columns = yeni_df.columns.str.strip()
    
    if 'Olcum_Tarihi' not in yeni_df.columns:
        yeni_df['Olcum_Tarihi'] = datetime.now().strftime("%Y-%m-%d")
    
    if mevcut.empty or 'Ad' not in mevcut.columns:
        mevcut = yeni_df
    else:
        for _, row in yeni_df.iterrows():
            # Güvenli karşılaştırma
            mask = (mevcut['Ad'].astype(str) == str(row['Ad'])) & \
                   (mevcut['Soyad'].astype(str) == str(row['Soyad'])) & \
                   (mevcut['Olcum_Tarihi'].astype(str) == str(row['Olcum_Tarihi']))
            
            if mask.any():
                idx = mevcut.index[mask][0]
                for col in yeni_df.columns:
                    mevcut.at[idx, col] = row[col]
            else:
                mevcut = pd.concat([mevcut, pd.DataFrame([row])], ignore_index=True)
    
    mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. PDF ÜRETME (Öncekiyle aynı) ---
def profesyonel_pdf_uret(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    b_stili = ParagraphStyle('B', fontName=FONT, fontSize=16, alignment=1, spaceAfter=20)
    h_stili = ParagraphStyle('H', fontName=FONT, fontSize=12, spaceBefore=10, textColor=colors.navy)

    akis = [Paragraph("BİREYSEL GELİŞİM VE PERFORMANS RAPORU", b_stili)]
    
    info = [
        [f"Ad Soyad: {secilen.get('Ad','')} {secilen.get('Soyad','')}", f"Grup: {secilen.get('Ceyrek','')}"],
        [f"Boy/Kilo: {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", f"Ölçüm Tarihi: {secilen.get('Olcum_Tarihi','')}"]
    ]
    t = Table(info, colWidths=[250, 250])
    t.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), FONT)]))
    akis.append(t)
    akis.append(Spacer(1, 15))

    akis.append(Paragraph("Mevcut Ölçüm Analizi", h_stili))
    veriler = [["Test", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        veriler.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t_mevcut = Table(veriler, colWidths=[140, 70, 70, 60, 100])
    t_mevcut.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND',(0,0),(-1,0), colors.whitesmoke), ('FONTNAME', (0,0), (-1,-1), FONT)]))
    akis.append(t_mevcut)

    doc.build(akis); buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("🔍 Sporcu Seçimi")
    
    # Sütun kontrolü yaparak hata almayı engelliyoruz
    if not db.empty and 'Ad' in db.columns and 'Soyad' in db.columns:
        sporcu_listesi = db.groupby(['Ad', 'Soyad']).size().index.tolist()
        isimler = [f"{s[0]} {s[1]}" for s in sporcu_listesi]
        arama = st.selectbox("Kayıtlı Sporcu Düzenle", ["-- Yeni Kayıt --"] + isimler)
        
        if arama != "-- Yeni Kayıt --":
            ad_s, soyad_s = arama.split(" ", 1)
            gecmis_veriler = db[(db['Ad'] == ad_s) & (db['Soyad'] == soyad_s)]
            if 'Olcum_Tarihi' in gecmis_veriler.columns:
                gecmis_veriler = gecmis_veriler.sort_values('Olcum_Tarihi', ascending=False)
            secilen_profil = gecmis_veriler.iloc[0]
    else:
        st.info("Henüz kayıtlı sporcu yok.")

    st.divider()
    st.subheader("📊 Araştırmacı Portalı")
    if not db.empty:
        # Hatalı olan satırı düzelttik: Sütun varsa sırala, yoksa düz ver
        siralama_sutunlari = [c for c in ['Ad', 'Olcum_Tarihi'] if c in db.columns]
        output_df = db.sort_values(siralama_sutunlari) if siralama_sutunlari else db
        
        towrite = io.BytesIO()
        output_df.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("Excel: Tüm Verileri İndir", towrite.getvalue(), "sporcu_veritabani.xlsx")

# --- 5. VERİ GİRİŞ FORMU (Öncekiyle aynı) ---
with st.form("olcum_formu"):
    st.subheader("📝 Yeni Ölçüm Girişi")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        olcum_tarihi = st.date_input("Ölçüm Tarihi", value=datetime.now())
        v_dt_str = str(secilen_profil['Dogum_Tarihi']) if secilen_profil is not None else "2012-01-01"
        try: v_dt = datetime.strptime(v_dt_str, '%Y-%m-%d')
        except: v_dt = datetime(2012, 1, 1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 150.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 40.0)

    test_specs = {"5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min", "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"}
    yeni_veriler = {}
    st.divider()
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v1, format="%.3f", key=f"{t_ad}1")
            d2 = st.number_input(f"{t_ad} D2", value=v2, format="%.3f", key=f"{t_ad}2")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "B": best}

    if st.form_submit_button("ÖLÇÜMÜ KAYDET"):
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            p = {"Ad": ad.strip(), "Soyad": soyad.strip(), "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), 
                 "Olcum_Tarihi": olcum_tarihi.strftime('%Y-%m-%d'), "Boy": boy, "Kilo": kilo, "Ceyrek": q}
            for t, v in yeni_veriler.items():
                p[f"{t}_D1"], p[f"{t}_D2"], p[t] = v["D1"], v["D2"], v["B"]
            
            veri_kaydet_yeni_olcum(pd.DataFrame([p]))
            st.success(f"Kaydedildi!")
            st.rerun()

# --- 6. ANALİZ (Öncekiyle aynı) ---
if secilen_profil is not None:
    st.divider()
    st.subheader(f"📊 {secilen_profil['Ad']} {secilen_profil['Soyad']} - Analiz")
    akranlar = db[db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    for t_ad, mod in test_specs.items():
        if t_ad in secilen_profil:
            skor = float(secilen_profil[t_ad])
            seri = akranlar[t_ad].replace(0, np.nan).dropna()
            if skor > 0 and len(seri) > 0:
                ort = seri.mean()
                std = seri.std() if len(seri) > 1 else 0.1
                z_f = round(-(skor-ort)/std if mod=="min" else (skor-ort)/std, 2)
                d = "🌟 ELİT" if z_f >= 2 else ("✅ ÜST" if z_f >= 1 else ("⚪ ORT" if z_f > -1 else "🆘 KRİTİK"))
                analiz_datalari.append({"Test": t_ad, "Skor": skor, "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": d})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        sporcu_gecmis = db[(db['Ad'] == secilen_profil['Ad']) & (db['Soyad'] == secilen_profil['Soyad'])]
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari, sporcu_gecmis)
        st.download_button("📄 PDF Raporu", pdf, f"Rapor_{secilen_profil['Ad']}.pdf")
