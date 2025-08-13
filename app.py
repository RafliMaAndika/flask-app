# app.py
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from config import Config
from models.predictor import MilkPredictor
from models.history import HistoryManager
from utils.validator import generate_rekomendasi
from utils.preprocessing import preprocess_data   # harus mengembalikan (df, highlight_mask, steps_log)
import os
import pandas as pd
from io import StringIO

app = Flask(__name__)
app.config.from_object(Config)


class MilkPredictionApp:
    def __init__(self):
        self.data_path = None
        self.predictor = None
        self.history_manager = HistoryManager()
        self.sapi_info = []

    # helper internal: normalisasi nama kolom supaya konsisten
    @staticmethod
    def _normalize_columns(cols):
        cols = pd.Index(cols).astype(str)
        cols = (
            cols.str.strip()
                 .str.lower()
                 .str.replace('/', '_per_', regex=False)
                 .str.replace(r'[()\[\],%]', '', regex=True)
                 .str.replace(r'\s+', '_', regex=True)
                 .str.replace(r'__+', '_', regex=True)
                 .str.strip('_')
        )
        return cols

    def load_sapi_info(self):
        """Load sapi info (kode sapi, umur, berat) from file, tolerant terhadap variasi nama kolom."""
        self.sapi_info = []
        if not self.data_path or not os.path.exists(self.data_path):
            return []

        # baca file
        try:
            df = pd.read_csv(self.data_path)
        except Exception:
            # coba encoding alternatif
            df = pd.read_csv(self.data_path, encoding='latin1')

        # normalisasi kolom sementara (tanpa mengganti df.columns permanen)
        normalized = {orig: norm for orig, norm in zip(df.columns, self._normalize_columns(df.columns))}
        # buat map dari nama normal -> original column name untuk mengambil nilai aslinya
        inv_map = {v: k for k, v in normalized.items()}

        # mapping nama yg dibutuhkan (alias)
        aliases = {
            'kode_sapi': ['kode_sapi', 'kode_sapi'],
            'umur': ['umur_(tahun)', 'umur'],
            'berat': ['berat_badan_kg', 'berat_badan', 'berat']
        }

        # jika kolom-kolom yang diperlukan ada, isi sapi_info
        if 'kode_sapi' not in inv_map or not ({'umur_(tahun)', 'berat_badan_kg'} & set(inv_map.keys())):
            # kalau tidak sesuai format, kosongkan
            self.sapi_info = []
            return []

        # # gunakan kolom original dari inv_map (fallback jika nama bervariasi)
        # kode_col = inv_map.get('kode_sapi')
        # # umur dapat dari kemungkinan nama umur_(tahun) atau umur
        # umur_col = inv_map.get('umur_(tahun)') or inv_map.get('umur')
        # berat_col = inv_map.get('berat_badan_kg') or inv_map.get('berat_badan') or inv_map.get('berat')

        ########################## Start Modified Area ############################

        kode_col = inv_map.get('kode_sapi') or next((v for k,v in inv_map.items() if 'kode' in k), None)
        umur_col = inv_map.get('umur_(tahun)') or inv_map.get('umur') or next((v for k,v in inv_map.items() if 'umur' in k), None)
        berat_col = inv_map.get('berat_badan_kg') or inv_map.get('berat_badan') or inv_map.get('berat') or next((v for k,v in inv_map.items() if 'berat' in k), None)

        ########################## End Modified Area ############################

        if not kode_col or not umur_col or not berat_col:
            self.sapi_info = []
            return []

        # drop duplicates by kode sapi and extract
        try:
            unique_rows = df.drop_duplicates(kode_col)
        except Exception:
            unique_rows = df

        result = []
        for _, row in unique_rows.iterrows():
            try:
                result.append({
                    'kode': row[kode_col],
                    'umur': row[umur_col],
                    'berat': row[berat_col]
                })
            except Exception:
                continue

        self.sapi_info = result
        return self.sapi_info

    def get_sapi_by_kode(self, kode_sapi):
        return next((s for s in self.sapi_info if str(s.get('kode')) == str(kode_sapi)), None)


app_state = MilkPredictionApp()


