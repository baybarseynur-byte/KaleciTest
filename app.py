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
            # UTF-16 ve UTF-8 denemeleri
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-16')
            except:
                df = pd.read_csv(DB_FILE, encoding='utf-8')
            
            df.columns = df.columns.str.strip()
            return df
        except: 
            return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    yeni_df.columns = yeni_df.columns.str.strip()
    
    # Mevcut veritabanı boşsa veya hatalıysa yeni tabloyu oluştur
    if mevcut.empty or 'Ad' not in mevcut.columns:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    for _, row in yeni_df.iterrows():
        ad, soyad = str(row.get('Ad', '')), str(row.get('Soyad', ''))
        if ad == "" or soyad == "": continue
        
        mask = (mevcut['Ad'].astype(str) == ad) & (mevcut['Soyad'].astype(str) == soyad)
        
        if mask.any():
            idx = mevcut.index[mask][0]
            for col in yeni_df.columns:
                val = row[col]
                if pd.notnull(val) and val != "":
                    if col in mevcut.columns and mevcut[col].dtype != yeni_df[col].dtype:
                        mevcut[col] = mevcut[col].astype(object)
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
    
    # Bilgi Tablosu
    info_data = [
        [Paragraph(f"<b>Ad Soyad:</b> {secilen.get('Ad','')} {secilen.get('Soyad','')}", alt_baslik_stili), 
         Paragraph(f"<b>Grup/Çeyrek:</b> {secilen.get('Ceyrek','')}", alt_baslik_stili)],
        [Paragraph(f"<b>Doğum Tarihi:</b> {secilen.get('Dogum_Tarihi','')}", alt_baslik_stili),
         Paragraph(f"<b>Başlama Tarihi:</b> {secilen.get('Baslama_Tarihi','')}", alt_baslik_stili)], # Burası eklendi
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", alt_baslik_stili), ""]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    akis.append(info_table)
    akis.append(Spacer(1, 15))

    # Analiz Tablosu
    tablo_verisi = [[Paragraph(f"<b>{h}</b>", tablo_icerik_stili) for h in ["Test Adı", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]]
    for r in analiz_datalari:
        tablo_verisi.append([Paragraph(str(r[k]), tablo_icerik_stili) for k in ['Test', 'Skor', 'Grup Ort.', 'Z-Skor', 'Durum']])
    
    ozet_tablo = Table(tablo_verisi, colWidths=[130, 60, 70, 60, 100])
    ozet_tablo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)]))
    akis.append(ozet_tablo)

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2.2))
        z_val = float(r['Z-Skor'])
        renk = '#81c784' if z_val >= 1 else ('#ff8a80' if z_val <= -1 else '#cfd8dc')
        plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, z_val, 3.0], color=['#ff8a80', 'gray', renk, '#81c784'])
        plt.xlim(-3.5, 3.5)
        plt.axvline(0, color='black', linewidth=0.8, linestyle='--')
        plt.tight_layout()
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
    st.header("🔍 Sporcu Yönetimi")
    if not db.empty and 'Ad' in db.columns:
        isimler = (db['Ad'].astype(str) + " " + db['Soyad'].astype(str)).tolist()
        arama = st.selectbox("Kayıtlı Öğrenciler", ["-- Yeni Kayıt --"] + isimler)
        if arama != "-- Yeni Kayıt --":
            secilen_profil = db.iloc[isimler.index(arama)]
    
    st.divider()
    st.subheader("📥 Veri Yükleme")
    yuklenen = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
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
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        v_dt = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2012,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
        # Antrenmana Başlama Tarihi Form Alanı
        v_bas = datetime.strptime(str(secilen_profil['Baslama_Tarihi']), '%Y-%m-%d') if secilen_profil is not None and str(secilen_profil['Baslama_Tarihi']) != 'nan' else datetime.now()
        baslama = st.date_input("Antrenmana Başlama Tarihi", value=v_bas)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 150.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 40.0)

    st.divider()
    test_specs = {
        "5m Sprint (sn)": {"mod": "min"}, "10m Sprint (sn)": {"mod": "min"}, 
        "20m Sprint (sn)": {"mod": "min"}, "Dikey Sıçrama (cm)": {"mod": "max"},
        "SKT Sağ (sn)": {"mod": "min"}, "SKT Sol (sn)": {"mod": "min"},
        "LSKT Sağ (sn)": {"mod": "min"}, "LSKT Sol (sn)": {"mod": "min"}
    }
    
    yeni_veriler = {}
    cols = st.columns(2)
    for i, (t_ad, conf) in enumerate(test_specs.items()):
        with cols[i % 2]:
            v_d1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v_d2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} D1", value=v_d1, format="%.3f", key=f"{t_ad}_1")
            d2 = st.number_input(f"{t_ad} D2", value=v_d2, format="%.3f", key=f"{t_ad}_2")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if conf["mod"] == "min" else max(d1, d2)
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            # Packet içine Baslama_Tarihi eklendi
            packet = {
                "Ad": ad, "Soyad": soyad, 
                "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), 
                "Baslama_Tarihi": baslama.strftime('%Y-%m-%d'), # Eksik olan buydu
                "Boy": boy, "Kilo": kilo, "Ceyrek": q
            }
            for t, v in yeni_veriler.items():
                packet[f"{t}_D1"] = v["D1"]; packet[f"{t}_D2"] = v["D2"]; packet[t] = v["Best"]
            
            veri_kaydet_ve_merge(pd.DataFrame([packet]))
            st.success("Veriler kaydedildi!"); st.rerun()

