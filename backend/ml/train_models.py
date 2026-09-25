import pandas as pd
import numpy as np
import os
import joblib
import sys
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import create_features, ALL_FEATURES

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'sensor_data.csv')
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')

os.makedirs(MODEL_DIR, exist_ok=True)

# 1. Load Data
print("Loading data...")
df = pd.read_csv(DATA_PATH, keep_default_na=False)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 2. Validation
print("\n--- DATA VALIDATION ---")
print(f"Total records: {len(df)}")
print(f"Missing values: {df.isnull().sum().sum()}")
print(f"Duplicate values: {df.duplicated().sum()}")
print(f"Target distribution (failure_within_24h):\n{df['failure_within_24h'].value_counts()}")

is_ordered = True
for m_id, group in df.groupby('machine_id'):
    if not group['timestamp'].is_monotonic_increasing:
        is_ordered = False
        break
print(f"Chronological ordering maintained: {is_ordered}")

# 3. Create Features
print("\nCreating features...")
df_feat = create_features(df)

# For Anomaly model, we use the whole dataset for training (unsupervised)
X_all = df_feat[ALL_FEATURES]

print("\n--- TRAINING ANOMALY MODEL ---")
# Compute contamination dynamically based on synthetic ground-truth anomaly rate
anomaly_rate = float(df_feat['anomaly'].mean())
contamination = max(0.01, min(0.05, round(anomaly_rate, 4)))
print(f"Dataset anomaly rate: {anomaly_rate:.4f} ({df_feat['anomaly'].sum()} / {len(df_feat)} records)")
print(f"Configuring IsolationForest contamination: {contamination:.4f}")

iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
iso_forest.fit(X_all)

# Save Anomaly Model
joblib.dump(iso_forest, os.path.join(MODEL_DIR, 'anomaly_model.pkl'))

# Evaluate against the 'anomaly' label we generated for ground truth
preds = iso_forest.predict(X_all)
y_pred_anomaly = [1 if p == -1 else 0 for p in preds]
y_true_anomaly = df_feat['anomaly'].values

print("Anomaly Detection Evaluation (against synthetic 'anomaly' label):")
print(classification_report(y_true_anomaly, y_pred_anomaly, zero_division=0))

# 4. Chronological Train/Test Split for Failure Prediction
# We sort by time and split 80/20
df_feat = df_feat.sort_values('timestamp').reset_index(drop=True)
split_idx = int(len(df_feat) * 0.8)

train_df = df_feat.iloc[:split_idx]
test_df = df_feat.iloc[split_idx:]

X_train = train_df[ALL_FEATURES]
y_train = train_df['failure_within_24h']

X_test = test_df[ALL_FEATURES]
y_test = test_df['failure_within_24h']

print("\n--- SAMPLE COUNTS & TARGET DISTRIBUTIONS ---")
print(f"Training samples: {len(X_train)} (Positive/Failures: {y_train.sum()}, Negative/Normal: {len(y_train) - y_train.sum()})")
print(f"Test samples:     {len(X_test)} (Positive/Failures: {y_test.sum()}, Negative/Normal: {len(y_test) - y_test.sum()})")
print(f"Full dataset failure distribution:\n{df['failure_within_24h'].value_counts(normalize=True).rename('proportion').to_frame().assign(count=df['failure_within_24h'].value_counts())}")
print(f"Full dataset anomaly distribution:\n{df['anomaly'].value_counts(normalize=True).rename('proportion').to_frame().assign(count=df['anomaly'].value_counts())}")

print("\n--- TRAINING FAILURE PREDICTION MODEL ---")
rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
rf.fit(X_train, y_train)

# Save Failure Model
joblib.dump(rf, os.path.join(MODEL_DIR, 'failure_model.pkl'))

# 5. Evaluate Failure Prediction
y_pred_fail = rf.predict(X_test)
y_prob_fail = rf.predict_proba(X_test)[:, 1]

precision = precision_score(y_test, y_pred_fail, zero_division=0)
recall = recall_score(y_test, y_pred_fail, zero_division=0)
f1 = f1_score(y_test, y_pred_fail, zero_division=0)
try:
    auc = roc_auc_score(y_test, y_prob_fail)
except ValueError:
    auc = None

print("Failure Prediction Evaluation (Test Set):")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-score: {f1:.4f}")
if auc is not None:
    print(f"ROC-AUC: {auc:.4f}")
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred_fail))

print("\n--- FEATURE IMPORTANCE ---")
importances = rf.feature_importances_
feature_imp = pd.DataFrame({'Feature': ALL_FEATURES, 'Importance': importances})
feature_imp = feature_imp.sort_values('Importance', ascending=False)
for _, row in feature_imp.iterrows():
    print(f"{row['Feature']}: {row['Importance']:.4f}")

# 6. Example Predictions
print("\n--- EXAMPLE PREDICTIONS ---")
from anomaly_model import AnomalyModel
from failure_model import FailureModel

am = AnomalyModel(os.path.join(MODEL_DIR, 'anomaly_model.pkl'))
fm = FailureModel(os.path.join(MODEL_DIR, 'failure_model.pkl'))

# Find examples from dataset
normal_record = df[(df['anomaly'] == 0) & (df['failure_within_24h'] == 0)].iloc[0].to_dict()
anomalous_record = df[df['anomaly'] == 1].iloc[0].to_dict()
pre_fail_record = df[df['failure_within_24h'] == 1].iloc[-1].to_dict()

for name, rec in [("Normal Machine Record", normal_record), 
                  ("Anomalous Machine Record", anomalous_record), 
                  ("Pre-failure Record", pre_fail_record)]:
    
    anom_res = am.detect(rec)
    fail_res = fm.predict(rec)
    print(f"\n{name} (Machine: {rec['machine_id']})")
    print(f"Anomaly: {anom_res['anomaly']} (Score: {anom_res['score']:.4f})")
    print(f"Failure within 24h: {fail_res['failure_within_24h']} (Probability: {fail_res['probability']:.4f})")

print("\nTraining completed successfully. Models saved to backend/ml/saved_models/")
