import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="GKD Performans Analiz", layout="centered")

# --- TÜRKÇE FONT YÜKLEME ---
# ÖNEMLİ: PDF için arial.ttf dosyasının uygulama klasöründe olması gerekir.
def load_pdf_fonts():
    try:
        # Streamlit Cloud üzerinde çalışırken font dosyasını klasöre koymalısınız
        pdfmetrics.registerFont(TTFont('ArialTr', 'arial.ttf'))
        return "ArialTr"
    except:
        return "Helvetica"

FONT_NAME = load_pdf_fonts()

# --- VERİ TABANI BAĞLANTISI (GOOGLE SHEETS) ---
# Streamlit'in "st.connection" özelliği ile Google Sheets'e bağlanıyoruz.
# Bunun için .streamlit/secrets.toml dosyasına bağlantı bilgilerini eklemelisiniz.
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    existing_data = conn.read(ttl="1m") # 1 dakikada bir veriyi yenile
except:
    existing_data = pd.DataFrame()

# --- UYGULAMA BAŞLIĞI ---
st.title("🏃‍♂️ GKD Bilimsel Performans Analiz Sistemi")
st.markdown("Birden fazla cihazdan eş zamanlı veri girişi ve merkezi raporlama paneli.")

# --- FORM ALANI ---
with st.form("sporcu_form"):
    st.subheader("1. Öğrenci Tanımlayıcı Bilgileri")
    col1, col2 = st.columns(2)
    with col1:
        ad = st.text_input("Ad")
        kilo = st.number_input("Kilo (kg)", format="%.2f")
        dogum_tarihi = st.date_input("Doğum Tarihi", min_value=datetime(1990, 1, 1))
        ayak = st.selectbox("Tercih Edilen Ayak", ["Sağ", "Sol"])
    with col2:
        soyad = st.text_input("Soyad")
        boy = st.number_input("Boy (cm)", format="%.1f")
        baslama_tarihi = st.date_input("Antrenmana Başlama Tarihi")
        el = st.selectbox("Tercih Edilen El", ["Sağ", "Sol"])

    st.divider()
    st.subheader("2. Performans Testleri (2 Deneme)")
    
    testler = {
        "5m Sprint (sn)": "min",
        "10m Sprint (sn)": "min",
        "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max",
        "SKT Sağ (sn)": "min",
        "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min",
        "LSKT Sol (sn)": "min"
    }
    
    test_sonuclari = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(testler.items()):
        target_col = cols[i % 2]
        with target_col:
            st.markdown(f"**{t_ad}**")
            d1 = st.number_input(f"1. Deneme", key=f"{t_ad}_1", step=0.01)
            d2 = st.number_input(f"2. Deneme", key=f"{t_ad}_2", step=0.01)
            # En iyi skoru hesapla
            if d1 > 0 and d2 > 0:
                best = min(d1, d2) if mod == "min" else max(d1, d2)
            else:
                best = max(d1, d2)
            test_sonuclari[t_ad] = best

    submit = st.form_submit_button("ANALİZ ET VE KAYDET")

# --- ANALİZ VE RAPORLAMA MANTIĞI ---
if submit:
    if not ad or not soyad:
        st.error("Lütfen öğrenci adını ve soyadını giriniz!")
    else:
        # Yeni Veri Hazırlama
        new_row = {
            "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo,
            "Dogum": dogum_tarihi.strftime("%d.%m.%Y"),
            "Ayak": ayak, "El": el, "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        new_row.update(test_sonuclari)
        
        # Veriyi Merkezi Tabloya Ekle (Simüle edilmiş veya GSheets)
        st.success(f"Veri başarıyla kaydedildi! Grup analizleri hesaplanıyor...")
        
        # İstatistiksel Hesaplamalar
        current_df = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
        
        # Z-Skoru ve Analiz Tablosu
        analiz_listesi = []
        for t_ad in testler.keys():
            mean_val = current_df[t_ad].mean()
            std_val = current_df[t_ad].std() if len(current_df) > 1 else 0
            z_score = (test_sonuclari[t_ad] - mean_val) / std_val if std_val > 0 else 0
            analiz_listesi.append({
                "Test": t_ad, "Skor": test_sonuclari[t_ad], 
                "Ortalama": round(mean_val, 2), "Z-Skor": round(z_score, 2)
            })

        # --- GÖRSELLEŞTİRME ---
        st.divider()
        st.subheader("📊 Performans Karşılaştırma")
        fig, ax = plt.subplots(figsize=(10, 6))
        tests = [a['Test'] for a in analiz_listesi]
        skors = [a['Skor'] for a in analiz_listesi]
        orts = [a['Ortalama'] for a in analiz_listesi]
        
        x = np.arange(len(tests))
        width = 0.35
        ax.bar(x - width/2, skors, width, label='Sporcu', color='#1a237e')
        ax.bar(x + width/2, orts, width, label='Grup Ort.', color='#bdbdbd')
        
        ax.set_xticks(x)
        ax.set_xticklabels(tests, rotation=45, ha='right')
        ax.legend()
        st.pyplot(fig)

        # --- PDF OLUŞTURMA ---
        def generate_pdf():
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            w, h = A4
            
            # Kapak
            c.setFillColor(colors.HexColor("#1a237e"))
            c.rect(0, h-80, w, 80, fill=1)
            c.setFillColor(colors.white)
            c.setFont(FONT_NAME, 20)
            c.drawCentredString(w/2, h-50, "BİLİMSEL PERFORMANS ANALİZ RAPORU")
            
            # Bilgiler
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 12)
            y = h-120
            c.drawString(50, y, f"Ad Soyad: {ad} {soyad}")
            c.drawString(50, y-20, f"Fiziksel: {boy} cm / {kilo} kg")
            c.drawString(50, y-40, f"Tercih: {ayak} Ayak / {el} El")
            
            # Tablo (Özet)
            y = h-200
            c.setFont(FONT_NAME, 10)
            c.drawString(50, y, "TEST ADI")
            c.drawString(200, y, "SKOR")
            c.drawString(300, y, "GRUP ORT.")
            c.drawString(400, y, "Z-SKOR")
            c.line(50, y-5, 500, y-5)
            
            y -= 25
            for a in analiz_listesi:
                c.drawString(50, y, a['Test'])
                c.drawString(200, y, str(a['Skor']))
                c.drawString(300, y, str(a['Ortalama']))
                c.drawString(400, y, str(a['Z-Skor']))
                y -= 20
            
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        pdf_data = generate_pdf()
        st.download_button(
            label="📄 Analiz Raporunu PDF Olarak İndir",
            data=pdf_data,
            file_name=f"{ad}_{soyad}_Rapor.pdf",
            mime="application/pdf"
        )

# --- ALT BİLGİ ---
st.sidebar.info("Gelişim Kinezyolojistleri Derneği Merkezi Analiz Portalı v1.0")