# --- 6. ANALİZ VE PDF BUTONU ---
if secilen_profil is not None:
    st.divider()
    f_db = veri_oku()
    akranlar = f_db[f_db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    
    for t_ad, conf in test_specs.items():
        if t_ad in secilen_profil:
            skor = float(secilen_profil[t_ad])
            seri = akranlar[t_ad].replace(0, np.nan).dropna()
            if skor > 0 and len(seri) > 1:
                ort, std = seri.mean(), seri.std()
                z = (skor - ort) / std if std > 0 else 0
                z_f = round(-z if conf["mod"] == "min" else z, 2)
                z_f = max(min(z_f, 3.0), -3.0)
                d = "🌟 ELİT" if z_f >= 2 else ("✅ ÜST" if z_f >= 1 else ("⚪ ORT" if z_f > -1 else "🆘 GELİŞTİRİLMELİ"))
                analiz_datalari.append({"Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": d})

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        pdf = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button("📄 PDF İndir", pdf, f"{ad}_{soyad}.pdf")            return pd.read_csv(DB_FILE, encoding='utf-16')
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
        tablo_verisi.append([
            Paragraph(str(r['Test']), tablo_icerik_stili),
            Paragraph(str(r['Skor']), tablo_icerik_stili),
            Paragraph(str(r['Grup Ort.']), tablo_icerik_stili),
            Paragraph(str(r['Z-Skor']), tablo_icerik_stili),
            Paragraph(str(r['Durum']), tablo_icerik_stili)
        ])
    
    ozet_tablo = Table(tablo_verisi, colWidths=[130, 60, 70, 60, 70])
    ozet_tablo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    akis.append(ozet_tablo)
    akis.append(Spacer(1, 20))

    for r in analiz_datalari:
        plt.figure(figsize=(6, 2.5))
        plt.barh(['Kritik (-3)', 'Ortalama (0)', 'Sporcu', 'Elit (+3)'], 
                 [-3.0, 0.0, float(r['Z-Skor']), 3.0], 
                 color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
        plt.xlim(-3.5, 3.5)
        plt.axvline(0, color='black', linewidth=0.8, linestyle='--')
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
            std = seri.std() if len(seri) > 1 else 0
            
            # Z-Skor Hesaplama ve Yönsel Düzeltme
            z_ham = (skor - ort) / std if std > 0 else 0
            z_final = round(-z_ham if mod == "min" else z_ham, 2)
            z_final = max(min(z_final, 3.0), -3.0) # +3 / -3 Sınırlandırması
            
            # Akademik Durum Belirleme
            if z_final >= 2.0: durum = "🌟 ELİT (+2/+3)"
            elif z_final >= 1.0: durum = "✅ ÜST DÜZEY (+1/+2)"
            elif z_final > -1.0: durum = "⚪ ORTALAMA (-1/+1)"
            elif z_final > -2.0: durum = "⚠️ GELİŞTİRİLMELI (-1/-2)"
            else: durum = "🆘 KRİTİK (-2/-3)"
            
            analiz_datalari.append({
                "Test": t_ad, "Skor": skor, "Grup Ort.": round(ort,2), 
                "Z-Skor": z_final, "Durum": durum
            })

    if analiz_datalari:
        st.subheader("📊 Akademik Performans Özeti (+3 / -3 Skalası)")
        st.table(pd.DataFrame(analiz_datalari))
        pdf_dosyasi = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button(label="📄 Yorumlu PDF İndir", data=pdf_dosyasi, file_name=f"{ad}_{soyad}_Analiz.pdf", key="pdf_down")
        try:
            # Önce utf-16 deniyoruz, olmazsa utf-8
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-16')
            except:
                df = pd.read_csv(DB_FILE, encoding='utf-8')
            
            df.columns = df.columns.str.strip() # Sütun isimlerindeki boşlukları temizle
            return df
        except: 
            return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    yeni_df.columns = yeni_df.columns.str.strip()
    
    if mevcut.empty:
        if 'Son_Guncelleme' not in yeni_df.columns:
            yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    # Ad ve Soyad üzerinden sporcuyu bul ve güncelle veya yeni ekle
    for _, row in yeni_df.iterrows():
        ad, soyad = str(row.get('Ad', '')), str(row.get('Soyad', ''))
        if ad == "" or soyad == "": continue # Geçersiz satırları atla
        
        mask = (mevcut['Ad'].astype(str) == ad) & (mevcut['Soyad'].astype(str) == soyad)
        
        if mask.any():
            idx = mevcut.index[mask][0]
            for col in yeni_df.columns:
                val = row[col]
                if pd.notnull(val) and val != "":
                    # Tip uyuşmazlığına karşı nesne tipine dönüştür
                    if col in mevcut.columns and mevcut[col].dtype != yeni_df[col].dtype:
                        mevcut[col] = mevcut[col].astype(object)
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
        [Paragraph(f"<b>Ad Soyad:</b> {secilen.get('Ad','')} {secilen.get('Soyad','')}", alt_baslik_stili), 
         Paragraph(f"<b>Grup/Çeyrek:</b> {secilen.get('Ceyrek','')}", alt_baslik_stili)],
        [Paragraph(f"<b>Doğum Tarihi:</b> {secilen.get('Dogum_Tarihi','')}", alt_baslik_stili),
         Paragraph(f"<b>Boy/Kilo:</b> {secilen.get('Boy','')}cm / {secilen.get('Kilo','')}kg", alt_baslik_stili)],
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
        # Z-skoru renkleri: Elit yeşil, Kritik kırmızı
        z_val = float(r['Z-Skor'])
        renk = '#81c784' if z_val >= 1 else ('#ff8a80' if z_val <= -1 else '#cfd8dc')
        
        plt.barh(['Kritik', 'Ortalama', 'Sporcu', 'Elit'], [-3.0, 0.0, z_val, 3.0], color=['#ff8a80', 'gray', renk, '#81c784'])
        plt.xlim(-3.5, 3.5)
        plt.axvline(0, color='black', linewidth=0.8, linestyle='--')
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=100)
        plt.close()
        akis.append(KeepTogether([Paragraph(f"• {r['Test']} Analizi", test_baslik_stili), Image(img_buf, width=400, height=150)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ VE SİDEBAR ---
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
    st.subheader("📥 Toplu Veri Aktar")
    yuklenen_dosya = st.file_uploader("Excel veya CSV Yükle", type=['xlsx', 'csv'])
    if yuklenen_dosya and st.button("Verileri Havuza Aktar"):
        try:
            df_yeni = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.endswith('.csv') else pd.read_excel(yuklenen_dosya)
            df_yeni.columns = df_yeni.columns.str.strip()
            
            if 'Dogum_Tarihi' in df_yeni.columns:
                df_yeni['Dogum_Tarihi'] = pd.to_datetime(df_yeni['Dogum_Tarihi']).dt.strftime('%Y-%m-%d')
                def cq(t_str):
                    t = datetime.strptime(str(t_str), '%Y-%m-%d')
                    return f"{t.year}_Q{(t.month-1)//3+1}"
                df_yeni['Ceyrek'] = df_yeni['Dogum_Tarihi'].apply(cq)
                
            veri_kaydet_ve_merge(df_yeni)
            st.success("Aktarım Tamamlandı!"); st.rerun()
        except Exception as e: st.error(f"Hata: {e}")

# --- 5. VERİ GİRİŞ FORMU (DENEME SAYILARI İLE) ---
with st.form("ana_veri_formu"):
    st.subheader("👤 Sporcu Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=str(secilen_profil['Ad']) if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen_profil['Soyad']) if secilen_profil is not None else "")
    with c2:
        v_dt = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2012,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 150.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 40.0)

    st.divider()
    st.subheader("⏱️ Test Ölçümleri (Saniye.Milisaniye)")
    
    # Testler ve protokolleri (min: düşük değer iyidir, max: yüksek değer iyidir)
    test_specs = {
        "5m Sprint (sn)": {"mod": "min", "d": 2},
        "10m Sprint (sn)": {"mod": "min", "d": 2},
        "20m Sprint (sn)": {"mod": "min", "d": 2},
        "Dikey Sıçrama (cm)": {"mod": "max", "d": 2},
        "SKT Sağ (sn)": {"mod": "min", "d": 2},
        "SKT Sol (sn)": {"mod": "min", "d": 2},
        "LSKT Sağ (sn)": {"mod": "min", "d": 2},
        "LSKT Sol (sn)": {"mod": "min", "d": 2}
    }
    
    yeni_veriler = {}
    cols = st.columns(2)
    for i, (t_ad, conf) in enumerate(test_specs.items()):
        with cols[i % 2]:
            st.write(f"**{t_ad}**")
            d_cols = st.columns(2)
            
            # Eski değerleri çek
            v_d1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v_d2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            
            d1 = d_cols[0].number_input(f"D1", value=v_d1, format="%.3f", key=f"{t_ad}_d1")
            d2 = d_cols[1].number_input(f"D2", value=v_d2, format="%.3f", key=f"{t_ad}_d2")
            
            # En iyi dereceyi saniye/milisaniye hassasiyetinde belirle
            if conf["mod"] == "min":
                best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2))
            else:
                best = max(d1, d2)
            
            yeni_veriler[t_ad] = {"D1": d1, "D2": d2, "Best": best}
            st.caption(f"En İyi: {best:.3f}")

    if st.form_submit_button("KAYDET VE ANALİZ ET"):
        if ad and soyad:
            q = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            packet = {"Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'), "Boy": boy, "Kilo": kilo, "Ceyrek": q}
            for t, v in yeni_veriler.items():
                packet[f"{t}_D1"] = v["D1"]
                packet[f"{t}_D2"] = v["D2"]
                packet[t] = v["Best"]
            
            veri_kaydet_ve_merge(pd.DataFrame([packet]))
            st.success(f"{ad} {soyad} için veriler kaydedildi!"); st.rerun()
        else:
            st.error("Ad ve Soyad girmek zorunludur!")

# --- 6. ANALİZ VE RAPORLAMA ---
if secilen_profil is not None:
    st.divider()
    f_db = veri_oku()
    akranlar = f_db[f_db['Ceyrek'] == secilen_profil['Ceyrek']]
    analiz_datalari = []
    
    for t_ad, conf in test_specs.items():
        if t_ad in secilen_profil:
            skor = float(secilen_profil[t_ad])
            seri = akranlar[t_ad].replace(0, np.nan).dropna()
            
            if skor > 0 and len(seri) > 1:
                ort, std = seri.mean(), seri.std()
                z_ham = (skor - ort) / std if std > 0 else 0
                
                # Saniye tabanlı testlerde düşük süre iyidir (- ile çarpılır)
                z_final = round(-z_ham if conf["mod"] == "min" else z_ham, 2)
                z_final = max(min(z_final, 3.0), -3.0)
                
                if z_final >= 2.0: durum = "🌟 ELİT"
                elif z_final >= 1.0: durum = "✅ ÜST DÜZEY"
                elif z_final > -1.0: durum = "⚪ ORTALAMA"
                elif z_final > -2.0: durum = "⚠️ GELİŞTİRİLMELİ"
                else: durum = "🆘 KRİTİK"
                
                analiz_datalari.append({
                    "Test": t_ad, "Skor": f"{skor:.3f}", "Grup Ort.": round(ort,3), 
                    "Z-Skor": z_final, "Durum": durum
                })

    if analiz_datalari:
        st.subheader(f"📊 {secilen_profil['Ad']} {secilen_profil['Soyad']} - Akademik Analiz")
        st.table(pd.DataFrame(analiz_datalari))
        
        # PDF Butonu
        pdf_file = profesyonel_pdf_uret(secilen_profil, analiz_datalari)
        st.download_button("📄 PDF Analiz Raporunu İndir", pdf_file, f"{ad}_{soyad}_Rapor.pdf")
