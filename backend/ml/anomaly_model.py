import joblib
import os
import pandas as pd
from feature_engineering import create_features, ALL_FEATURES

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models', 'anomaly_model.pkl')

class AnomalyModel:
    def __init__(self, model_path=MODEL_PATH):
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None
        
    def detect(self, record):
        if not self.model:
            raise FileNotFoundError("Model file not found. Train the model first.")
            
        if isinstance(record, dict):
            df = pd.DataFrame([record])
        else:
            df = record.copy()
            
        df = create_features(df)
        X = df[ALL_FEATURES]
        
        # Isolation forest returns 1 for inliers, -1 for outliers
        pred = self.model.predict(X)[0]
        score = self.model.decision_function(X)[0]
        
        return {
            "anomaly": bool(pred == -1),
            "score": float(score)
        }

def detect_anomaly(record):
    model = AnomalyModel()
    return model.detect(record)
