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

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(page_title="GKD Akademik Performans Sistemi", layout="wide")

def font_yukle():
    """Türkçe karakterler için font yapılandırması."""
    # Yaygın font yollarını dene
    font_paths = ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Global_Font', path))
                return 'Global_Font'
            except: continue
    return 'Helvetica'

FONT = font_yukle()
DB_FILE = "gkd_akademik_veritabani.csv"

# --- 2. VERİ YÖNETİMİ (GÜÇLENDİRİLMİŞ) ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-16')
            except:
                df = pd.read_csv(DB_FILE, encoding='utf-8')
            
            if not df.empty:
                df.columns = df.columns.str.strip()
                # KRİTİK: Eğer eski dosyada ID yoksa otomatik ekle
                if 'ID' not in df.columns:
                    df['ID'] = [f"ESKI-{uuid.uuid4().hex[:4].upper()}" for _ in range(len(df))]
                if 'Olcum_Tarihi' not in df.columns:
                    df['Olcum_Tarihi'] = datetime.now().strftime("%Y-%m-%d")
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_guncelle(yeni_df):
    mevcut = veri_oku()
    yeni_df.columns = yeni_df.columns.str.strip()
    
    if mevcut.empty:
        mevcut = yeni_df
    else:
        for _, row in yeni_df.iterrows():
            # ID ve Ölçüm Tarihi bazlı eşleşme kontrolü
            mask = (mevcut['ID'].astype(str) == str(row['ID'])) & \
                   (mevcut['Olcum_Tarihi'].astype(str) == str(row['Olcum_Tarihi']))
            
            if mask.any():
                idx = mevcut.index[mask][0]
                for col in yeni_df.columns:
                    mevcut.at[idx, col] = row[col]
            else:
                mevcut = pd.concat([mevcut, pd.DataFrame([row])], ignore_index=True)
    
    mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')

# --- 3. PDF ÜRETME MOTORU ---
def profesyonel_pdf_uret(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Türkçe Karakter Destekli Stiller
    title_style = ParagraphStyle('T', fontName=FONT, fontSize=18, alignment=1, spaceAfter=20)
    head_style = ParagraphStyle('H', fontName=FONT, fontSize=12, spaceBefore=10, textColor=colors.navy)
    
    akis = [Paragraph("BİREYSEL PERFORMANS VE GELİŞİM RAPORU", title_style)]
    
    # Künye
    info_data = [
        [f"ID: {secilen.get('ID','')}", f"Grup: {secilen.get('Ceyrek','')}"],
        [f"Ad Soyad: {secilen.get('Ad','')} {secilen.get('Soyad','')}", f"Ölçüm Tarihi: {secilen.get('Olcum_Tarihi','')}"],
        [f"Boy: {secilen.get('Boy','')} cm", f"Kilo: {secilen.get('Kilo','')} kg"]
    ]
    t_info = Table(info_data, colWidths=[250, 250])
    t_info.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), FONT)]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # Tablo
    table_data = [["Test Adı", "Skor", "Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        table_data.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t = Table(table_data, colWidths=[160, 60, 70, 60, 100])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), FONT),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)
    ]))
    akis.append(t)
    
    # Grafiklerin Eklenmesi
    for r in analiz_datalari:
        test_adi = r['Test']
        plt.figure(figsize=(6, 3))
        gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(gecmis) > 1:
            plt.plot(gecmis['Olcum_Tarihi'], gecmis[test_adi], marker='o', color='blue', lw=2)
            plt.title(f"{test_adi} Gelişim Trendi", fontsize=10)
        else:
            z = float(r['Z-Skor'])
            plt.barh(['Akran', 'Sporcu'], [0, z], color=['grey', 'blue'])
            plt.xlim(-3.5, 3.5); plt.axvline(0, color='black')
            plt.title(f"{test_adi} Kıyaslama", fontsize=10)
            
        plt.grid(True, alpha=0.3); plt.tight_layout()
        img_buf = io.BytesIO(); plt.savefig(img_buf, format='png'); plt.close()
        akis.append(KeepTogether([Spacer(1,15), Image(img_buf, width=400, height=160)]))

    doc.build(akis); buf.seek(0)
    return buf

