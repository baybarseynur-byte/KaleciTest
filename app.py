# --- 4. GÜNCELLENMİŞ PDF MOTORU ---
def pdf_olustur(secilen, analiz_datalari, tum_gecmis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    baslik_stil = ParagraphStyle('Baslik', fontName=SECILEN_FONT, fontSize=18, alignment=1, spaceAfter=20)
    normal_stil = ParagraphStyle('Normal', fontName=SECILEN_FONT, fontSize=10, leading=12)
    
    akis = [Paragraph("<b>BİREYSEL PERFORMANS VE GELİŞİM RAPORU</b>", baslik_stil)]
    
    # Üst Künye Bilgileri
    info = [
        [Paragraph(f"<b>ID:</b> {secilen['ID']}", normal_stil), Paragraph(f"<b>Grup:</b> {secilen['Ceyrek']}", normal_stil)],
        [Paragraph(f"<b>Ad Soyad:</b> {secilen['Ad']} {secilen['Soyad']}", normal_stil), Paragraph(f"<b>Tarih:</b> {secilen['Olcum_Tarihi']}", normal_stil)],
        [Paragraph(f"<b>Boy/Kilo:</b> {secilen['Boy']}cm / {secilen['Kilo']}kg", normal_stil), Paragraph(f"<b>Hesaplanan Peak Power:</b> {secilen.get('Peak Power (W)', 0)} W", normal_stil)]
    ]
    t_info = Table(info, colWidths=[240, 240])
    t_info.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), SECILEN_FONT), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    akis.append(t_info)
    akis.append(Spacer(1, 15))

    # --- TABLO BÖLÜMÜ: Peak Power artık burada bir satır olarak yer alır ---
    tablo_verisi = [[Paragraph(f"<b>{h}</b>", normal_stil) for h in ["Test Adı", "Skor", "Ort.", "Z-Skor", "Durum"]]]
    
    for r in analiz_datalari:
        durum_temiz = str(r['Durum']).replace("🌟", "").replace("✅", "").replace("⚪", "").replace("🆘", "").strip()
        dur_renk = colors.red if "KRİTİK" in durum_temiz else (colors.darkgreen if "ELİT" in durum_temiz else colors.black)
        durum_stili = ParagraphStyle('DStil', fontName=SECILEN_FONT, fontSize=10, textColor=dur_renk, alignment=1)

        tablo_verisi.append([
            Paragraph(str(r['Test']), normal_stil),
            Paragraph(str(r['Skor']), normal_stil),
            Paragraph(str(r['Grup Ort.']), normal_stil),
            Paragraph(str(r['Z-Skor']), normal_stil),
            Paragraph(f"<b>{durum_temiz}</b>", durum_stili)
        ])
    
    t_analiz = Table(tablo_verisi, colWidths=[150, 60, 70, 60, 100])
    t_analiz.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), SECILEN_FONT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    akis.append(t_analiz)

    # --- GRAFİKLER BÖLÜMÜ: Peak Power grafiği dahil tüm testler ---
    akis.append(Spacer(1, 20))
    for r in analiz_datalari:
        test_adi = r['Test']
        # tum_gecmis içinde bu testin sütunu varsa grafiği çiz
        if test_adi in tum_gecmis.columns:
            fig, ax = plt.subplots(figsize=(6, 2.5))
            # Türkçe karakter desteği için font ayarı
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
            
            # Zaman serisi verisini hazırla
            gecmis_verisi = tum_gecmis.sort_values('Olcum_Tarihi')
            
            # Grafiği çiz
            ax.plot(gecmis_verisi['Olcum_Tarihi'], gecmis_verisi[test_adi], 
                    marker='o', linestyle='-', color='#1f77b4', lw=2.5, markersize=6)
            
            # Başlık ve Etiketler
            ax.set_title(f"{test_adi} - Gelişim Analizi", fontsize=11, fontweight='bold')
            ax.set_ylabel("Skor / Değer")
            ax.grid(True, linestyle='--', alpha=0.6)
            plt.xticks(rotation=15)
            
            plt.tight_layout()
            
            # Resmi PDF'e aktar
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=120)
            plt.close(fig)
            
            akis.append(KeepTogether([
                Spacer(1, 10), 
                Image(img_buf, width=440, height=180),
                Spacer(1, 10)
            ]))

    doc.build(akis)
    buf.seek(0)
    return buf
