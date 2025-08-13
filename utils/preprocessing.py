import pandas as pd

def preprocess_data(df):
    """
    Mengembalikan:
      - df: dataframe hasil preprocessing (kolom baku)
      - highlight_mask: DataFrame boolean dengan kolom numeric yang menandai sel yg diubah karena outlier
      - steps_log: list string berisi ringkasan langkah (siap ditampilkan)
    """
    steps_log = []

    # --- 1) Normalisasi nama kolom (robust) ---
    original_cols = list(df.columns)
    cols = (
        df.columns
          .astype(str)
          .str.strip()
          .str.lower()
          # penting: ganti slash (/) dengan _per_ supaya 'susu/hari' -> 'susu_per_hari'
          .str.replace('/', '_per_', regex=False)
          .str.replace(r'[-–—]', '_', regex=True)        # hyphen -> underscore
          .str.replace(r'[()\[\],%]', '', regex=True)   # hapus tanda kurung, bracket, koma, persen
          .str.replace(r'\s+', '_', regex=True)         # spasi -> underscore
          .str.replace(r'__+', '_', regex=True)         # collapse double underscore
          .str.strip('_')
    )
    df.columns = cols
    steps_log.append("1) Normalisasi nama kolom (lowercase, spasi->_, '/'->_per_, hapus simbol).")
    steps_log.append(f"   Sebelumnya: {original_cols}")
    steps_log.append(f"   Sekarang  : {list(df.columns)}")

    # --- 2) Mapping alias ke nama baku (tambah alias jika perlu) ---
    col_map = {
        # identitas penting
        'kode_sapi': 'kode_sapi',
        'tanggal_pemerahan': 'tanggal_pemerahan',
        'tanggal_lahir': 'tanggal_lahir',

        # umur
        'umur': 'umur_tahun',
        'umur_(tahun)': 'umur_tahun',
        'umur_tahun': 'umur_tahun',

        # berat
        'berat_badan_kg': 'berat_badan_kg',
        'berat_badan': 'berat_badan_kg',
        'berat': 'berat_badan_kg',

        # pakan
        'jumlah_pakan_kg': 'jumlah_pakan_kg',
        'jumlah_pakan': 'jumlah_pakan_kg',
        'pakan': 'jumlah_pakan_kg',

        # suhu
        'rata_rata_suhu': 'rata_rata_suhu',
        'rata-rata_suhu': 'rata_rata_suhu',
        'suhu': 'rata_rata_suhu',

        # produksi (beberapa variasi)
        'produksi_susu_per_hari_liter': 'produksi_susu_per_hari_liter',
        'produksi_susu_hari_liter': 'produksi_susu_per_hari_liter',
        'produksi_susuhari_liter': 'produksi_susu_per_hari_liter',
        'produksi_susu': 'produksi_susu_per_hari_liter',
        # produksi pagi/sore (untuk fallback)
        'produksi_susu_pagi_liter': 'produksi_susu_pagi_liter',
        'produksi_susu_sore_liter': 'produksi_susu_sore_liter',
    }
    df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})
    steps_log.append("2) Mapping alias kolom ke nama baku (jika ada).")
    steps_log.append(f"   Nama kolom setelah mapping: {list(df.columns)}")

    # --- 3) Fallback: buat produksi_per_hari jika tidak ada tapi pagi+sore ada ---
    if 'produksi_susu_per_hari_liter' not in df.columns:
        if ('produksi_susu_pagi_liter' in df.columns) and ('produksi_susu_sore_liter' in df.columns):
            # pastikan numeric lalu jumlahkan
            df['produksi_susu_pagi_liter'] = pd.to_numeric(df['produksi_susu_pagi_liter'], errors='coerce')
            df['produksi_susu_sore_liter'] = pd.to_numeric(df['produksi_susu_sore_liter'], errors='coerce')
            df['produksi_susu_per_hari_liter'] = df['produksi_susu_pagi_liter'].fillna(0) + df['produksi_susu_sore_liter'].fillna(0)
            steps_log.append("3) Kolom 'produksi_susu_per_hari_liter' dibuat dari (pagi + sore).")
        else:
            # tidak bisa fallback — akan diperiksa di cek wajib
            steps_log.append("3) 'produksi_susu_per_hari_liter' tidak ditemukan dan tidak dapat dihitung (pagi/sore tidak lengkap).")

    # --- 4) Cek kolom wajib (setelah mapping & fallback) ---
    required_cols = [
        'kode_sapi', 'tanggal_pemerahan', 'tanggal_lahir', 'umur_tahun',
        'berat_badan_kg', 'jumlah_pakan_kg', 'rata_rata_suhu', 'produksi_susu_per_hari_liter'
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        # tampilkan kolom yang tersedia untuk debugging
        available = list(df.columns)
        raise ValueError(f"❌ Gagal memproses data: Kolom wajib hilang: {missing}. Kolom tersedia: {available}")

    steps_log.append("4) Semua kolom wajib tersedia (setelah mapping/fallback).")

    # --- 5) Hapus duplikat ---
    before = len(df)
    df = df.drop_duplicates()
    steps_log.append(f"5) Dihapus {before - len(df)} baris duplikat (jika ada).")

    # --- 6) Konversi tanggal ---
    df['tanggal_pemerahan'] = pd.to_datetime(df['tanggal_pemerahan'], errors='coerce')
    df['tanggal_lahir'] = pd.to_datetime(df['tanggal_lahir'], errors='coerce')
    steps_log.append("6) Konversi kolom tanggal ke datetime.")

    # --- 7) Hitung umur bila perlu ---
    df['umur_tahun'] = pd.to_numeric(df.get('umur_tahun'), errors='coerce')
    missing_age = df['umur_tahun'].isna().sum()
    if missing_age > 0:
        df['umur_tahun'] = (df['tanggal_pemerahan'] - df['tanggal_lahir']).dt.days // 365
        steps_log.append(f"7) Menghitung umur untuk {missing_age} baris yang kosong/invalid.")
    else:
        steps_log.append("7) Umur lengkap, tidak perlu dihitung ulang.")

    # --- 8) Konversi kolom numerik & hapus baris kosong pada wajib ---
    numeric_cols = ['umur_tahun', 'berat_badan_kg', 'jumlah_pakan_kg', 'rata_rata_suhu', 'produksi_susu_per_hari_liter']
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    before = len(df)
    df = df.dropna(subset=required_cols)
    steps_log.append(f"8) Dihapus {before - len(df)} baris karena nilai kosong pada kolom wajib.")

    # --- 9) Deteksi outlier (IQR) dan ganti dengan mean; buat highlight mask ---
    highlight_mask = pd.DataFrame(False, index=df.index, columns=numeric_cols)
    for col in numeric_cols:
        if df[col].empty:
            continue
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        mean_val = df[col].mean()
        mask = (df[col] < lower) | (df[col] > upper)
        highlight_mask[col] = mask
        df.loc[mask, col] = mean_val
        steps_log.append(f"9) {mask.sum()} outlier di '{col}' diganti dengan rata-rata ({mean_val:.2f}).")

    # --- 10) Reset index dan selesai ---
    df = df.reset_index(drop=True)
    steps_log.append("10) Reset index selesai.")

    return df, highlight_mask, steps_log
