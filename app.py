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
st.set_page_config(page_title="GKD Akademik Performans & Gelişim Takibi", layout="wide")

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
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_yeni_olcum(yeni_df):
    mevcut = veri_oku()
    # Her kayda işlem anındaki tarihi 'Olcum_Tarihi' olarak ekle
    if 'Olcum_Tarihi' not in yeni_df.columns:
        yeni_df['Olcum_Tarihi'] = datetime.now().strftime("%Y-%m-%d")
    
    if mevcut.empty:
        mevcut = yeni_df
    else:
        # Aynı gün, aynı kişiye ait kayıt varsa güncelle, yoksa yeni satır ekle (Gelişim takibi için)
        for _, row in yeni_df.iterrows():
            mask = (mevcut['Ad'] == row['Ad']) & (mevcut['Soyad'] == row['Soyad']) & (mevcut['Olcum_Tarihi'] == row['Olcum_Tarihi'])
            if mask.any():
                idx = mevcut.index[mask][0]
                for col in yeni_df.columns:
                    mevcut.at[idx, col] = row[col]
            else:
                mevcut = pd.concat([mevcut, pd.DataFrame([row])], ignore_index=True)
    
    mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. GELİŞİM ANALİZLİ PDF ÜRETME ---
def profesyonel_pdf_uret(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    b_stili = ParagraphStyle('B', fontName=FONT, fontSize=16, alignment=1, spaceAfter=20)
    a_stili = ParagraphStyle('A', fontName=FONT, fontSize=10, leading=12)
    h_stili = ParagraphStyle('H', fontName=FONT, fontSize=12, spaceBefore=10, textColor=colors.navy)

    akis = [Paragraph("BİREYSEL GELİŞİM VE PERFORMANS RAPORU", b_stili)]
    
    # Künye Bilgileri
    info = [
        [f"Ad Soyad: {secilen['Ad']} {secilen['Soyad']}", f"Grup: {secilen['Ceyrek']}"],
        [f"Boy/Kilo: {secilen['Boy']}cm / {secilen['Kilo']}kg", f"Ölçüm Tarihi: {secilen['Olcum_Tarihi']}"]
    ]
    t = Table(info, colWidths=[250, 250])
    t.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), FONT)]))
    akis.append(t)
    akis.append(Spacer(1, 15))

    # 1. Mevcut Durum Tablosu
    akis.append(Paragraph("Mevcut Ölçüm Analizi", h_stili))
    veriler = [["Test", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        veriler.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t_mevcut = Table(veriler, colWidths=[140, 70, 70, 60, 100])
    t_mevcut.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND',(0,0),(-1,0), colors.whitesmoke), ('FONTNAME', (0,0), (-1,-1), FONT)]))
    akis.append(t_mevcut)

    # 2. Tarihsel Gelişim Tablosu
    if len(tum_gecmis) > 1:
        akis.append(Spacer(1, 15))
        akis.append(Paragraph("Tarihsel Gelişim Özeti", h_stili))
        gecmis_tablo = [["Tarih"] + [r['Test'][:8] for r in analiz_datalari]] # Test isimlerini kısalttık
        
        for _, row in tum_gecmis.sort_values('Olcum_Tarihi').iterrows():
            satir = [row['Olcum_Tarihi']]
            for r in analiz_datalari:
                satir.append(row.get(r['Test'], "-"))
            gecmis_tablo.append(satir)
        
        t_gecmis = Table(gecmis_tablo)
        t_gecmis.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 8)]))
        akis.append(t_gecmis)

    # 3. Görsel Grafikler
    for r in analiz_datalari:
        plt.figure(figsize=(6, 2.5))
        test_adi = r['Test']
        # Gelişim Grafiği (Eğer birden fazla ölçüm varsa)
        sporcu_gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        if len(sporcu_gecmis) > 1:
            plt.plot(sporcu_gecmis['Olcum_Tarihi'], sporcu_gecmis[test_adi], marker='o', color='blue', linewidth=2)
            plt.title(f"{test_adi} - Gelişim Trendi")
            plt.grid(True, linestyle='--', alpha=0.7)
        else:
            z = float(r['Z-Skor'])
            plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, z, 3.0], color=['red', 'gray', 'blue', 'green'])
            plt.xlim(-3.5, 3.5); plt.axvline(0, color='black', lw=1)
            plt.title(f"{test_adi} - Akran Kıyaslaması (Z-Skor)")
        
        img_buf = io.BytesIO(); plt.savefig(img_buf, format='png', bbox_inches='tight'); plt.close()
        akis.append(KeepTogether([Spacer(1,10), Image(img_buf, width=400, height=150)]))

    doc.build(akis); buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("🔍 Sporcu Seçimi")
    if not db.empty:
        # Sporcuları tekilleştir (Sadece ad-soyad listesi için)
        sporcu_listesi = db.groupby(['Ad', 'Soyad']).size().index.tolist()
        isimler = [f"{s[0]} {s[1]}" for s in sporcu_listesi]
        arama = st.selectbox("Kayıtlı Sporcu Düzenle", ["-- Yeni Kayıt --"] + isimler)
        
        if arama != "-- Yeni Kayıt --":
            ad_s, soyad_s = arama.split(" ", 1)
            gecmis_veriler = db[(db['Ad'] == ad_s) & (db['Soyad'] == soyad_s)].sort_values('Olcum_Tarihi', ascending=False)
            # Düzenlemek için en son ölçümü baz al
            secilen_profil = gecmis_veriler.iloc[0]
            st.info(f"Son ölçüm: {secilen_profil['Olcum_Tarihi']}")

    st.divider()
    st.subheader("📊 Araştırmacı Portalı")
    if not db.empty:
        towrite = io.BytesIO()
        db.sort_values(['Ad', 'Olcum_Tarihi']).to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("Excel: Tüm Zamanların Verisi", towrite.getvalue(), "akademik_gelisim_db.xlsx")

