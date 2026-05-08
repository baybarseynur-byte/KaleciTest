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
st.set_page_config(page_title="GKD Bilimsel Performans Analizi", layout="wide")

def font_yukle():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Linux/GitHub uyumu için büyük-küçük harf kontrolü
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

# --- 2. VERİ YÖNETİMİ (MERKEZİ VE PARALEL İSTASYON UYUMLU) ---
def veri_oku():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE, encoding='utf-16')
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_merge(yeni_df):
    mevcut = veri_oku()
    if mevcut.empty:
        yeni_df.to_csv(DB_FILE, index=False, encoding='utf-16')
        return
    
    ad, soyad = yeni_df['Ad'].iloc[0], yeni_df['Soyad'].iloc[0]
    mask = (mevcut['Ad'] == ad) & (mevcut['Soyad'] == soyad)
    
    if mask.any():
        idx = mevcut.index[mask][0]
        for col in yeni_df.columns:
            val = yeni_df[col].iloc[0]
            # Sadece yeni veri girilmişse (0'dan büyükse) mevcut sporcuyu güncelle
            if pd.notnull(val) and val != 0 and val != "":
                mevcut.at[idx, col] = val
        mevcut.at[idx, 'Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        mevcut.to_csv(DB_FILE, index=False, encoding='utf-16')
    else:
        yeni_df['Son_Guncelleme'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        pd.concat([mevcut, yeni_df], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-16')

def get_age_quarter(date_obj):
    return f"{date_obj.year}_Q{(date_obj.month - 1) // 3 + 1}"

# --- 3. SPORCU SEÇİMİ (SIDEBAR) ---
db = veri_oku()
secilen_sporcu = None

with st.sidebar:
    st.header("🔍 Sporcu Çağırma")
    if not db.empty:
        isimler = (db['Ad'] + " " + db['Soyad']).tolist()
        secim = st.selectbox("Kayıtlı Sporcu", ["-- Yeni Kayıt Girişi --"] + isimler)
        if secim != "-- Yeni Kayıt Girişi --":
            secilen_sporcu = db[db['Ad'] + " " + db['Soyad'] == secim].iloc[0]
            st.success(f"Profil: {secim}")
    else:
        st.info("Veritabanı boş.")

# --- 4. FORM (TANIMLAYICI BİLGİLER VE TESTLER) ---
with st.form("ana_form"):
    st.subheader("👤 1. Sporcu Tanımlayıcı Bilgileri")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ad = st.text_input("Ad", value=secilen_sporcu['Ad'] if secilen_sporcu is not None else "")
        soyad = st.text_input("Soyad", value=secilen_sporcu['Soyad'] if secilen_sporcu is not None else "")
    with c2:
        v_dogum = datetime.strptime(str(secilen_sporcu['Dogum_Tarihi']), '%Y-%m-%d') if secilen_sporcu is not None else datetime(2010,1,1)
        dogum = st.date_input("Doğum Tarihi", value=v_dogum)
        v_baslama = datetime.strptime(str(secilen_sporcu['Baslama_Tarihi']), '%Y-%m-%d') if secilen_sporcu is not None and pd.notnull(secilen_sporcu['Baslama_Tarihi']) else datetime.now()
        baslama = st.date_input("Antrenman Başlama Tarihi", value=v_baslama)
    with c3:
        boy = st.number_input("Boy (cm)", value=float(secilen_sporcu['Boy']) if secilen_sporcu is not None else 165.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_sporcu['Kilo']) if secilen_sporcu is not None else 55.0)
    with c4:
        ayak = st.selectbox("Tercih Edilen Ayak", ["Sağ", "Sol"], index=0 if secilen_sporcu is None or secilen_sporcu['Ayak']=="Sağ" else 1)
        el = st.selectbox("Tercih Edilen El", ["Sağ", "Sol"], index=0 if secilen_sporcu is None or secilen_sporcu['El']=="Sağ" else 1)

    st.divider()
    st.subheader("⏱️ 2. Performans Testleri (Sağ/Sol ve Denemeler)")
    
    # Test Tanımları: (İsim, Değerlendirme Modu)
    test_protokolu = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", 
        "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    girdiler = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_protokolu.items()):
        with cols[i % 2]:
            st.markdown(f"**{t_ad}**")
            v_d1 = float(secilen_sporcu[f"{t_ad}_D1"]) if secilen_sporcu is not None else 0.0
            v_d2 = float(secilen_sporcu[f"{t_ad}_D2"]) if secilen_sporcu is not None else 0.0
            
            d1 = st.number_input("1. Deneme", key=f"{t_ad}_1", value=v_d1, format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}_2", value=v_d2, format="%.3f")
            
            if d1 > 0 and d2 > 0: best = min(d1, d2) if mod == "min" else max(d1, d2)
            else: best = max(d1, d2)
            girdiler[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    submit = st.form_submit_button("VERİLERİ MERKEZİ SİSTEME KAYDET", use_container_width=True)

if submit:
    if not ad or not soyad:
        st.error("Ad ve Soyad zorunludur!")
    else:
        dilim = get_age_quarter(dogum)
        packet = {
            "Ad": ad, "Soyad": soyad, "Dogum_Tarihi": dogum, "Baslama_Tarihi": baslama,
            "Boy": boy, "Kilo": kilo, "Ayak": ayak, "El": el, "Ceyrek": dilim
        }
        for t, v in girdiler.items():
            packet[f"{t}_D1"] = v["D1"]; packet[f"{t}_D2"] = v["D2"]; packet[t] = v["Best"]
        
        veri_kaydet_ve_merge(pd.DataFrame([packet]))
        st.success(f"İstasyon verisi başarıyla senkronize edildi. (Grup: {dilim})")
        st.rerun()

# --- 5. DEĞERLENDİRME VE RAPORLAMA ---
if secilen_sporcu is not None:
    st.divider()
    st.subheader(f"📊 Performans Analizi: {secilen_sporcu['Ad']} {secilen_sporcu['Soyad']}")
    
    # Güncel veri üzerinden akran istatistiklerini hesapla
    full_db = veri_oku()
    akranlar = full_db[full_db['Ceyrek'] == secilen_sporcu['Ceyrek']]
    
    analiz_listesi = []
    biten_test_sayisi = 0
    for t_ad, mod in test_protokolu.items():
        seri = akranlar[t_ad].replace(0, np.nan).dropna()
        skor = float(secilen_sporcu[t_ad])
        
        durum = "✅ Tamamlandı" if skor > 0 else "❌ Bekleniyor"
        if skor > 0: biten_test_sayisi += 1
        
        if not seri.empty and skor > 0:
            ort, std = seri.mean(), (seri.std() if len(seri)>1 else 0)
            en_iyi, en_kotu = (seri.min(), seri.max()) if mod == "min" else (seri.max(), seri.min())
            z = (skor - ort) / std if std > 0 else 0
            
            analiz_listesi.append({
                "Test": t_ad, "Skor": skor, "Akran Ort.": round(ort,3), 
                "Z-Skor": round(z,2), "En İyi": en_iyi, "En Kötü": en_kotu, "Durum": durum
            })
        else:
            analiz_listesi.append({"Test": t_ad, "Skor": "-", "Akran Ort.": "-", "Z-Skor": "-", "En İyi": "-", "En Kötü": "-", "Durum": durum})

    st.table(pd.DataFrame(analiz_listesi))
    
    if biten_test_sayisi > 0:
        # PDF OLUŞTURMA
        def pdf_olustur():
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            
            # Üst Bilgi
            c.setFont(FONT, 16); c.drawCentredString(w/2, h-40, "AKADEMİK PERFORMANS ANALİZ RAPORU")
            c.setFont(FONT, 10); 
            c.drawString(50, h-70, f"Sporcu: {secilen_sporcu['Ad']} {secilen_sporcu['Soyad']} | Dilim: {secilen_sporcu['Ceyrek']}")
            c.drawString(50, h-85, f"Fiziksel: {secilen_sporcu['Boy']} cm / {secilen_sporcu['Kilo']} kg | Tercih: {secilen_sporcu['Ayak']} Ayak - {secilen_sporcu['El']} El")
            c.line(50, h-95, 550, h-95)
            
            y = h - 120
            for row in analiz_listesi:
                if row['Skor'] == "-": continue # Tamamlanmamış testi rapora basma
                if y < 300: c.showPage(); y = h - 50
                
                c.setFont(FONT, 12); c.drawString(50, y, f"TEST: {row['Test']}")
                y -= 15; c.setFont(FONT, 8)
                bilgi = f"Skor: {row['Skor']} | Ort: {row['Akran Ort.']} | Z-Skor: {row['Z-Skor']} | En İyi: {row['En İyi']} | En Kötü: {row['En Kötü']}"
                c.drawString(60, y, bilgi)
                
                # Grafik
                plt.figure(figsize=(5, 2.5))
                plt.barh(['En Kötü', 'Ortalama', 'Sporcu', 'En İyi'], 
                         [float(row['En Kötü']), float(row['Akran Ort.']), float(row['Skor']), float(row['En İyi'])], 
                         color=['#ff8a80', '#cfd8dc', '#1a237e', '#81c784'])
                plt.tight_layout()
                img_s = io.BytesIO(); plt.savefig(img_s, format='png', dpi=100); plt.close(); img_s.seek(0)
                
                y -= 135
                c.drawImage(ImageReader(img_s), 60, y, width=320, preserveAspectRatio=True)
                y -= 35; c.line(50, y, 500, y); y -= 25
            
            c.save(); buf.seek(0)
            return buf

        st.download_button(f"📄 PDF Raporu İndir ({biten_test_sayisi}/{len(test_protokolu)} Test)", 
                           pdf_olustur(), f"{secilen_sporcu['Ad']}_Rapor.pdf", use_container_width=True)

# --- 6. ARAŞTIRMACI PANELİ ---
with st.sidebar:
    st.divider()
    if not db.empty:
        csv_data = db.to_csv(index=False).encode('utf-16')
        st.download_button("📂 Tüm Veriyi İndir (Excel/SPSS)", csv_data, "akademik_veri_toplu.csv", "text/csv")
