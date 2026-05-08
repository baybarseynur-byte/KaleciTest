import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

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

# --- 2. VERİ YÖNETİMİ (HATA DÜZELTİLMİŞ MERGE MANTIĞI) ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            # Pandas veri tipi hatalarını önlemek için boş değerleri standartlaştır
            return df
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
        # HATA ÇÖZÜMÜ: Sütun sütun tip kontrolü yaparak güncelleme
        for col in yeni_df.columns:
            val = yeni_df[col].iloc[0]
            # Sadece geçerli, boş olmayan ve 0'dan büyük verileri güncelle
            if pd.notnull(val) and val != 0 and val != "":
                # Pandas'ın tip hatası vermemesi için sütunu 'object' tipine zorla veya dönüştür
                if mevcut[col].dtype != yeni_df[col].dtype:
                    mevcut[col] = mevcut[col].astype(object)
                mevcut.loc[idx, col] = val
        
        mevcut.loc[idx, 'Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        pd.concat([mevcut, yeni_df], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-16')

def get_age_quarter(date_obj):
    return f"{date_obj.year}_Q{(date_obj.month - 1) // 3 + 1}"

# --- 3. ÖĞRENCİ ÇAĞIRMA ---
db = veri_oku()
secilen = None

with st.sidebar:
    st.header("🔍 Öğrenci Arama/Seçme")
    if not db.empty:
        isimler = (db['Ad'].astype(str) + " " + db['Soyad'].astype(str)).tolist()
        arama = st.selectbox("Kayıtlı Öğrenciler", ["-- Yeni Kayıt --"] + isimler)
        if arama != "-- Yeni Kayıt --":
            secilen = db.iloc[isimler.index(arama)]
            st.success(f"Profil Yüklendi: {arama}")
    else:
        st.info("Henüz kayıt bulunmuyor.")

# --- 4. GİRİŞ FORMU (TANIMLAYICI VE TESTLER) ---
with st.form("akademik_form"):
    st.subheader("👤 Tanımlayıcı Bilgiler")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ad = st.text_input("Ad", value=str(secilen['Ad']) if secilen is not None else "")
        soyad = st.text_input("Soyad", value=str(secilen['Soyad']) if secilen is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(secilen['Dogum_Tarihi']), '%Y-%m-%d') if secilen is not None else datetime(2010,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
        v_ant = datetime.strptime(str(secilen['Ant_Baslama']), '%Y-%m-%d') if secilen is not None and pd.notnull(secilen['Ant_Baslama']) else datetime.now()
        ant_baslama = st.date_input("Antrenman Başlama Tarihi", value=v_ant)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen['Boy']) if secilen is not None else 160.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen['Kilo']) if secilen is not None else 50.0)
    with c4:
        ayak = st.selectbox("Ayak Tercihi", ["Sağ", "Sol"], index=0 if secilen is None or secilen['Ayak']=="Sağ" else 1)
        el = st.selectbox("El Tercihi", ["Sağ", "Sol"], index=0 if secilen is None or secilen['El']=="Sağ" else 1)

    st.divider()
    st.subheader("⏱️ İstasyon Testleri (2 Deneme)")
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    girdiler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with cols[i % 2]:
            st.markdown(f"**{t_ad}**")
            v_d1 = float(secilen[f"{t_ad}_D1"]) if secilen is not None else 0.0
            v_d2 = float(secilen[f"{t_ad}_D2"]) if secilen is not None else 0.0
            d1 = st.number_input("1. Deneme", key=f"{t_ad}1", value=v_d1, format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}2", value=v_d2, format="%.3f")
            
            best = (min(d1, d2) if d1>0 and d2>0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            girdiler[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    save = st.form_submit_button("VERİLERİ GÜNCELLE VE KAYDET")

if save:
    if not ad or not soyad:
        st.error("Ad ve Soyad boş bırakılamaz.")
    else:
        q = get_age_quarter(dogum)
        packet = {
            "Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum, "Ant_Baslama": ant_baslama,
            "Boy": boy, "Kilo": kilo, "Ayak": ayak, "El": el, "Ceyrek": q
        }
        for t, v in girdiler.items():
            packet[f"{t}_D1"] = v["D1"]; packet[f"{t}_D2"] = v["D2"]; packet[t] = v["Best"]
        
        veri_kaydet_ve_merge(pd.DataFrame([packet]))
        st.success("Veriler başarıyla işlendi.")
        st.rerun()

# --- 5. DEĞERLENDİRME VE RAPORLAMA ---
if secilen is not None:
    st.divider()
    st.subheader(f"📊 Performans Durumu: {secilen['Ad']} {secilen['Soyad']}")
    
    f_db = veri_oku()
    akranlar = f_db[f_db['Ceyrek'] == secilen['Ceyrek']]
    
    analiz_datalari = []
    for t_ad, mod in test_specs.items():
        skor = float(secilen[t_ad])
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        
        if skor > 0 and not seri.empty:
            ort, std = seri.mean(), (seri.std() if len(seri)>1 else 0)
            en_iyi, en_kotu = (seri.min(), seri.max()) if mod == "min" else (seri.max(), seri.min())
            z = (skor - ort) / std if std > 0 else 0
            
            analiz_datalari.append({
                "Test": t_ad, "Skor": skor, "Grup Ort.": round(ort,3), 
                "Z-Skor": round(z,2), "En İyi": en_iyi, "En Kötü": en_kotu
            })

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        
        def pdf_cikar():
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            c.setFont(FONT, 16); c.drawCentredString(w/2, h-40, "BİREYSEL PERFORMANS ANALİZ RAPORU")
            c.setFont(FONT, 10); c.drawString(50, h-70, f"Sporcu: {secilen['Ad']} {secilen['Soyad']} | Grup: {secilen['Ceyrek']}")
            c.drawString(50, h-85, f"Boy/Kilo: {secilen['Boy']}cm / {secilen['Kilo']}kg | Branş Yaşı: {ant_baslama.year}")
            c.line(50, h-90, 550, h-90)
            
            y = h - 120
            for r in analiz_datalari:
                if y < 300: c.showPage(); y = h - 50
                c.setFont(FONT, 12); c.drawString(50, y, f"TEST: {r['Test']}")
                y -= 15; c.setFont(FONT, 8)
                c.drawString(60, y, f"Skor: {r['Skor']} | Ort: {r['Grup Ort.']} | Z: {r['Z-Skor']} | Grup En İyi: {r['En İyi']}")
                
                plt.figure(figsize=(5, 2.5))
                plt.barh(['En Kötü', 'Ortalama', 'Sporcu', 'En İyi'], 
                         [float(r['En Kötü']), float(r['Grup Ort.']), float(r['Skor']), float(r['En İyi'])], 
                         color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
                plt.tight_layout()
                img_s = io.BytesIO(); plt.savefig(img_s, format='png', dpi=100); plt.close(); img_s.seek(0)
                y -= 135
                c.drawImage(ImageReader(img_s), 60, y, width=320, preserveAspectRatio=True)
                y -= 40; c.line(50, y, 500, y); y -= 20
            
            c.save(); buf.seek(0)
            return buf

        st.download_button("📄 PDF Analiz Raporu Al", pdf_cikar(), f"{secilen['Ad']}_Analiz.pdf", use_container_width=True)
