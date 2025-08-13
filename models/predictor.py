import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import timedelta
import os

class MilkPredictor:
    def __init__(self, data_path):
        self.data_path = data_path
        self.model = LinearRegression()

    def _load_data(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError("Dataset belum diunggah.")
        df = pd.read_csv(self.data_path)
        df['tanggal pemerahan'] = pd.to_datetime(df['tanggal pemerahan'])
        return df

    def get_valid_dates(self):
        df = self._load_data()
        tanggal_akhir = df['tanggal pemerahan'].max()
        tanggal_awal = df['tanggal pemerahan'].min()

        tanggal_prediksi_mulai = tanggal_awal + timedelta(days=14)
        tanggal_prediksi_akhir = tanggal_akhir + timedelta(days=1)

        valid_dates = []
        while tanggal_prediksi_mulai <= tanggal_prediksi_akhir:
            window = df[(df['tanggal pemerahan'] >= tanggal_prediksi_mulai - timedelta(days=14)) &
                        (df['tanggal pemerahan'] < tanggal_prediksi_mulai)]
            if window.shape[0] >= 14:
                valid_dates.append(tanggal_prediksi_mulai.strftime('%Y-%m-%d'))
            tanggal_prediksi_mulai += timedelta(days=1)

        return valid_dates

    def train_and_predict(self, tanggal_prediksi, fitur):
        df = self._load_data()
        tanggal_prediksi = pd.to_datetime(tanggal_prediksi)
        window = df[(df['tanggal pemerahan'] >= tanggal_prediksi - timedelta(days=14)) &
                    (df['tanggal pemerahan'] < tanggal_prediksi)]
        if window.shape[0] < 14:
            raise ValueError("Data kurang dari 14 hari untuk prediksi.")

        X = window[['jumlah pakan (kg)', 'Rata-rata Suhu', 'umur (tahun)', 'berat badan (kg)']]
        y = window[['produksi susu/hari (liter)']]
        self.model.fit(X, y)
        return round(self.model.predict([fitur])[0][0], 2)

    def get_analysis_model(self, riwayat_df):
        X = riwayat_df[['Jumlah Pakan', 'Suhu', 'Umur', 'Berat Badan']]
        y = riwayat_df[['Produksi Susu']]
        self.model.fit(X, y)
        return {
            'b0': self.model.intercept_[0],
            'b1': self.model.coef_[0][0],
            'b2': self.model.coef_[0][1],
            'b3': self.model.coef_[0][2],
            'b4': self.model.coef_[0][3]
        }
