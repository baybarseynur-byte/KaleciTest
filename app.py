import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, io, platform
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# --- 1. AYARLAR VE FONT MOTORU ---
st.set_page_config(page_title="GKD Performans Analiz", layout="wide")

def font_yukle():
    """PDF'de Türkçe karakter hatasını önlemek için fontu yükler."""
    font_path = "arial.ttf" # Uygulama klasöründe bulunmalıdır
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Tr', font_path))
            pdfmetrics.registerFont(TTFont('Arial_Tr_Bold', font_path)) # Kalın font simülasyonu
            return "Arial_Tr"
        except:
            return "Helvetica"
    return "Helvetica"

FONT_NAME = font_yukle()

# --- 2. VERİ YÖNETİMİ ---
# Not: Gerçek bir bulut deneyimi için Google Sheets Connection kullanılabilir.
# Bu versiyon, Streamlit oturumu (session) boyunca verileri hafızada tutar.
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()

# --- 3. ARAYÜZ TASARIMI ---
st.title("🏃 GKD Bilimsel Performans Analiz Portalı")
st.markdown("Öğrenci verilerini girin, grup ortalamalarıyla kıyaslayın ve bilimsel rapor oluşturun.")

with st.sidebar:
    st.header("Sistem Bilgisi")
    st.info("Bu uygulama çoklu bilgisayar kullanımı için Streamlit Cloud üzerinde yayınlanmaya uygundur.")
    if st.button("Tüm Veri Tabanını Sıfırla"):
        st.session_state.db = pd.DataFrame()
        st.rerun()

