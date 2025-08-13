def generate_rekomendasi(umur, berat, pakan, suhu):
    rekomendasi = []

    # Suhu Lingkungan
    if suhu < 20:
        rekomendasi.append("🌡️ Suhu lingkungan terlalu dingin (< 20°C). Tambahkan jerami untuk insulasi dan tutup celah angin agar sapi tetap hangat dan tidak stres.")
    elif 20 <= suhu <= 25:
        rekomendasi.append("🌡️ Suhu lingkungan ideal (20°C – 25°C). Pertahankan kondisi ini untuk kenyamanan dan produksi susu yang optimal.")
    elif 26 <= suhu <= 28:
        rekomendasi.append("🌡️ Suhu lingkungan cukup panas (26°C – 28°C). Tingkatkan ventilasi dan siram lantai serta tubuh sapi 2 kali sehari (pagi & siang) untuk menjaga suhu tubuh.")
    elif 29 <= suhu <= 31:
        rekomendasi.append("🌡️ Suhu lingkungan panas (29°C – 31°C). Siram lantai dan tubuh sapi 3 kali sehari (pagi, siang, sore) dan pastikan ventilasi maksimal.")
    elif 32 <= suhu <= 34:
        rekomendasi.append("🌡️ Suhu lingkungan sangat panas (32°C – 34°C). Siram lantai dan tubuh sapi 4 kali sehari (pagi, siang, sore, malam) dan tingkatkan ventilasi.")
    else:  # suhu > 34
        rekomendasi.append("🌡️ Suhu lingkungan ekstrem (> 34°C). Siram lantai dan tubuh sapi setiap 2–3 jam, terutama siang hari, dan pastikan ventilasi terbuka maksimal untuk menghindari stres panas.")

    # Umur dan pakan
    if umur < 1:
        rekomendasi.append("🥬 Sapi masih terlalu muda, belum siap untuk produksi susu.")
    elif 1 <= umur < 2:
        if pakan < 20:
            rekomendasi.append("🥬 Tambah jumlah pakan. Usia 1–2 tahun butuh minimal 20 kg pakan per hari.")
        elif pakan > 25:
            rekomendasi.append("🥬 Kurangi sedikit pakan. Untuk usia 1–2 tahun, maksimal 25 kg per hari sudah cukup.")
        else:
            rekomendasi.append("🥬 Jumlah pakan sudah pas untuk usia 1–2 tahun.")
    elif 2 <= umur <= 4:
        if pakan < 30:
            rekomendasi.append("🥬 Tambah pakan. Usia 2–4 tahun butuh minimal 30 kg per hari.")
        elif pakan > 40:
            rekomendasi.append("🥬 Pakan terlalu banyak. Cukup 30–40 kg per hari untuk usia ini.")
        else:
            rekomendasi.append("🥬 Pemberian pakan sudah tepat untuk usia 2–4 tahun.")
    else:
        if pakan < 30:
            rekomendasi.append("🥬 Untuk sapi dewasa, tambahkan pakan minimal 30 kg per hari.")
        elif pakan > 40:
            rekomendasi.append("🥬 Kurangi sedikit pakan. 30–40 kg per hari cukup untuk sapi dewasa.")
        else:
            rekomendasi.append("🥬 Jumlah pakan sudah sesuai untuk sapi dewasa.")

    # Umur produktif
    if umur < 2:
        rekomendasi.append("🐮 Sapi masih terlalu muda untuk produksi susu. Umumnya mulai produktif setelah usia 2 tahun.")
    elif 2 <= umur < 3:
        rekomendasi.append("🐮 Sapi baru mulai masa produksi. Jaga kondisi tubuh agar produksi stabil.")
    elif 3 <= umur <= 5:
        rekomendasi.append("🐮 Sapi berada di masa produksi puncak. Pertahankan kualitas pakan dan perawatan.")
    elif 6 <= umur <= 8:
        rekomendasi.append("🐮 Sapi mulai memasuki masa tua. Produksi bisa menurun, pastikan kesehatannya terjaga.")
    else:
        rekomendasi.append("🐮 Sapi sudah tua. Produksi susu cenderung rendah, perhatikan pola makan dan kesehatan.")

    # Berat badan
    if berat < 350:
        rekomendasi.append("⚖️ Berat badan terlalu ringan. Tingkatkan nutrisi pakan agar berat ideal.")
    elif berat > 600:
        rekomendasi.append("⚖️ Berat badan terlalu berat. Kontrol pakan agar tidak obesitas.")
    else:
        rekomendasi.append("⚖️ Berat badan sapi sudah ideal, pertahankan pola makan dan perawatan.")

    return rekomendasi
