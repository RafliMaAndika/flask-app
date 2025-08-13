import pandas as pd
import os
from config import Config

class HistoryManager:
    def __init__(self):
        self.path = Config.RIWAYAT_PATH

    def load(self):
        if not os.path.exists(self.path):
            return pd.DataFrame()
        return pd.read_csv(self.path)

    def save(self, data):
        df = self.load()
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_csv(self.path, index=False)

    def delete(self, index):
        df = self.load()
        if 0 <= index < len(df):
            df = df.drop(index).reset_index(drop=True)
            df.to_csv(self.path, index=False)
