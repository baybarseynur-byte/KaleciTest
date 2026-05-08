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

# --- 1. SİSTEM VE FONT AYARLARI ---
st.set_page_config(page_title="GKD Araştırma ve Analiz Portalı", layout="wide")

def font_yukle():
    if os.path.exists("arial.ttf"):
        try:
            pdfmetrics.registerFont(TTFont('Arial_Tr', 'arial.ttf'))
            return "Arial_Tr"
        except: return "Helvetica"
    return "Helvetica"

FONT = font_yukle()

# --- 2. MERKEZİ VERİ YÖNETİMİ (ARAŞTIRMA İÇİN) ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()

# --- 3. ARAYÜZ ---
st.title("🔬 GKD Bilimsel Araştırma ve Performans Sistemi")
st.markdown("Veriler araştırma amaçlı toplu kullanım ve bireysel detaylı raporlama için işlenir.")

with st.form("gelismis_form"):
    st.subheader("👤 Öğrenci Kimlik Bilgileri")
    c1, c2, c3 = st.columns(3)
    with c1:
        ad, soyad = st.text_input("Ad"), st.text_input("Soyad")
        dogum = st.date_input("Doğum Tarihi", min_value=datetime(1990, 1, 1))
    with c2:
        kilo, boy = st.number_input("Kilo (kg)"), st.number_input("Boy (cm)")
        ant_baslama = st.date_input("Antrenman Başlama Tarihi")
    with c3:
        ayak = st.selectbox("Ayak", ["Sağ", "Sol"])
        el = st.selectbox("El", ["Sağ", "Sol"])

    st.divider()
    st.subheader("📊 Test Verileri (Denemeler)")
    
    test_yapisi = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min",
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min",
        "LSKT Sağ (sn)": "min", "LSKT Sol (sn)": "min"
    }

    raw_data = {}
    cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_yapisi.items()):
        with cols[i % 2]:
            st.write(f"**{t_ad}**")
            d1 = st.number_input("1. Deneme", key=f"{t_ad}_d1", format="%.3f")
            d2 = st.number_input("2. Deneme", key=f"{t_ad}_d2", format="%.3f")
            best = (min(d1, d2) if d1>0 and d2>0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            raw_data[t_ad] = {"d1": d1, "d2": d2, "best": best}

    submit = st.form_submit_button("ANALİZ ET VE VERİ TABANINA İŞLE")

if submit:
    # Veri Kaydı (Araştırma Amaçlı Tüm Detaylar)
    yeni_kayit = {
        "Ad": ad, "Soyad": soyad, "Boy": boy, "Kilo": kilo, "Ayak": ayak, "El": el,
        "Kayit": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    for t, v in raw_data.items():
        yeni_kayit[f"{t}_D1"] = v['d1']
        yeni_kayit[f"{t}_D2"] = v['d2']
        yeni_kayit[t] = v['best']
    
    st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([yeni_kayit])], ignore_index=True)
    
    # İstatistiksel Hesaplamalar
    istatistikler = []
    for t_ad in test_yapisi.keys():
        seri = st.session_state.db[t_ad]
        ort, std = seri.mean(), (seri.std() if len(seri)>1 else 0)
        en_iyi = seri.min() if test_yapisi[t_ad] == "min" else seri.max()
        en_kotu = seri.max() if test_yapisi[t_ad] == "min" else seri.min()
        z = (raw_data[t_ad]['best'] - ort) / std if std > 0 else 0
        
        istatistikler.append({
            "Test": t_ad, "Skor": raw_data[t_ad]['best'], "Ort": round(ort,3), 
            "Std": round(std,3), "Z": round(z,2), "Grup En İyi": en_iyi, "Grup En Kötü": en_kotu
        })

    st.success("Veri başarıyla işlendi ve grup istatistikleri güncellendi.")
    st.dataframe(pd.DataFrame(istatistikler))

    # --- PDF OLUŞTURMA (Her Test Ayrı Grafik ve Geniş Tablo) ---
    def generate_detailed_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        w, h = A4
        
        # Kapak ve Bilgiler
        c.setFont(FONT, 16); c.drawString(50, h-50, "BİREYSEL PERFORMANS ANALİZ RAPORU")
        c.setFont(FONT, 10); c.drawString(50, h-80, f"Sporcu: {ad} {soyad} | Boy: {boy} | Kilo: {kilo} | Tarih: {datetime.now().strftime('%d.%m.%Y')}")
        c.line(50, h-90, 545, h-90)

        curr_y = h - 120
        for i, stat in enumerate(istatistikler):
            if curr_y < 250: # Yeni sayfa kontrolü
                c.showPage(); curr_y = h - 50
            
            # Test Başlığı ve Verileri
            c.setFont(FONT + "-Bold" if "Helvetica" not in FONT else "Helvetica-Bold", 11)
            c.drawString(50, curr_y, f"TEST: {stat['Test']}")
            c.setFont(FONT, 9)
            curr_y -= 15
            info_str = f"Skor: {stat['Skor']} | Ort: {stat['Ort']} | Z-Skor: {stat['Z']} | Grup En İyi: {stat['Grup En İyi']} | Grup En Kötü: {stat['Grup En Kötü']}"
            c.drawString(60, curr_y, info_str)
            
            # Her Test İçin Ayrı Grafik
            plt.figure(figsize=(4, 2))
            plt.barh(['Grup En Kötü', 'Grup Ort.', 'Sporcu', 'Grup En İyi'], 
                     [stat['Grup En Kötü'], stat['Ort'], stat['Skor'], stat['Grup En İyi']], 
                     color=['red', 'gray', 'blue', 'green'])
            plt.tight_layout()
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=100)
            plt.close()
            
            curr_y -= 110
            c.drawImage(io.BytesIO(img_buf.getvalue()), 60, curr_y, width=300, preserveAspectRatio=True)
            curr_y -= 40
            c.line(50, curr_y, 500, curr_y)
            curr_y -= 30

        c.save()
        buffer.seek(0)
        return buffer

    st.download_button("📄 Detaylı Raporu İndir (Grafik + Geniş Tablo)", generate_detailed_pdf(), f"{ad}_{soyad}_Detayli.pdf")

# --- ARAŞTIRMA İÇİN TOPLU VERİ İNDİRME ---
st.sidebar.divider()
st.sidebar.subheader("🔬 Araştırmacı Paneli")
if not st.session_state.db.empty:
    csv = st.session_state.db.to_csv(index=False).encode('utf-16')
    st.sidebar.download_button("Excel/SPSS İçin Toplu Veriyi İndir", csv, "arastirma_verisi.csv", "text/csv")        "10m Sprint (sn)": "min",
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
