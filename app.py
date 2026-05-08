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

# --- 1. SİSTEM AYARLARI VE FONT GÜVENLİĞİ ---
st.set_page_config(page_title="GKD İstasyon Sistemi", layout="wide")

def font_yukle():
    """GitHub/Linux üzerinde büyük-küçük harf duyarlılığını yönetir."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Olası tüm font dosyası isimlerini tara
    font_names = ["arial.ttf", "Arial.ttf", "ARIAL.TTF"]
    
    for name in font_names:
        font_path = os.path.join(current_dir, name)
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial_Tr', font_path))
                return 'Arial_Tr'
            except:
                continue
    
    st.warning("Font dosyası bulunamadı, sistem fontuna (Helvetica) dönülüyor.")
    return 'Helvetica'

FONT = font_yukle()
DB_FILE = "akademik_veri_havuzu.csv"

# --- 2. VERİ YÖNETİMİ (İSTASYONLAR ARASI VERİ MERGE) ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, encoding='utf-16')
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    """Farklı makinelerden gelen verileri sporcu ismine göre birleştirir."""
    mevcut = veri_oku()
    if mevcut.empty:
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return

    ad = yeni_df['Ad'].iloc[0]
    soyad = yeni_df['Soyad'].iloc[0]
    
    mask = (mevcut['Ad'] == ad) & (mevcut['Soyad'] == soyad)
    
    if mask.any():
        idx = mevcut.index[mask][0]
        # Sadece değeri 0'dan büyük olan (yeni girilen) sütunları güncelle
        for col in yeni_df.columns:
            yeni_val = yeni_df[col].iloc[0]
            # Eğer yeni_val bir sayıysa ve 0'dan büyükse VEYA metinse ve boş değilse güncelle
            if pd.notnull(yeni_val):
                if isinstance(yeni_val, (int, float)) and yeni_val > 0:
                    mevcut.at[idx, col] = yeni_val
                elif isinstance(yeni_val, str) and yeni_val != "":
                    mevcut.at[idx, col] = yeni_val
        mevcut.at[idx, 'Son_Guncelleme'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        pd.concat([mevcut, yeni_df], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-16')

def get_quarter(date_obj):
    return f"{date_obj.year}_Q{(date_obj.month - 1) // 3 + 1}"

# --- 3. ÖĞRENCİ ÇAĞIRMA (SIDEBAR) ---
db = veri_oku()
secilen_sporcu = None

# Sidebar her zaman görünür olmalı
with st.sidebar:
    st.header("🔍 Sporcu Paneli")
    if not db.empty:
        # İsim ve soyada göre benzersiz liste oluştur
        isim_listesi = (db['Ad'] + " " + db['Soyad']).tolist()
        secim = st.selectbox("Kayıtlı Bir Sporcu Seçin", ["-- Yeni Kayıt --"] + isim_listesi)
        
        if secim != "-- Yeni Kayıt --":
            secilen_sporcu = db[db['Ad'] + " " + db['Soyad'] == secim].iloc[0]
            st.success(f"✅ {secim} yüklendi. İstasyon verilerini girebilirsiniz.")
    else:
        st.info("Veritabanı henüz boş. İlk kaydı yapın.")

# --- 4. VERİ GİRİŞ FORMU ---
with st.form("ana_form"):
    st.subheader("👤 Sporcu ve İstasyon Tanımlama")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        ad = st.text_input("Ad", value=secilen_sporcu['Ad'] if secilen_sporcu is not None else "")
        soyad = st.text_input("Soyad", value=secilen_sporcu['Soyad'] if secilen_sporcu is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(secilen_sporcu['Dogum_Tarihi']), '%Y-%m-%d') if secilen_sporcu is not None else datetime(2010, 1, 1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
        boy = st.number_input("Boy (cm)", value=float(secilen_sporcu['Boy']) if secilen_sporcu is not None else 165.0)
    with c3:
        kilo = st.number_input("Kilo (kg)", value=float(secilen_sporcu['Kilo']) if secilen_sporcu is not None else 60.0)
        ayak = st.selectbox("Ayak", ["Sağ", "Sol"], index=0 if secilen_sporcu is None or secilen_sporcu['Ayak']=="Sağ" else 1)

    st.divider()
    st.subheader("⏱️ Performans Testleri (2 Deneme)")
    st.caption("Farklı istasyonlarda çalışıyorsanız, sadece kendi istasyonunuzun verisini girip kaydedin.")
    
    testler = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    girdiler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(testler.items()):
        with cols[i % 2]:
            st.write(f"**{t_ad}**")
            # Mevcut değerleri forma doldur (0.0 ise boş görünür)
            v_d1 = float(secilen_sporcu[f"{t_ad}_D1"]) if secilen_sporcu is not None else 0.0
            v_d2 = float(secilen_sporcu[f"{t_ad}_D2"]) if secilen_sporcu is not None else 0.0
            
            d1 = st.number_input("1. Deneme", key=f"{t_ad}_d1", value=v_d1, format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}_d2", value=v_d2, format="%.3f")
            
            # En iyi skoru belirle
            if d1 > 0 and d2 > 0: best = min(d1, d2) if mod == "min" else max(d1, d2)
            else: best = max(d1, d2)
            girdiler[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    kaydet = st.form_submit_button("VERİLERİ SİSTEME GÖNDER VE ANALİZ ET", use_container_width=True)

if kaydet:
    if not ad or not soyad:
        st.error("Ad ve Soyad alanları zorunludur!")
    else:
        q_dilim = get_quarter(dogum)
        # Veri Paketi
        data_packet = {
            "Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum, "Boy": boy, 
            "Kilo": kilo, "Ayak": ayak, "Ceyrek": q_dilim
        }
        for t, v in girdiler.items():
            data_packet[f"{t}_D1"] = v["D1"]; data_packet[f"{t}_D2"] = v["D2"]; data_packet[t] = v["Best"]
        
        veri_kaydet_ve_merge(pd.DataFrame([data_packet]))
        st.success(f"Başarılı: {ad} {soyad} verileri güncellendi. Çeyrek: {q_dilim}")
        st.rerun() # Sidebar'ı güncellemek için

# --- 5. İSTATİSTİK VE RAPORLAMA BÖLÜMÜ ---
# (Formun dışında, en güncel veriye göre sonuçları gösterir)
if secilen_sporcu is not None:
    st.divider()
    st.subheader(f"📊 {secilen_sporcu['Ad']} {secilen_sporcu['Soyad']} - Performans Analizi")
    
    current_db = veri_oku()
    q_akranlar = current_db[current_db['Ceyrek'] == secilen_sporcu['Ceyrek']]
    
    rapor_verisi = []
    for t_ad, mod in testler.items():
        seri = q_akranlar[t_ad].replace(0, np.nan).dropna()
        if not seri.empty:
            ort, std = seri.mean(), (seri.std() if len(seri) > 1 else 0)
            en_iyi, en_kotu = (seri.min(), seri.max()) if mod == "min" else (seri.max(), seri.min())
            skor = float(secilen_sporcu[t_ad])
            z = (skor - ort) / std if std > 0 else 0
            
            rapor_verisi.append({
                "Test": t_ad, "Skor": skor, "Akran Ort.": round(ort, 3), 
                "Maks": en_iyi, "Min": en_kotu, "Z-Skor": round(z, 2)
            })

    if rapor_verisi:
        st.table(pd.DataFrame(rapor_verisi))
        
        # PDF OLUŞTURMA FONKSİYONU
        def pdf_uret():
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            c.setFont(FONT, 16); c.drawCentredString(w/2, h-40, "AKADEMİK PERFORMANS RAPORU")
            c.setFont(FONT, 10); c.drawString(50, h-70, f"Sporcu: {secilen_sporcu['Ad']} {secilen_sporcu['Soyad']} | Dilim: {secilen_sporcu['Ceyrek']}")
            c.line(50, h-75, 550, h-75)
            
            y = h - 100
            for item in rapor_verisi:
                if y < 300: c.showPage(); y = h - 50
                c.setFont(FONT, 12); c.drawString(50, y, f"TEST: {item['Test']}")
                y -= 15; c.setFont(FONT, 8)
                c.drawString(60, y, f"Skor: {item['Skor']} | Ort: {item['Akran Ort.']} | En İyi: {item['Maks']} | En Kötü: {item['Min']} | Z: {item['Z-Skor']}")
                
                # Grafik
                plt.figure(figsize=(5, 2.5))
                plt.barh(['En Kötü', 'Ortalama', 'Sporcu', 'En İyi'], 
                         [item['Min'], item['Akran Ort.'], item['Skor'], item['Maks']], 
                         color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
                plt.tight_layout()
                img_s = io.BytesIO(); plt.savefig(img_s, format='png', dpi=100); plt.close(); img_s.seek(0)
                
                y -= 135
                c.drawImage(ImageReader(img_s), 60, y, width=320, preserveAspectRatio=True)
                y -= 40; c.line(50, y, 500, y); y -= 20
                
            c.save(); buf.seek(0)
            return buf

        st.download_button("📄 PDF Analiz Raporunu İndir", pdf_uret(), f"{secilen_sporcu['Ad']}_Rapor.pdf", use_container_width=True)