@app.route('/')
def index():
    if not app_state.data_path or not os.path.exists(app_state.data_path):
        flash("Silakan upload dataset.")
        return redirect(url_for('upload_file'))

    df = pd.read_csv(app_state.data_path)

    if app_state.predictor is None:
        app_state.predictor = MilkPredictor(app_state.data_path)

    app_state.load_sapi_info()

    # ambil nama kolom asli kode sapi jika ada, fallback ke 'kode sapi'
    kode_col = None
    cols_norm = MilkPredictionApp._normalize_columns(df.columns)
    if 'kode_sapi' in cols_norm:
        kode_col = df.columns[list(cols_norm).index('kode_sapi')]
    else:
        # fallback: cari kolom yang mengandung 'kode'
        for c in df.columns:
            if 'kode' in c.lower():
                kode_col = c
                break

    kode_sapi = sorted(df[kode_col].unique()) if kode_col else []
    return render_template("index.html",
                           kode_sapi_list=kode_sapi,
                           tanggal_valid=app_state.predictor.get_valid_dates(),
                           hasil=None,
                           rekomendasi=None)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('csvfile')
        if not file or file.filename.strip() == '':
            flash("⚠️ File tidak ditemukan.")
            return redirect(request.url)

        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in Config.ALLOWED_EXTENSIONS:
            flash("⚠️ Hanya file dengan ekstensi .csv yang diperbolehkan.")
            return redirect(request.url)

        filename = file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        try:
            # baca file (coba dua encoding umum)
            try:
                df = pd.read_csv(path)
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding='latin1')

            # normalisasi nama kolom untuk pengecekan
            normalized = MilkPredictionApp._normalize_columns(df.columns)
            normalized_set = set(normalized)

            # required columns versi human (sesuaikan dengan format file awal)
            required_columns_original = [
                'kode sapi', 'umur (tahun)', 'berat badan (kg)',
                'jumlah pakan (kg)', 'produksi susu/hari (liter)',
                'tanggal pemerahan'
            ]
            # normalisasikan required untuk pengecekan
            required_normalized = set(pd.Index(required_columns_original)
                                      .str.strip()
                                      .str.lower()
                                      .str.replace('/', '_per_', regex=False)
                                      .str.replace(r'[()\[\],%]', '', regex=True)
                                      .str.replace(r'\s+', '_', regex=True)
                                      .str.replace(r'__+', '_', regex=True)
                                      .str.strip('_'))

            missing = required_normalized - set(normalized)
            if missing:
                # tak perlu hapus file kalau mau debugging, tapi kita hapus untuk kebersihan
                os.remove(path)
                flash(f"❌ File tidak valid. Kolom berikut hilang: {', '.join(sorted(missing))}")
                return redirect(request.url)

            # simpan path & preview df untuk diproses di /preview
            app_state.data_path = path
            app_state.df_preview = df
            app_state.predictor = MilkPredictor(path)
            app_state.load_sapi_info()

            flash(f"✅ File {filename} berhasil diunggah dan divalidasi.")
            return redirect(url_for('index'))

        except Exception as e:
            if os.path.exists(path):
                os.remove(path)
            flash(f"❌ Terjadi kesalahan saat membaca file: {e}")
            return redirect(request.url)

    return render_template('upload.html')


@app.route("/preview")
def preview():
    if not getattr(app_state, 'data_path', None):
        flash("Silakan upload dataset terlebih dahulu.")
        return redirect(url_for('upload_file'))

    try:
        # baca file asli
        try:
            df = pd.read_csv(app_state.data_path)
        except UnicodeDecodeError:
            df = pd.read_csv(app_state.data_path, encoding='latin1')

        # gunakan fungsi preprocessing dari utils.preprocessing
        processed_df, highlight_mask, steps_log = preprocess_data(df)

        # Buat styling: highlight hanya pada kolom numeric yang ada di highlight_mask
        # convert highlight_mask columns to present columns (if highlight_mask uses different names)
        numeric_cols = highlight_mask.columns.tolist()

        def highlight_col(col):
            return ['background-color: yellow' if highlight_mask.loc[i, col.name] else '' for i in col.index]

        # Terapkan styler hanya pada kolom yang ada di processed_df
        styled = processed_df.style.apply(lambda col: highlight_col(col) if col.name in numeric_cols else ['' for _ in col.index], axis=0)

        return render_template(
            "preview.html",
            tables=styled.to_html(),
            steps=steps_log
        )

    except Exception as e:
        flash(f"❌ Gagal memproses data: {e}")
        return redirect(url_for('upload_file'))


@app.route('/predict', methods=['POST'])
def predict():
    tanggal = request.form['tanggal_pemerahan']
    kode_sapi = request.form['kode_sapi']
    umur = float(request.form['umur'])
    berat = float(request.form['berat'])
    pakan = float(request.form['pakan'])
    suhu = float(request.form['suhu'])

    try:
        if not app_state.predictor:
            flash("Model belum tersedia. Silakan upload ulang dataset.")
            return redirect(url_for('index'))

        valid_dates = app_state.predictor.get_valid_dates()
        if tanggal not in valid_dates:
            flash("Tanggal tidak valid.")
            return redirect(url_for('index'))

        fitur = [pakan, suhu, umur, berat]
        hasil = app_state.predictor.train_and_predict(tanggal, fitur)
        rekomendasi = generate_rekomendasi(umur, berat, pakan, suhu)

        app_state.history_manager.save({
            'Tanggal Pemerahan': tanggal,
            'Kode Sapi': kode_sapi,
            'Jumlah Pakan': pakan,
            'Suhu': suhu,
            'Umur': umur,
            'Berat Badan': berat,
            'Produksi Susu': hasil,
            'Rekomendasi': ' | '.join(rekomendasi)
        })

        df = pd.read_csv(app_state.data_path)
        return render_template("index.html",
                               hasil=hasil,
                               rekomendasi=rekomendasi,
                               kode_sapi_list=sorted(df['kode sapi'].unique()),
                               tanggal_valid=valid_dates
                               )
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}")
        return redirect(url_for('index'))


@app.route('/analisis')
def analisis():
    riwayat_df = app_state.history_manager.load()
    if riwayat_df.empty:
        return render_template("analisis.html", riwayat=None, koef=None)

    if not app_state.predictor:
        flash("Model belum tersedia untuk analisis.")
        return redirect(url_for('index'))

    model = app_state.predictor.get_analysis_model(riwayat_df)
    return render_template("analisis.html",
                           riwayat=riwayat_df.to_dict(orient='records'),
                           koef=model
                           )


@app.route('/hapus_riwayat/<int:index>', methods=['POST'])
def hapus(index):
    app_state.history_manager.delete(index)
    flash("Data berhasil dihapus.")
    return redirect(url_for('analisis'))


@app.route('/get_sapi_info', methods=['POST'])
def get_sapi_info():
    data = request.get_json()
    kode_sapi = data.get('kode_sapi')
    sapi = app_state.get_sapi_by_kode(kode_sapi)

    if sapi:
        return jsonify({
            'umur': float(sapi['umur']),
            'berat': float(sapi['berat'])
        })
    else:
        return jsonify({'umur': '', 'berat': ''}), 404

if __name__ == '__main__':
   app.run(debug=True)
