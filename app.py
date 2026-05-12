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
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-16')
            except:
                df = pd.read_csv(DB_FILE, encoding='utf-8')
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    yeni_df.columns = yeni_df.columns.str.strip()
    
    if mevcut.empty or 'Ad' not in mevcut.columns:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    for _, row in yeni_df.iterrows():
        ad, soyad = str(row.get('Ad', '')), str(row.get('Soyad', ''))
        if ad != "" and soyad != "":
            mask = (mevcut['Ad'].astype(str) == ad) & (mevcut['Soyad'].astype(str) == soyad)
            if mask.any():
                idx = mevcut.index[mask][0]
                for col in yeni_df.columns:
                    if pd.notnull(row[col]) and row[col] != "":
                        if col in mevcut.columns and mevcut[col].dtype != yeni_df[col].dtype:
                            mevcut[col] = mevcut[col].astype(object)
                        mevcut.loc[idx, col] = row[col]
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
    b_stili = ParagraphStyle('B', fontName=FONT, fontSize=16, alignment=1, spaceAfter=20)
    a_stili = ParagraphStyle('A', fontName=FONT, fontSize=11, leading=14)
    t_stili = ParagraphStyle('T', fontName=FONT, fontSize=9, alignment=1)

    akis = [Paragraph("BİREYSEL PERFORMANS ANALİZ RAPORU", b_stili)]
    info = [
        [Paragraph(f"<b>Ad Soyad:</b> {secilen.get('Ad','')} {secilen.get('Soyad','')}", a_stili), Paragraph(f"<b>Grup:</b> {secilen.get('Ceyrek','')}", a_stili)],
        [Paragraph(f"<b>Doğum:</b> {secilen.get('Dogum_Tarihi','')}", a_stili), Paragraph(f"<b>Başlama Tarihi:</b> {secilen.get('Baslama_Tarihi','')}", a_stili)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", a_stili), ""]
    ]
    akis.append(Table(info, colWidths=[250, 250]))
    akis.append(Spacer(1, 15))

    veriler = [[Paragraph(f"<b>{h}</b>", t_stili) for h in ["Test", "Skor", "Ort.", "Z-Skor", "Durum"]]]
    for r in analiz_datalari:
        veriler.append([Paragraph(str(r[k]), t_stili) for k in ['Test', 'Skor', 'Grup Ort.', 'Z-Skor', 'Durum']])
    
    tablo = Table(veriler, colWidths=[130, 60, 70, 60, 100])
    tablo.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND',(0,0),(-1,0), colors.whitesmoke)]))
    akis.append(tablo)

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2))
        z = float(r['Z-Skor'])
        plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, z, 3.0], color=['red', 'gray', 'blue', 'green'])
        plt.xlim(-3.5, 3.5); plt.axvline(0, color='black', lw=1); plt.tight_layout()
        img_buf = io.BytesIO(); plt.savefig(img_buf, format='png'); plt.close()
        akis.append(KeepTogether([Paragraph(f"<br/><br/>• {r['Test']}", a_stili), Image(img_buf, width=350, height=120)]))

    doc.build(akis); buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("🔍 Sporcu Yönetimi")
    if not db.empty and 'Ad' in db.columns:
        isimler = (db['Ad'].astype(str) + " " + db['Soyad'].astype(str)).tolist()
        arama = st.selectbox("Kayıtlı Öğrenciler", ["-- Yeni Kayıt --"] + isimler)
        if arama != "-- Yeni Kayıt --":
            secilen_profil = db.iloc[isimler.index(arama)]
    
    st.divider()
    st.subheader("📈 Araştırmacı Menüsü")
    if not db.empty:
        try:
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                db.to_excel(writer, index=False, sheet_name='Performans Verileri')
            st.download_button("📊 Tüm Verileri Excel İndir", towrite.getvalue(), f"gkd_veriseti_{datetime.now().strftime('%Y%m%d')}.xlsx")
        except Exception as e: st.error(f"Excel hatası: {e}")

    st.divider()
    st.subheader("📥 Veri Yükleme")
    yuklenen = st.file_uploader("Dosya Seç", type=['xlsx', 'csv'])
    if yuklenen and st.button("Havuza Aktar"):
        df_yeni = pd.read_excel(yuklenen) if yuklenen.name.endswith('xlsx') else pd.read_csv(yuklenen)
        df_yeni.columns = df_yeni.columns.str.strip()
        veri_kaydet_ve_merge(df_yeni)
        st.success("Aktarıldı!"); st.rerun()