# --- 4. ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("⚙️ Yönetim")
    if not db.empty and 'ID' in db.columns:
        # İsim ve ID ile seçim listesi oluştur
        unique_list = db.sort_values('Olcum_Tarihi', ascending=False).drop_duplicates('ID')
        options = ["-- Yeni Kayıt --"] + [f"{r['Ad']} {r['Soyad']} ({r['ID']})" for _, r in unique_list.iterrows()]
        secim = st.selectbox("Sporcu Seç", options)
        
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]

    st.divider()
    # Excel Yükleme Şablonu Uyarısı
    st.subheader("📥 Excel/CSV Yükle")
    file = st.file_uploader("Dosya seç", type=['xlsx', 'csv'])
    if file and st.button("Yükle"):
        df_new = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)
        if 'ID' not in df_new.columns:
            df_new['ID'] = [f"GKD-{uuid.uuid4().hex[:6].upper()}" for _ in range(len(df_new))]
        veri_kaydet_ve_guncelle(df_new)
        st.success("Yüklendi!"); st.rerun()

# --- 5. FORM ---
with st.form("kayit_formu"):
    st.subheader("📝 Ölçüm Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        # ID alanı
        curr_id = st.text_input("ID", value=secilen_profil['ID'] if secilen_profil is not None else f"GKD-{uuid.uuid4().hex[:6].upper()}")
        ad = st.text_input("Ad", value=secilen_profil['Ad'] if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=secilen_profil['Soyad'] if secilen_profil is not None else "")
    with c2:
        olcum_tarihi = st.date_input("Ölçüm Tarihi", value=datetime.now())
        v_dt = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2012, 1, 1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
        v_bas = datetime.strptime(str(secilen_profil['Baslama_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2020, 1, 1)
        baslama = st.date_input("Başlama Tarihi", value=v_bas)
    with c3:
        boy = st.number_input("Boy", value=float(secilen_profil['Boy']) if secilen_profil is not None else 160.0)
        kilo = st.number_input("Kilo", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 50.0)

    st.divider()
    test_specs = {"5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min"}
    
    test_sonuclari = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v1, format="%.3f")
            d2 = st.number_input(f"{t_ad} D2", value=v2, format="%.3f")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            test_sonuclari[t_ad] = {"D1": d1, "D2": d2, "B": best}

    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
        row_dict = {
            "ID": curr_id, "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo, "Ceyrek": q,
            "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), 
            "Olcum_Tarihi": olcum_tarihi.strftime('%Y-%m-%d'),
            "Baslama_Tarihi": baslama.strftime('%Y-%m-%d')
        }
        for t_ad, vals in test_sonuclari.items():
            row_dict[f"{t_ad}_D1"], row_dict[f"{t_ad}_D2"], row_dict[t_ad] = vals["D1"], vals["D2"], vals["B"]
        
        veri_kaydet_ve_guncelle(pd.DataFrame([row_dict]))
        st.success("Veritabanı güncellendi!"); st.rerun()

# --- 6. ANALİZ PANELİ ---
if secilen_profil is not None:
    st.divider()
    st.header(f"📊 Analiz: {secilen_profil['Ad']} {secilen_profil['Soyad']}")
    
    akranlar = db[db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    
    for t_ad, mod in test_specs.items():
        skor = float(secilen_profil[t_ad])
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        if skor > 0 and len(seri) > 0:
            ort = seri.mean()
            std = seri.std() if len(seri) > 1 else 0.1
            z_f = round(-(skor-ort)/std if mod=="min" else (skor-ort)/std, 2)
            durum = "🌟 ELİT" if z_f >= 2 else ("✅ ÜST" if z_f >= 1 else ("⚪ ORT" if z_f > -1 else "🆘 KRİTİK"))
            analiz_datalari.append({"Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": durum})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari, db[db['ID'] == secilen_profil['ID']])
        st.download_button("📄 PDF Raporu İndir", pdf, f"Rapor_{secilen_profil['ID']}.pdf")
