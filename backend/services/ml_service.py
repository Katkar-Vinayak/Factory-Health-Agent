import sys
import os
from pathlib import Path

# Add the ml directory to the path so we can import from it
ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml')
if ML_DIR not in sys.path:
    sys.path.append(ML_DIR)

from anomaly_model import AnomalyModel
from failure_model import FailureModel

class MLService:
    def __init__(self):
        self.anomaly_model_path = os.path.join(ML_DIR, 'saved_models', 'anomaly_model.pkl')
        self.failure_model_path = os.path.join(ML_DIR, 'saved_models', 'failure_model.pkl')
        self.anomaly_mtime = None
        self.failure_mtime = None
        self.anomaly_model = None
        self.failure_model = None
        self._load_models()

    def _load_models(self):
        if os.path.exists(self.anomaly_model_path):
            self.anomaly_mtime = os.path.getmtime(self.anomaly_model_path)
            self.anomaly_model = AnomalyModel(self.anomaly_model_path)
        if os.path.exists(self.failure_model_path):
            self.failure_mtime = os.path.getmtime(self.failure_model_path)
            self.failure_model = FailureModel(self.failure_model_path)

    def _ensure_latest_models(self):
        if os.path.exists(self.anomaly_model_path):
            current_anom_mtime = os.path.getmtime(self.anomaly_model_path)
            if self.anomaly_mtime != current_anom_mtime:
                self.anomaly_mtime = current_anom_mtime
                self.anomaly_model = AnomalyModel(self.anomaly_model_path)

        if os.path.exists(self.failure_model_path):
            current_fail_mtime = os.path.getmtime(self.failure_model_path)
            if self.failure_mtime != current_fail_mtime:
                self.failure_mtime = current_fail_mtime
                self.failure_model = FailureModel(self.failure_model_path)

    def analyze_machine(self, record: dict) -> dict:
        """
        Accepts a machine sensor record (dict)
        Returns anomaly prediction, score, and failure prediction/probability.
        """
        self._ensure_latest_models()
        anom_res = self.anomaly_model.detect(record)
        fail_res = self.failure_model.predict(record)
        
        return {
            "machine_id": record.get("machine_id", "Unknown"),
            "anomaly": anom_res["anomaly"],
            "anomaly_score": anom_res["score"],
            "failure_within_24h": fail_res["failure_within_24h"],
            "failure_probability": fail_res["probability"]
        }

# Instantiate a single global instance so models are loaded once
ml_service_instance = MLService()

def analyze_machine(record: dict) -> dict:
    return ml_service_instance.analyze_machine(record)

