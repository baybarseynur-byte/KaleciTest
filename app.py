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

# --- 1. SİSTEM AYARLARI VE FONT ---
st.set_page_config(page_title="GKD Akademik Performans Sistemi", layout="wide")

# Matplotlib Türkçe Karakter Desteği
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

def font_yukle():
    """PDF için Türkçe karakter destekli fontu yükler."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Sistemde arial.ttf olup olmadığını kontrol et (Streamlit Cloud genelde Helvetica kullanır)
    font_paths = ["arial.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for path in font_paths:
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
            df = pd.read_csv(DB_FILE, encoding='utf-16')
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def veri_kaydet_ve_guncelle(yeni_df):
    mevcut = veri_oku()
    if mevcut.empty:
        mevcut = yeni_df
    else:
        # ID bazlı veya İsim-Soyisim-Tarih bazlı güncelleme
        for _, row in yeni_df.iterrows():
            mask = (mevcut['ID'] == row['ID']) & (mevcut['Olcum_Tarihi'] == row['Olcum_Tarihi'])
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
    
    # Özel Stiller
    title_style = ParagraphStyle('TitleTr', fontName=FONT, fontSize=18, alignment=1, spaceAfter=20)
    head_style = ParagraphStyle('HeadTr', fontName=FONT, fontSize=12, spaceBefore=10, textColor=colors.navy)
    normal_style = ParagraphStyle('NormalTr', fontName=FONT, fontSize=10)

    akis = [Paragraph("BİREYSEL PERFORMANS VE GELİŞİM RAPORU", title_style)]
    
    # Künye Tablosu
    info_data = [
        [f"ID: {secilen.get('ID','')}", f"Grup (Çeyrek): {secilen.get('Ceyrek','')}"],
        [f"Ad Soyad: {secilen.get('Ad','')} {secilen.get('Soyad','')}", f"Ölçüm Tarihi: {secilen.get('Olcum_Tarihi','')}"],
        [f"Doğum Tarihi: {secilen.get('Dogum_Tarihi','')}", f"Başlama Tarihi: {secilen.get('Baslama_Tarihi','')}"],
        [f"Boy: {secilen.get('Boy','')} cm", f"Kilo: {secilen.get('Kilo','')} kg"]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 10)]))
    akis.append(info_table)
    akis.append(Spacer(1, 20))

    # Analiz Tablosu
    akis.append(Paragraph("Mevcut Ölçüm Verileri ve Akran Kıyaslaması", head_style))
    table_data = [["Test Adı", "Skor", "Grup Ort.", "Z-Skor", "Durum"]]
    for r in analiz_datalari:
        table_data.append([r['Test'], r['Skor'], r['Grup Ort.'], r['Z-Skor'], r['Durum']])
    
    t = Table(table_data, colWidths=[160, 60, 70, 60, 100])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), FONT),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    akis.append(t)
    akis.append(Spacer(1, 20))

    # GRAFİKLER
    akis.append(Paragraph("Performans Grafikleri", head_style))
    for r in analiz_datalari:
        test_adi = r['Test']
        plt.figure(figsize=(6, 3))
        
        sporcu_gecmis = tum_gecmis.sort_values('Olcum_Tarihi')
        
        if len(sporcu_gecmis) > 1:
            # Gelişim Çizgi Grafiği
            plt.plot(sporcu_gecmis['Olcum_Tarihi'], sporcu_gecmis[test_adi], marker='o', color='#1f77b4', linewidth=2)
            plt.title(f"{test_adi} - Zaman İçindeki Gelişim", fontsize=10)
            plt.xticks(rotation=45)
        else:
            # Akran Kıyaslama Barı
            z_skor = float(r['Z-Skor'])
            renk = 'green' if z_skor > 1 else ('red' if z_skor < -1 else 'gray')
            plt.barh(['Akran Ortalaması', 'Sporcu'], [0, z_skor], color=['gray', renk])
            plt.axvline(0, color='black', lw=1)
            plt.xlim(-3.5, 3.5)
            plt.title(f"{test_adi} - Akran Kıyaslama (Z-Skor)", fontsize=10)

        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=120)
        plt.close()
        akis.append(KeepTogether([Image(img_buf, width=420, height=180), Spacer(1, 10)]))

    doc.build(akis)
    buf.seek(0)
    return buf

# --- 4. ANA ARAYÜZ VE SİDEBAR ---
db = veri_oku()
secilen_profil = None

with st.sidebar:
    st.header("⚙️ Yönetim Paneli")
    
    # 1. Kayıtlı Sporcu Seçimi & Güncelleme
    if not db.empty and 'ID' in db.columns:
        db['Display'] = db['Ad'] + " " + db['Soyad'] + " (" + db['ID'] + ")"
        unique_students = db.drop_duplicates(subset=['ID'])
        secim = st.selectbox("Sporcu Düzenle", ["-- Yeni Kayıt --"] + unique_students['Display'].tolist())
        
        if secim != "-- Yeni Kayıt --":
            sid = secim.split("(")[-1].replace(")", "")
            secilen_profil = db[db['ID'] == sid].sort_values('Olcum_Tarihi', ascending=False).iloc[0]
            st.success(f"ID: {sid} yüklendi. Bilgileri aşağıdan güncelleyebilirsiniz.")

    st.divider()
    
    # 2. Excel ile Toplu Veri Yükleme
    st.subheader("📥 Toplu Veri Yükle")
    uploaded_file = st.file_uploader("Şablona uygun Excel/CSV seçin", type=['xlsx', 'csv'])
    if uploaded_file and st.button("Sisteme Aktar"):
        df_ext = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        if 'ID' not in df_ext.columns:
            df_ext['ID'] = [f"GKD-{uuid.uuid4().hex[:6].upper()}" for _ in range(len(df_ext))]
        veri_kaydet_ve_guncelle(df_ext)
        st.success("Veriler başarıyla aktarıldı!")
        st.rerun()

    # 3. Veritabanı İndirme
    if not db.empty:
        st.divider()
        towrite = io.BytesIO()
        db.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("📊 Tüm Veritabanını İndir (Excel)", towrite.getvalue(), "gkd_master_db.xlsx")

# --- 5. VERİ GİRİŞ FORMU ---
with st.form("main_form"):
    st.subheader("📋 Sporcu ve Ölçüm Bilgileri")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**Kimlik Bilgileri**")
        # Eğer profil seçiliyse ID'yi koru, yoksa yeni oluştur
        curr_id = st.text_input("Sporcu ID (Değiştirmeyin)", value=secilen_profil['ID'] if secilen_profil is not None else f"GKD-{uuid.uuid4().hex[:6].upper()}", help="Yeni kayıtta otomatik oluşturulur.")
        ad = st.text_input("Ad", value=secilen_profil['Ad'] if secilen_profil is not None else "")
        soyad = st.text_input("Soyad", value=secilen_profil['Soyad'] if secilen_profil is not None else "")
    
    with c2:
        st.markdown("**Tarih Bilgileri**")
        olcum_tarihi = st.date_input("Ölçüm Tarihi", value=datetime.now())
        v_dt = datetime.strptime(str(secilen_profil['Dogum_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2012, 1, 1)
        dogum = st.date_input("Doğum Tarihi", value=v_dt)
        v_bas = datetime.strptime(str(secilen_profil['Baslama_Tarihi']), '%Y-%m-%d') if secilen_profil is not None else datetime(2020, 1, 1)
        baslama = st.date_input("Antrenman Başlama Tarihi", value=v_bas)

    with c3:
        st.markdown("**Fiziksel Veriler**")
        boy = st.number_input("Boy (cm)", value=float(secilen_profil['Boy']) if secilen_profil is not None else 160.0)
        kilo = st.number_input("Kilo (kg)", value=float(secilen_profil['Kilo']) if secilen_profil is not None else 50.0)

    st.divider()
    st.markdown("**Performans Testleri**")
    test_specs = {
        "5m Sprint (sn)": "min", "10m Sprint (sn)": "min", "20m Sprint (sn)": "min", 
        "Dikey Sıçrama (cm)": "max", "SKT Sağ (sn)": "min", "SKT Sol (sn)": "min"
    }
    
    test_inputs = {}
    t_cols = st.columns(2)
    for i, (t_ad, mod) in enumerate(test_specs.items()):
        with t_cols[i % 2]:
            v1 = float(secilen_profil[f"{t_ad}_D1"]) if secilen_profil is not None and f"{t_ad}_D1" in secilen_profil else 0.0
            v2 = float(secilen_profil[f"{t_ad}_D2"]) if secilen_profil is not None and f"{t_ad}_D2" in secilen_profil else 0.0
            d1 = st.number_input(f"{t_ad} Deneme 1", value=v1, format="%.3f")
            d2 = st.number_input(f"{t_ad} Deneme 2", value=v2, format="%.3f")
            best = (min(d1, d2) if d1 > 0 and d2 > 0 else max(d1, d2)) if mod == "min" else max(d1, d2)
            test_inputs[t_ad] = {"D1": d1, "D2": d2, "Best": best}

    if st.form_submit_button("💾 VERİLERİ KAYDET VE ANALİZ ET"):
        if ad and soyad:
            ceyrek = f"{dogum.year}_Q{(dogum.month-1)//3+1}"
            data_dict = {
                "ID": curr_id, "Ad": ad, "Soyad": soyad, 
                "Dogum_Tarihi": dogum.strftime('%Y-%m-%d'),
                "Baslama_Tarihi": baslama.strftime('%Y-%m-%d'),
                "Olcum_Tarihi": olcum_tarihi.strftime('%Y-%m-%d'),
                "Boy": boy, "Kilo": kilo, "Ceyrek": ceyrek
            }
            for t_ad, vals in test_inputs.items():
                data_dict[f"{t_ad}_D1"] = vals["D1"]
                data_dict[f"{t_ad}_D2"] = vals["D2"]
                data_dict[t_ad] = vals["Best"]
            
            veri_kaydet_ve_guncelle(pd.DataFrame([data_dict]))
            st.success("İşlem Başarılı! Veritabanı güncellendi.")
            st.rerun()

# --- 6. ANALİZ VE RAPORLAMA ---
if secilen_profil is not None:
    st.divider()
    st.header(f"📈 Analiz Paneli: {secilen_profil['Ad']} {secilen_profil['Soyad']}")
    
    # Akran Grubu Analizi
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
            analiz_datalari.append({
                "Test": t_ad, "Skor": f"{skor:.3f}", 
                "Grup Ort.": round(ort,3), "Z-Skor": z_f, "Durum": durum
            })

    if analiz_datalari:
        st.table(pd.DataFrame(analiz_datalari))
        
        # PDF Butonu
        sporcu_tum_gecmis = db[db['ID'] == secilen_profil['ID']]
        pdf_file = profesyonel_pdf_uret(secilen_profil, analiz_datalari, sporcu_tum_gecmis)
        st.download_button(
            label="📄 Profesyonel PDF Raporu İndir",
            data=pdf_file,
            file_name=f"GKD_Rapor_{secilen_profil['ID']}_{secilen_profil['Olcum_Tarihi']}.pdf",
            mime="application/pdf"
        )
