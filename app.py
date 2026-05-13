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

# --- 1. SİSTEM VE FONT YAPILANDIRMASI ---
st.set_page_config(page_title="GKD Performans Sistemi", layout="wide")

@st.cache_resource
def font_hazirla():
    # Dosya adınız tam olarak sistemdeki gibi (Arial.ttf)
    font_yolu = "Arial.ttf"
    if os.path.exists(font_yolu):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Turkce', font_yolu))
            return 'Arial_Turkce'
        except: return 'Helvetica'
    return 'Helvetica'

SECILEN_FONT = font_hazirla()
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

def veri_kaydet(yeni_df):
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

# --- 3. PDF ÜRETME MOTORU (RENKLİ VE TÜRKÇE) ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Stil Tanımları
    baslik_stil = ParagraphStyle('Baslik', fontName=SECILEN_FONT, fontSize=18, alignment=1, spaceAfter=20)
    normal_stil = ParagraphStyle('Normal', fontName=SECILEN_FONT, fontSize=10, leading=12)
    
    akis = [Paragraph("<b>BİREYSEL PERFORMANS VE GELİŞİM RAPORU</b>", baslik_stil)]
    
    # Künye Tablosu
    info = [
        [Paragraph(f"<b>ID:</b> {secilen['ID']}", normal_stil), Paragraph(f"<b>Grup:</b> {secilen['Ceyrek']}", normal_stil)],
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", normal_stil), Paragraph(f"<b>Tarih:</b> {secilen['Olcum_Tarihi']}", normal_stil)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", normal_stil), Paragraph(f"<b>Başlama:</b> {secilen['Baslama_Tarihi']}", normal_stil)]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), SECILEN_FONT), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    tablo_verisi = [[Paragraph(f"<b>{h}</b>", normal_stil) for h in ["Test Adı", "Skor", "Ort.", "Z-Skor", "Durum"]]]
    
    for r in analiz_datalari:
        # İkonları temizle ve metne göre renk belirle
        durum_temiz = str(r['Durum']).replace("🌟", "").replace("✅", "").replace("⚪", "").replace("🆘", "").strip()
        
        # Duruma göre renk seçimi
        durum_rengi = colors.black
        if "ELİT" in durum_temiz: durum_rengi = colors.darkgreen
        elif "ÜST" in durum_temiz: durum_rengi = colors.green
        elif "KRİTİK" in durum_temiz: durum_rengi = colors.red
        
        durum_stili = ParagraphStyle('DStil', fontName=SECILEN_FONT, fontSize=10, textColor=durum_rengi, alignment=1)

        tablo_verisi.append([
            Paragraph(str(r['Test']), normal_stil),
            Paragraph(str(r['Skor']), normal_stil),
            Paragraph(str(r['Grup Ort.']), normal_stil),
            Paragraph(str(r['Z-Skor']), normal_stil),
            Paragraph(f"<b>{durum_temiz}</b>", durum_stili)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    akis.append(t_analiz)

    # Grafikler
    for r in analiz_datalari:
        test_adi = r['Test']
        fig, ax = plt.subplots(figsize=(6, 2.6))
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        
        gecmis_verisi = tum_gecmis.sort_values('Olcum_Tarihi')
        if len(gecmis_verisi) > 1:
            ax.plot(gecmis_verisi['Olcum_Tarihi'], gecmis_verisi[test_adi], marker='o', color='#1f77b4', lw=2)
            ax.set_title(f"{test_adi} Gelişim Grafiği", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            ax.barh(['Akran', 'Sporcu'], [0, z], color=['#cccccc', '#1f77b4'])
            ax.set_title(f"{test_adi} Kıyaslama Analizi", fontsize=10)
            
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=110)
        plt.close(fig)
        akis.append(KeepTogether([Spacer(1, 15), Image(img_buf, width=420, height=170)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. STREAMLIT ARAYÜZÜ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.info(f"Kullanılan Font: {SECILEN_FONT}")
    if not db.empty:
        u_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in u_list.iterrows()]
        secim = st.selectbox("Mevcut Kayıtlar", options)
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

with st.form("ana_form"):
    st.header("📝 Performans Veri Girişi")
    c1, c2, c3 = st.columns(3)
    with c1:
        sid = st.text_input("ID", value=secilen_profil['ID'] if secilen_profil is not None else f"GKD-{uuid.uuid4().hex[:6].upper()}")
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
            val_d1 = st.number_input(f"{t_ad} D1", value=float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None else 0.0, format="%.3f")
            val_d2 = st.number_input(f"{t_ad} D2", value=float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None else 0.0, format="%.3f")
            best = (min(val_d1, val_d2) if val_d1 > 0 and val_d2 > 0 else max(val_d1, val_d2)) if m == "min" else max(val_d1, val_d2)
            vals[t_ad] = {"D1": val_d1, "D2": val_d2, "B": best}

    if st.form_submit_button("✅ VERİLERİ KAYDET VE ANALİZ ET"):
        row_data = {"ID": sid, "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo, "Ceyrek": f"{d_tar.year}_Q{(d_tar.month-1)//3+1}",
                    "Dogum_Tarihi": d_tar.strftime('%Y-%m-%d'), "Olcum_Tarihi": o_tar.strftime('%Y-%m-%d'), "Baslama_Tarihi": b_tar.strftime('%Y-%m-%d')}
        for t, v in vals.items(): row_data[f"{t}_D1"], row_data[f"{t}_D2"], row_data[t] = v["D1"], v["D2"], v["B"]
        veri_kaydet(pd.DataFrame([row_data]))
        st.success("Kayıt Edildi!"); st.rerun()

# Analiz ve PDF İndirme
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
        pdf_file = pdf_olustur(secilen_profil, analiz_list, db[db['ID'] == secilen_profil['ID']])
        st.download_button("📄 PDF RAPORUNU İNDİR", pdf_file, f"Rapor_{sid}.pdf")
