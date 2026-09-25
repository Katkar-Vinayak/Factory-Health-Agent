import joblib
import os
import pandas as pd
from feature_engineering import create_features, ALL_FEATURES

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models', 'failure_model.pkl')

class FailureModel:
    def __init__(self, model_path=MODEL_PATH):
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None
        
    def predict(self, record):
        if not self.model:
            raise FileNotFoundError("Model file not found. Train the model first.")
            
        if isinstance(record, dict):
            df = pd.DataFrame([record])
        else:
            df = record.copy()
            
        df = create_features(df)
        X = df[ALL_FEATURES]
        
        # RandomForest
        prob = self.model.predict_proba(X)[0][1] # Probability of class 1 (failure)
        pred = self.model.predict(X)[0]
        
        return {
            "failure_within_24h": bool(pred == 1),
            "probability": float(prob)
        }

def predict_failure(record):
    model = FailureModel()
    return model.predict(record)