# --- 5. VERİ GİRİŞ FORMU ---
with st.form("ana_veri_formu"):
    st.subheader("👤 Sporcu Bilgileri")
    c1, c2, c3 = st.columns(3)
    
    # AttributeError engellemek için kontroller
    with c1:
        ad_init = str(secilen_profil['Ad']) if secilen_profil is not None else ""
        soyad_init = str(secilen_profil['Soyad']) if secilen_profil is not None else ""
        ad = st.text_input("Ad", value=ad_init)
        soyad = st.text_input("Soyad", value=soyad_init)
    with c2:
        v_dt_str = str(secilen_profil['Dogum_Tarihi']) if secilen_profil is not None else "2012-01-01"
        try:
            v_dt = datetime.strptime(v_dt_str, '%Y-%m-%d')
        except:
            v_dt = datetime(2012, 1, 1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
        
        # Başlama Tarihi Kontrolü
        v_bas_str = str(secilen_profil.get('Baslama_Tarihi', 'nan')) if secilen_profil is not None else 'nan'
        try:
            v_bas = datetime.strptime(v_bas_str, '%Y-%m-%d')
        except:
            v_bas = datetime.now()
        baslama = st.date_input("Antrenmana Başlama Tarihi", value=v_bas)
        
    with c3:
        boy_init = float(secilen_profil['Boy']) if secilen_profil is not None else 150.0
        kilo_init = float(secilen_profil['Kilo']) if secilen_profil is not None else 40.0
        boy = st.number_input("Boy (cm)", value=boy_init)
        kilo = st.number_input("Kilo (kg)", value=kilo_init)

    st.divider()
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", 
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }
    
    yeni_veriler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v1, format="%.3f", key=f"{t_ad}1")
            d2 = st.number_input(f"{t_ad} D2", value=v2, format="%.3f", key=f"{t_ad}2")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "B": best}

    # FORM BUTONU (Formun içinde kalmalı)
    submit = st.form_submit_button("KAYDET VE ANALİZ ET")
    if submit:
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            p = {
                "Ad": ad, "Soyad": soyad, 
                "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), 
                "Baslama_Tarihi": baslama.strftime('%Y-%m-%d'), 
                "Boy": boy, "Kilo": kilo, "Ceyrek": q
            }
            for t, v in yeni_veriler.items():
                p[f"{t}_D1"], p[f"{t}_D2"], p[t] = v["D1"], v["D2"], v["B"]
            veri_kaydet_ve_merge(pd.DataFrame([p]))
            st.success("Kaydedildi!"); st.rerun()
        else:
            st.error("Ad ve Soyad girmek zorunludur!")

# --- 6. ANALİZ VE PDF ---
if secilen_profil is not None:
    st.divider()
    akranlar = db[db['Ceyrek'] == secilen_profil['Ceyrek']] if not db.empty else pd.DataFrame()
    analiz_datalari = []
    for t_ad, mod in test_specs.items():
        if t_ad in secilen_profil:
            skor = float(secilen_profil[t_ad])
            seri = akranlar[t_ad].replace(0, np.nan).dropna() if not akranlar.empty else pd.Series()
            if skor > 0 and len(seri) > 1:
                ort, std = seri.mean(), seri.std()
                z_f = round(-(skor-ort)/std if mod=="min" else (skor-ort)/std, 2)
                z_f = max(min(z_f, 3.0), -3.0)
                d = "🌟 ELİT" if z_f >= 2 else ("✅ ÜST" if z_f >= 1 else ("⚪ ORT" if z_f > -1 else "🆘 KRİTİK"))
                analiz_datalari.append({"Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": d})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button("📄 PDF İndir", pdf, f"{secilen_profil['Ad']}_{secilen_profil['Soyad']}.pdf")                    if pd.notnull(row[col]) and row[col] != "":
                        if col in mevcut.columns and mevcut[col].dtype != yeni_df[col].dtype:
                            mevcut[col] = mevcut[col].astype(object)
                        mevcut.loc[idx, col] = row[col]
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
    b_stili = ParagraphStyle('B', fontName=FONT, fontSize=16, alignment=1, spaceAfter=20)
    a_stili = ParagraphStyle('A', fontName=FONT, fontSize=11, leading=14)
    t_stili = ParagraphStyle('T', fontName=FONT, fontSize=9, alignment=1)

    akis = [Paragraph("BİREYSEL PERFORMANS ANALİZ RAPORU", b_stili)]
    info = [
        [Paragraph(f"<b>Ad Soyad:</b> {secilen.get('Ad','')} {secilen.get('Soyad','')}", a_stili), Paragraph(f"<b>Grup:</b> {secilen.get('Ceyrek','')}", a_stili)],
        [Paragraph(f"<b>Doğum:</b> {secilen.get('Dogum_Tarihi','')}", a_stili), Paragraph(f"<b>Başlama Tarihi:</b> {secilen.get('Baslama_Tarihi','')}", a_stili)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", a_stili), ""]
    ]
    akis.append(Table(info, colWidths=[250, 250]))
    akis.append(Spacer(1, 15))

    veriler = [[Paragraph(f"<b>{h}</b>", t_stili) for h in ["Test", "Skor", "Ort.", "Z-Skor", "Durum"]]]
    for r in analiz_datalari:
        veriler.append([Paragraph(str(r[k]), t_stili) for k in ['Test', 'Skor', 'Grup Ort.', 'Z-Skor', 'Durum']])
    
    tablo = Table(veriler, colWidths=[130, 60, 70, 60, 100])
    tablo.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND',(0,0),(-1,0), colors.whitesmoke)]))
    akis.append(tablo)

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2))
        z = float(r['Z-Skor'])
        plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, z, 3.0], color=['red', 'gray', 'blue', 'green'])
        plt.xlim(-3.5, 3.5); plt.axvline(0, color='black', lw=1); plt.tight_layout()
        img_buf = io.BytesIO(); plt.savefig(img_buf, format='png'); plt.close()
        akis.append(KeepTogether([Paragraph(f"<br/><br/>• {r['Test']}", a_stili), Image(img_buf, width=350, height=120)]))

    doc.build(akis); buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ VE ARAŞTIRMACI MENÜSÜ ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("🔍 Sporcu Yönetimi")
    if not db.empty and 'Ad' in db.columns:
        isimler = (db['Ad'].astype(str) + " " + db['Soyad'].astype(str)).tolist()
        arama = st.selectbox("Kayıtlı Öğrenciler", ["-- Yeni Kayıt --"] + isimler)
        if arama != "-- Yeni Kayıt --":
            secilen_profil = db.iloc[isimler.index(arama)]
    
    st.divider()
    st.subheader("📈 Araştırmacı Menüsü")
    if not db.empty:
        try:
            # ÇIKTIDA AD VE SOYAD ARTIK VERİLİYOR
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                db.to_excel(writer, index=False, sheet_name='Performans Verileri')
            st.download_button("📊 Tüm Verileri Excel İndir", towrite.getvalue(), f"gkd_tam_veriseti_{datetime.now().strftime('%Y%m%d')}.xlsx")
        except Exception as e: st.error(f"Excel hatası: {e}")

    st.divider()
    st.subheader("📥 Veri Yükleme")
    yuklenen = st.file_uploader("Dosya Seç", type=['xlsx', 'csv'])
    if yuklenen and st.button("Havuza Aktar"):
        df_yeni = pd.read_excel(yuklenen) if yuklenen.name.endswith('xlsx') else pd.read_csv(yuklenen)
        df_yeni.columns = df_yeni.columns.str.strip()
        veri_kaydet_ve_merge(df_yeni)
        st.success("Aktarıldı!"); st.rerun()

