import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io, uuid, requests
from datetime import datetime

# ReportLab Bileşenleri
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. SİSTEM AYARLARI VE FONT İNDİRME ---
st.set_page_config(page_title="GKD Akademik Performans", layout="wide")

def font_hazirla():
    """Türkçe destekli fontu GitHub'dan indirir ve kaydeder."""
    font_path = "DejaVuSans.ttf"
    if not os.path.exists(font_path):
        # GitHub üzerinden açık kaynaklı Türkçe destekli fontu indir
        url = "https://github.com/stefanhesselman/font-dejavu/raw/master/DejaVuSans.ttf"
        try:
            r = requests.get(url)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except:
            return "Helvetica" # Hata olursa varsayılana dön
    
    try:
        pdfmetrics.registerFont(TTFont('GKD_Font', font_path))
        return 'GKD_Font'
    except:
        return 'Helvetica'

FONT_NAME = font_hazirla()

# Matplotlib için Türkçe ve Grafik Ayarları
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False 

DB_FILE = "gkd_akademik_veritabani.csv"

# --- 2. VERİ YÖNETİMİ ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            df.columns = df.columns.str.strip()
            if 'ID' not in df.columns:
                df['ID'] = [f"ID-{uuid.uuid4().hex[:4].upper()}" for _ in range(len(df))]
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

# --- 3. PDF MOTORU ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Türkçe Stil Tanımları
    baslik_stili = ParagraphStyle('B', fontName=FONT_NAME, fontSize=16, alignment=1, spaceAfter=20)
    normal_stil = ParagraphStyle('N', fontName=FONT_NAME, fontSize=10)
    alt_baslik = ParagraphStyle('H', fontName=FONT_NAME, fontSize=12, textColor=colors.navy, spaceBefore=10)

    akis = [Paragraph("BİREYSEL GELİŞİM VE PERFORMANS RAPORU", baslik_stili)]
    
    # Künye Tablosu
    info = [
        [f"Sporcu ID: {secilen.get('ID','')}", f"Grup: {secilen.get('Ceyrek','')}"],
        [f"Ad Soyad: {secilen.get('Ad','')} {secilen.get('Soyad','')}", f"Ölçüm Tarihi: {secilen.get('Olcum_Tarihi','')}"],
        [f"Boy/Kilo: {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", f"Başlama: {secilen.get('Baslama_Tarihi','')}"]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), FONT_NAME)]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    akis.append(Paragraph("Test Sonuçları ve Analiz", alt_baslik))
    tablo_verisi = [["Test Adı", "Skor", "Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        tablo_verisi.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
    ]))
    akis.append(t_analiz)

    # GRAFİKLERİN ÇİZİLMESİ VE PDF'E EKLENMESİ
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.5))
        sporcu_gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(sporcu_gecmis) > 1:
            ax.plot(sporcu_gecmis['Olcum_Tarihi'], sporcu_gecmis[test_adi], marker='o', lw=2, color='#1f77b4')
            ax.set_title(f"{test_adi} Gelişim Grafiği", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran Ort.', 'Sporcu'], [0, z], color=['grey', '#1f77b4'])
            ax.set_xlim(-3.5, 3.5)
            ax.axvline(0, color='black', lw=1)
            ax.set_title(f"{test_adi} Kıyaslama (Z-Skor)", fontsize=10)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100)
        plt.close(fig) # Hafızayı temizle
        
        akis.append(KeepTogether([Spacer(1, 15), Image(img_data, width=400, height=160)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("👤 Sporcu Yönetimi")
    if not db.empty:
        u_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in u_list.iterrows()]
        secim = st.selectbox("Kayıt Seç", options)
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

    st.divider()
    st.subheader("📥 Excel ile Veri Ekle")
    f = st.file_uploader("Dosya Seç", type=['xlsx', 'csv'])
    if f and st.button("Verileri Aktar"):
        ext_df = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
        if 'ID' not in ext_df.columns: ext_df['ID'] = [uuid.uuid4().hex[:6].upper() for _ in range(len(ext_df))]
        veri_kaydet_ve_guncelle(ext_df)
        st.success("Aktarıldı!"); st.rerun()

# --- 5. FORM ---
with st.form("gkd_form"):
    st.subheader("📝 Veri Giriş Ekranı")
    c1, c2, c3 = st.columns(3)
    with c1:
        sid = st.text_input("Sporcu ID", value=secilen_profil['ID'] if secilen_profil is not None else f"GKD-{uuid.uuid4().hex[:6].upper()}")
        ad = st.text_input("Ad", value=secilen_profil['Ad'] if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=secilen_profil['Soyad'] if secilen_profil is not None else "")
    with c2:
        o_tar = st.date_input("Ölçüm Tarihi", value=datetime.now())
        d_tar = st.date_input("Doğum Tarihi", value=datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2012,1,1))
        b_tar = st.date_input("Başlama Tarihi", value=datetime.strptime(str(secilen_profil['Baslama_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2020,1,1))
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 160.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 50.0)

    st.divider()
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", 
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }
    
    vals = {}
    cols = st.columns(2)
    for i, (t_ad, m) in enumerate(test_specs.items()):
        with cols[i % 2]:
            d1 = st.number_input(f"{t_ad} D1", value=float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None else 0.0, format="%.3f")
            d2 = st.number_input(f"{t_ad} D2", value=float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None else 0.0, format="%.3f")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if m == "min" else max(d1, d2)
            vals[t_ad] = {"D1": d1, "D2": d2, "B": best}

    if st.form_submit_button("KAYDET VE RAPORLA"):
        row = {
            "ID": sid, "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo,
            "Ceyrek": f"{d_tar.year}_Q{(d_tar.month-1)//3+1}",
            "Dogum_Tarihi": d_tar.strftime('%Y-%m-%d'), "Olcum_Tarihi": o_tar.strftime('%Y-%m-%d'),
            "Baslama_Tarihi": b_tar.strftime('%Y-%m-%d')
        }
        for t, v in vals.items():
            row[f"{t}_D1"], row[f"{t}_D2"], row[t] = v["D1"], v["D2"], v["B"]
        veri_kaydet_ve_guncelle(pd.DataFrame([row]))
        st.rerun()

# --- 6. ANALİZ ---
if secilen_profil is not None:
    st.divider()
    st.header(f"📊 Analiz: {secilen_profil['Ad']} {secilen_profil['Soyad']}")
    akranlar = db[db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_list = []
    
    for t_ad, m in test_specs.items():
        skor = float(secilen_profil[t_ad])
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        if skor > 0 and not seri.empty:
            ort, std = seri.mean(), (seri.std() if seri.std() > 0 else 0.1)
            z = round(-(skor-ort)/std if m=="min" else (skor-ort)/std, 2)
            dur = "🌟 ELİT" if z >= 2 else ("✅ ÜST" if z >= 1 else ("⚪ ORT" if z > -1 else "🆘 KRİTİK"))
            analiz_list.append({"Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), "Z-Skor": z, "Durum": dur})

    if analiz_list:
        st.table(pd.DataFrame(analiz_list))
        pdf_data = pdf_olustur(secilen_profil, analiz_list, db[db['ID'] == secilen_profil['ID']])
        st.download_button("📄 PDF Raporu İndir", pdf_data, f"Rapor_{secilen_profil['Ad']}.pdf")
