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
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# --- 1. SİSTEM AYARLARI VE FONT ---
st.set_page_config(page_title="GKD Çoklu İstasyon Analiz", layout="wide")

def font_yukle():
    if os.path.exists("arial.ttf"):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Tr', 'arial.ttf'))
            return "Arial_Tr"
        except: return "Helvetica"
    return "Helvetica"

FONT = font_yukle()
DB_FILE = "akademik_veri_havuzu.csv"

# --- 2. VERİ YÖNETİMİ (ÇOKLU İSTASYON UYUMLU) ---
def veri_oku():
    if os.path.isfile(DB_FILE):
        return pd.read_csv(DB_FILE, encoding='utf-16')
    return pd.DataFrame()

def veri_kaydet_ve_birlestir(yeni_df):
    """
    Farklı istasyonlardan gelen verileri sporcu bazlı birleştirir.
    Eğer sporcu varsa, sadece yeni girilen sütunları günceller.
    """
    mevcut = veri_oku()
    if mevcut.empty:
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    # Ad ve Soyad üzerinden anahtar oluştur
    ad = yeni_df['Ad'].iloc[0]
    soyad = yeni_df['Soyad'].iloc[0]
    
    mask = (mevcut['Ad'] == ad) & (mevcut['Soyad'] == soyad)
    
    if mask.any():
        # Sporcu zaten var, mevcut verilerini al ve yenileriyle güncelle
        idx = mevcut.index[mask][0]
        for col in yeni_df.columns:
            # Sadece değer girilmiş (0'dan farklı) testleri güncelle
            val = yeni_df[col].iloc[0]
            if pd.notnull(val) and val != 0:
                mevcut.at[idx, col] = val
        mevcut.at[idx, 'Son_Guncelleme'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        # Yeni sporcu ekle
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        pd.concat([mevcut, yeni_df], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-16')

def get_quarter_label(date_obj):
    month = date_obj.month
    q = (month - 1) // 3 + 1
    return f"{date_obj.year}_Q{q}"

# --- 3. ARAYÜZ ---
st.title("🔬 GKD Eş Zamanlı İstasyon Veri Giriş Portalı")
st.info("Farklı bilgisayarlardan aynı sporcu için farklı test girişleri yapılabilir. Veriler merkezi olarak birleştirilir.")

# --- SPORCU SEÇİMİ VE ÇAĞIRMA ---
db = veri_oku()
sporcu_verisi = None

with st.sidebar:
    st.header("🔍 Sporcu Çağır / İstasyon Seç")
    if not db.empty:
        liste = (db['Ad'] + " " + db['Soyad']).tolist()
        secilen = st.selectbox("İşlem Yapılacak Sporcu", ["Yeni Kayıt Girişi"] + liste)
        if secilen != "Yeni Kayıt Girişi":
            sporcu_verisi = db[db['Ad'] + " " + db['Soyad'] == secilen].iloc[0]
            st.success(f"📌 {secilen} verileri yüklendi.")

# --- FORM ---
with st.form("istasyon_form"):
    st.subheader("👤 Kimlik Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad", value=sporcu_verisi['Ad'] if sporcu_verisi is not None else "")
        soyad = st.text_input("Soyad", value=sporcu_verisi['Soyad'] if sporcu_verisi is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(sporcu_verisi['Dogum_Tarihi']), '%Y-%m-%d') if sporcu_verisi is not None else datetime(2010,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
        boy = st.number_input("Boy (cm)", value=float(sporcu_verisi['Boy']) if sporcu_verisi is not None else 160.0)
    with c3:
        kilo = st.number_input("Kilo (kg)", value=float(sporcu_verisi['Kilo']) if sporcu_verisi is not None else 50.0)
        ayak = st.selectbox("Ayak", ["Sağ", "Sol"], index=0 if sporcu_verisi is None or sporcu_verisi['Ayak']=="Sağ" else 1)

    st.divider()
    st.subheader("⏱️ İstasyon Ölçümleri (Sadece Bulunduğunuz İstasyonun Verisini Giriniz)")
    
    test_yapisi = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    yeni_test_girdileri = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_yapisi.items()):
        with cols[i % 2]:
            st.markdown(f"**{t_ad}**")
            # Mevcut kayıt varsa getir
            v_d1 = float(sporcu_verisi[f"{t_ad}_D1"]) if sporcu_verisi is not None else 0.0
            v_d2 = float(sporcu_verisi[f"{t_ad}_D2"]) if sporcu_verisi is not None else 0.0
            
            d1 = st.number_input("1. Deneme", key=f"{t_ad}_1", value=v_d1, format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}_2", value=v_d2, format="%.3f")
            
            # En iyi skor hesaplama
            if d1 > 0 and d2 > 0: best = min(d1, d2) if mod == "min" else max(d1, d2)
            else: best = max(d1, d2)
            
            yeni_test_girdileri[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    save = st.form_submit_button("İSTASYON VERİSİNİ KAYDET VE ANALİZİ GÜNCELLE", use_container_width=True)

if save:
    ceyrek = get_quarter_label(dogum)
    
    # Veri birleştirme ve kaydetme
    entry = {"Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum, "Boy": boy, "Kilo": kilo, "Ayak": ayak, "Ceyrek": ceyrek}
    for t, v in yeni_test_girdileri.items():
        entry[f"{t}_D1"] = v["D1"]; entry[f"{t}_D2"] = v["D2"]; entry[t] = v["Best"]
    
    veri_kaydet_ve_birlestir(pd.DataFrame([entry]))
    
    # Güncel veri üzerinden istatistik (Sadece aynı çeyrek/akran grubu)
    db_updated = veri_oku()
    akranlar = db_updated[db_updated['Ceyrek'] == ceyrek]
    
    final_stats = []
    for t_ad, mod in test_yapisi.items():
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        if not seri.empty:
            ort, std = seri.mean(), (seri.std() if len(seri)>1 else 0)
            en_iyi, en_kotu = (seri.min(), seri.max()) if mod == "min" else (seri.max(), seri.min())
            skor = yeni_test_girdileri[t_ad]["Best"]
            z = (skor - ort) / std if std > 0 else 0
            
            final_stats.append({
                "Test": t_ad, "Skor": skor, "Ort": round(ort,3), "Std": round(std,3),
                "Max": en_iyi, "Min": en_kotu, "Z": round(z,2)
            })

    st.subheader(f"📊 {ceyrek} Akran Analiz Tablosu")
    st.table(pd.DataFrame(final_stats))

    # --- PDF RAPOR ---
    def generate_pdf():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        c.setFont(FONT, 16); c.drawCentredString(w/2, h-40, "AKADEMİK PERFORMANS ANALİZ RAPORU")
        c.setFont(FONT, 10); c.drawString(50, h-70, f"Sporcu: {ad} {soyad} | Dilim: {ceyrek}")
        c.line(50, h-75, 550, h-75)

        y = h - 100
        for s in final_stats:
            if y < 300: c.showPage(); y = h - 50
            c.setFont(FONT, 12); c.drawString(50, y, f"TEST: {s['Test']}")
            y -= 15; c.setFont(FONT, 8)
            info = f"Skor: {s['Skor']} | Akran Ort: {s['Ort']} | Std: {s['Std']} | Grup En İyi: {s['Max']} | Grup En Kötü: {s['Min']} | Z: {s['Z']}"
            c.drawString(60, y, info)
            
            # Grafik
            plt.figure(figsize=(5, 2.5))
            plt.barh(['En Kötü', 'Akran Ort.', 'Sporcu', 'En İyi'], [s['Min'], s['Ort'], s['Skor'], s['Max']], color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
            plt.title(f"{s['Test']} Kıyaslama")
            plt.tight_layout()
            img_s = io.BytesIO(); plt.savefig(img_s, format='png', dpi=100); plt.close(); img_s.seek(0)
            
            y -= 135
            c.drawImage(ImageReader(img_s), 60, y, width=320, preserveAspectRatio=True)
            y -= 35; c.line(50, y, 500, y); y -= 25

        c.save(); buf.seek(0)
        return buf

    st.download_button("📄 Detaylı Raporu İndir (PDF)", generate_pdf(), f"{ad}_{soyad}_Rapor.pdf", use_container_width=True)