# --- 5. VERİ GİRİŞ FORMU ---
with st.form("ana_veri_formu"):
    st.subheader("👤 Sporcu Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad_val = str(secilen_profil['Ad']) if secilen_profil is not None else ""
        soyad_val = str(secilen_profil['Soyad']) if secilen_profil is not None else ""
        ad = st.text_input("Ad", value=ad_val)
        soyad = st.text_input("Soyad", value=soyad_val)
    with c2:
        v_dt_str = str(secilen_profil['Dogum_Tarihi']) if secilen_profil is not None else "2012-01-01"
        v_dt = datetime.strptime(v_dt_str, '%Y-%m-%d') if v_dt_str != 'nan' else datetime(2012,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
        v_bas_str = str(secilen_profil.get('Baslama_Tarihi', 'nan'))
        v_bas = datetime.strptime(v_bas_str, '%Y-%m-%d') if v_bas_str != 'nan' else datetime.now()
        baslama = st.date_input("Antrenmana Başlama Tarihi", value=v_bas)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 150.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 40.0)

    st.divider()
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", 
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }
    
    yeni_veriler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v1, format="%.3f", key=f"{t_ad}1")
            d2 = st.number_input(f"{t_ad} D2", value=v2, format="%.3f", key=f"{t_ad}2")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "B": best}

    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            p = {"Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), "Baslama_Tarihi": baslama.strftime('%Y-%m-%d'), "Boy": boy, "Kilo": kilo, "Ceyrek": q}
            for t, v in yeni_veriler.items():
                p[f"{t}_D1"], p[f"{t}_D2"], p[t] = v["D1"], v["D2"], v["B"]
            veri_kaydet_ve_merge(pd.DataFrame([p]))
            st.success("Kaydedildi!"); st.rerun()

# --- 6. ANALİZ VE PDF ---
if secilen_profil is not None:
    st.divider()
    akranlar = db[db['Ceyrek'] == secilen_profil['Ceyrek']] if not db.empty else pd.DataFrame()
    analiz_datalari = []
    for t_ad, mod in test_specs.items():
        if t_ad in secilen_profil:
            skor = float(secilen_profil[t_ad])
            seri = akranlar[t_ad].replace(0, np.nan).dropna() if not akranlar.empty else pd.Series()
            if skor > 0 and len(seri) > 1:
                ort, std = seri.mean(), seri.std()
                z_f = round(-(skor-ort)/std if mod=="min" else (skor-ort)/std, 2)
                z_f = max(min(z_f, 3.0), -3.0)
                d = "🌟 ELİT" if z_f >= 2 else ("✅ ÜST" if z_f >= 1 else ("⚪ ORT" if z_f > -1 else "🆘 KRİTİK"))
                analiz_datalari.append({"Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": d})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button("📄 PDF İndir", pdf, f"{ad}_{soyad}.pdf")