# --- 4. VERİ GİRİŞ FORMU ---
with st.form("ana_form"):
    st.subheader("📋 1. Öğrenci Tanımlayıcı Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad = st.text_input("Ad")
        soyad = st.text_input("Soyad")
        dogum = st.date_input("Doğum Tarihi", min_value=datetime(1990, 1, 1))
    with c2:
        kilo = st.number_input("Kilo (kg)", format="%.2f")
        boy = st.number_input("Boy (cm)", format="%.1f")
        antrenman_baslama = st.date_input("Antrenmana Başlama Tarihi")
    with c3:
        ayak = st.selectbox("Tercih Edilen Ayak", ["Sağ", "Sol"])
        el = st.selectbox("Tercih Edilen El", ["Sağ", "Sol"])

    st.divider()
    st.subheader("⏱️ 2. Performans Testleri (2 Deneme)")
    
    # Test konfigürasyonu: (İsim, Değerlendirme Tipi)
    test_konfig = {
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
    cols = st.columns(4)
    for i, (t_ad, mod) in enumerate(test_konfig.items()):
        with cols[i % 4]:
            st.markdown(f"**{t_ad}**")
            d1 = st.number_input(f"1. Deneme", key=f"{t_ad}_d1", format="%.2f")
            d2 = st.number_input(f"2. Deneme", key=f"{t_ad}_d2", format="%.2f")
            
            # En iyi skoru belirle
            if d1 > 0 and d2 > 0:
                best = min(d1, d2) if mod == "min" else max(d1, d2)
            else:
                best = max(d1, d2) # Biri girilmemişse girilen değeri al
            test_sonuclari[t_ad] = best

    submit = st.form_submit_button("VERİLERİ ANALİZ ET VE KAYDET", use_container_width=True)

# --- 5. HESAPLAMA VE ANALİZ ---
if submit:
    if not ad or not soyad:
        st.error("Hata: Ad ve Soyad alanları boş bırakılamaz!")
    else:
        # Mevcut öğrenci verisi
        yeni_kayit = {
            "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo,
            "Dogum": dogum.strftime("%d.%m.%Y"),
            "Baslama": antrenman_baslama.strftime("%d.%m.%Y"),
            "Ayak": ayak, "El": el,
            "Kayit_Tarihi": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        yeni_kayit.update(test_sonuclari)
        
        # Veri tabanına ekle
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([yeni_kayit])], ignore_index=True)
        
        # Bilimsel Analizler (Grup Ortalaması, Std Sapma, Z-Skor)
        analiz_ozet = []
        for t_ad in test_konfig.keys():
            grup_verisi = st.session_state.db[t_ad]
            ort = grup_verisi.mean()
            std = grup_verisi.std() if len(grup_verisi) > 1 else 0
            
            # Z-Skoru: (Skor - Ortalama) / Std Sapma
            z = (test_sonuclari[t_ad] - ort) / std if std > 0 else 0
            
            analiz_ozet.append({
                "Test": t_ad,
                "Skor": test_sonuclari[t_ad],
                "Grup Ort.": round(ort, 2),
                "Std. Sapma": round(std, 2),
                "Z-Skor": round(z, 2)
            })

        st.success("Analiz tamamlandı! Aşağıdaki sonuçları inceleyebilir ve PDF raporu indirebilirsiniz.")

        # --- 6. GÖRSELLEŞTİRME ---
        tab1, tab2 = st.tabs(["📊 Karşılaştırma Grafikleri", "📋 Detaylı Tablo"])
        
        with tab1:
            fig, axes = plt.subplots(4, 2, figsize=(12, 18))
            axes = axes.flatten()
            for idx, a in enumerate(analiz_ozet):
                axes[idx].bar(['Öğrenci', 'Grup Ort.'], [a['Skor'], a['Grup Ort.']], color=['#1a237e', '#cfd8dc'])
                axes[idx].set_title(a['Test'], fontweight='bold')
                axes[idx].grid(axis='y', alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)

        with tab2:
            st.table(pd.DataFrame(analiz_ozet))

        # --- 7. PDF ÜRETİMİ ---
        def pdf_olustur():
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            w, h = A4
            
            # Sayfa 1: Kimlik Bilgileri
            p.setFillColor(colors.HexColor("#1a237e"))
            p.rect(0, h-100, w, 100, fill=1)
            p.setFillColor(colors.white)
            p.setFont(FONT_NAME, 22)
            p.drawCentredString(w/2, h-60, "PERFORMANS ANALİZ RAPORU")
            
            p.setFillColor(colors.black)
            p.setFont(FONT_NAME, 14)
            p.drawString(50, h-140, "1. SPORCU TANIMLAYICI BİLGİLERİ")
            p.line(50, h-145, 545, h-145)
            
            p.setFont(FONT_NAME, 11)
            p.drawString(60, h-170, f"Ad Soyad: {ad} {soyad}")
            p.drawString(60, h-190, f"Doğum Tarihi: {dogum.strftime('%d.%m.%Y')}")
            p.drawString(60, h-210, f"Boy / Kilo: {boy} cm / {kilo} kg")
            p.drawString(60, h-230, f"Tercih: {ayak} Ayak / {el} El")
            p.drawString(60, h-250, f"Antrenman Başlama: {antrenman_baslama.strftime('%d.%m.%Y')}")
            
            # Sayfa 1: Tablo
            p.setFont(FONT_NAME, 14)
            p.drawString(50, h-300, "2. TEST SKORLARI VE İSTATİSTİKSEL ANALİZ")
            p.line(50, h-305, 545, h-305)
            
            y = h-330
            p.setFont(FONT_NAME, 9)
            p.drawString(55, y, "TEST ADI")
            p.drawString(200, y, "SKOR")
            p.drawString(280, y, "ORT.")
            p.drawString(360, y, "STD. SAPMA")
            p.drawString(450, y, "Z-SKOR")
            
            p.setFont(FONT_NAME, 9)
            y -= 20
            for r in analiz_ozet:
                p.drawString(55, y, r['Test'])
                p.drawString(200, y, str(r['Skor']))
                p.drawString(280, y, str(r['Grup Ort.']))
                p.drawString(360, y, str(r['Std. Sapma']))
                p.drawString(450, y, str(r['Z-Skor']))
                y -= 20
                
            p.showPage() # Grafikler için yeni sayfa
            
            # Sayfa 2: Grafikler (Matplotlib'den aktar)
            img_data = io.BytesIO()
            fig.savefig(img_data, format='png', dpi=150)
            img_data.seek(0)
            p.drawImage(io.BytesIO(img_data.read()), 40, 50, width=520, preserveAspectRatio=True)
            
            p.save()
            buffer.seek(0)
            return buffer

        pdf_raw = pdf_olustur()
        st.download_button(
            label="📥 Profesyonel PDF Raporu İndir",
            data=pdf_raw,
            file_name=f"{ad}_{soyad}_Performans_Raporu.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- ALT BİLGİ ---
st.divider()
st.caption("GKD Bilimsel Analiz Modülü | v7.0 Final | Türkçe Karakter ve Çoklu Kullanıcı Uyumluluğu")