# --- 5. VERİ GİRİŞ FORMU ---
with st.form("olcum_formu"):
    st.subheader("📝 Yeni Ölçüm Girişi / Bilgi Güncelleme")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        olcum_tarihi = st.date_input("Ölçüm Tarihi", value=datetime.now())
        v_dt_str = str(secilen_profil['Dogum_Tarihi']) if secilen_profil is not None else "2012-01-01"
        dogum = st.date_input("Doğum Tarihi", value=datetime.strptime(v_dt_str, '%Y-%m-%d'))
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

    if st.form_submit_button("ÖLÇÜMÜ KAYDET VE VERİTABANINA İŞLE"):
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            p = {"Ad": ad.strip(), "Soyad": soyad.strip(), "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), 
                 "Olcum_Tarihi": olcum_tarihi.strftime('%Y-%m-%d'), "Boy": boy, "Kilo": kilo, "Ceyrek": q}
            for t, v in yeni_veriler.items():
                p[f"{t}_D1"], p[f"{t}_D2"], p[t] = v["D1"], v["D2"], v["B"]
            
            veri_kaydet_yeni_olcum(pd.DataFrame([p]))
            st.success(f"{ad} {soyad} için {olcum_tarihi} tarihli ölçüm başarıyla eklendi!")
            st.rerun()

# --- 6. ANALİZ VE GELİŞİM RAPORU ---
if secilen_profil is not None:
    st.divider()
    st.subheader(f"📊 {secilen_profil['Ad']} {secilen_profil['Soyad']} - Analiz Paneli")
    
    # Akran Grubu (Aynı Çeyrek) Ortalamaları
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
        st.dataframe(pd.DataFrame(analiz_datalari), use_container_width=True)
        
        # Bu sporcunun tüm zamanlardaki verisi
        sporcu_gecmis = db[(db['Ad'] == secilen_profil['Ad']) & (db['Soyad'] == secilen_profil['Soyad'])]
        
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari, sporcu_gecmis)
        st.download_button("📄 Gelişim Raporunu (PDF) İndir", pdf, f"Gelisim_Raporu_{secilen_profil['Ad']}_{secilen_profil['Soyad']}.pdf")
