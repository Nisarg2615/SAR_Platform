"""
prediction_engine/model.py
XGBoost Risk Classifier + SHAP explainer for SAR Platform.
Trains on startup using the Bank_Transaction_Fraud_Detection.csv dataset.
"""

import os
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
import shap

MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgb_model.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Bank_Transaction_Fraud_Detection.csv")

NUM_FEATURES = 15
FEATURE_NAMES = [
    "transaction_frequency_7d",
    "amount_usd",
    "geography_risk_score",
    "account_age_days",
    "velocity_score",
    "merchant_category_risk",
    "device_risk",
    "time_of_day_risk",
    "transaction_type_risk",
    "account_balance_ratio",
    "customer_age_risk",
    "state_risk",
    "transaction_hour",
    "is_weekend",
    "is_high_amount"
]


def load_and_preprocess_data(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load CSV, preprocess, and return X, y arrays."""
    df = pd.read_csv(csv_path)
    
    df = df.dropna(subset=["Is_Fraud"])
    
    df["Transaction_Amount"] = pd.to_numeric(df["Transaction_Amount"], errors="coerce").fillna(0)
    df["Account_Balance"] = pd.to_numeric(df["Account_Balance"], errors="coerce").fillna(0)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(35)
    
    df = df.fillna("")
    
    high_risk_states = ["Bihar", "Jharkhand", "Assam", "West Bengal", "Odisha"]
    high_risk_cities = ["Patna", "Dhanbad", "Ranchi", "Guwahati", "Kolkata"]
    high_risk_merchants = ["Gambling", "Cryptocurrency", "Online Gaming", "Foreign Exchange"]
    
    state_risk_map = {state: 0.9 for state in high_risk_states}
    state_risk_map.update({s: 0.5 for s in df["State"].unique() if s not in high_risk_states})
    
    city_risk_map = {city: 0.9 for city in high_risk_cities}
    city_risk_map.update({c: 0.5 for c in df["City"].unique() if c not in high_risk_cities})
    
    merchant_risk_map = {m: 0.9 for m in high_risk_merchants}
    merchant_risk_map.update({m: 0.3 for m in df["Merchant_Category"].unique() if m not in high_risk_merchants})
    
    device_risk_map = {"Desktop": 0.2, "Mobile": 0.3, "ATM": 0.4, "POS Mobile Device": 0.5, "Voice Assistant": 0.7}
    
    def extract_hour(time_str):
        try:
            if pd.notna(time_str) and ":" in str(time_str):
                return int(str(time_str).split(":")[0])
            return 12
        except:
            return 12
    
    df["transaction_hour"] = df["Transaction_Time"].apply(extract_hour)
    df["is_weekend"] = df["Transaction_Date"].apply(lambda x: 1 if pd.notna(x) and any(d in str(x).lower() for d in ["sun", "sat"]) else 0)
    
    features = pd.DataFrame()
    
    # --- DETERMINISTIC FEATURE ENGINEERING (Removing random noise) ---
    # Frequency is modeled as a function of transaction count relative to account age
    # For synthetic demo, we use a more stable mapping based on Transaction_Amount and Age
    features["transaction_frequency_7d"] = (df["Transaction_Amount"] % 100) / 100.0 if not df.empty else 0.5
    features["amount_usd"] = (df["Transaction_Amount"] / 1000.0).clip(0, 100)
    features["geography_risk_score"] = df["City"].map(city_risk_map).fillna(0.3)
    features["account_age_days"] = (df["Age"] * 365.25).clip(0, 20000) / 20000.0
    # Velocity is modeled based on transaction hour (night time = higher velocity risk)
    features["velocity_score"] = df["transaction_hour"].apply(lambda h: 0.7 if (h < 6 or h > 22) else 0.2)
    features["merchant_category_risk"] = df["Merchant_Category"].map(merchant_risk_map).fillna(0.3)
    features["device_risk"] = df["Transaction_Device"].map(device_risk_map).fillna(0.3)
    features["time_of_day_risk"] = df["transaction_hour"].apply(lambda h: 0.8 if (h >= 0 and h < 6) else 0.3)
    features["transaction_type_risk"] = 0.3 # Default for now
    features["account_balance_ratio"] = (df["Account_Balance"] / (df["Transaction_Amount"] + 1.0)).clip(0, 10) / 10.0
    features["customer_age_risk"] = df["Age"].apply(lambda a: 0.8 if a < 25 or a > 60 else 0.3)
    features["state_risk"] = df["State"].map(state_risk_map).fillna(0.3)
    features["transaction_hour"] = df["transaction_hour"] / 24.0
    features["is_weekend"] = df["is_weekend"]
    features["is_high_amount"] = (df["Transaction_Amount"] > 10000).astype(int)
    
    X = features.values.astype(np.float32)
    y = df["Is_Fraud"].astype(int).values
    
    return X, y


def train_and_save_model():
    """Train XGBoost model with overfit protection and regularizers."""
    print(f"Loading data from {DATA_PATH}...")
    
    if not os.path.exists(DATA_PATH):
        print("Data file not found, training on synthetic data")
        X = np.random.rand(1000, NUM_FEATURES)
        y = (np.sum(X[:, :5], axis=1) > 3.0).astype(int)
    else:
        X, y = load_and_preprocess_data(DATA_PATH)
        print(f"Loaded {len(X)} samples, {np.sum(y)} fraudulent")

    # Split for validation to enable early stopping
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, random_state=42)
    
    print("Training XGBoost model (with Overfit Protection)...")
    
    model = xgb.XGBClassifier(
        n_estimators=500,        # Higher estimators with early stopping
        max_depth=4,             # PREVENT OVERFITTING: shallower trees
        learning_rate=0.05,      # Smaller learning rate for better generalization
        gamma=1.0,               # PREVENT OVERFITTING: min loss reduction
        reg_lambda=2.0,          # PREVENT OVERFITTING: L2 regularization
        reg_alpha=0.5,           # PREVENT OVERFITTING: L1 regularization
        scale_pos_weight=len(y_train[y_train==0]) / max(1, len(y_train[y_train==1])),
        use_label_encoder=False,
        eval_metric='logloss',
        early_stopping_rounds=15, # MOVED TO CONSTRUCTOR
        random_state=42
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    joblib.dump(model, MODEL_PATH)
    print(f"Regularized model saved to {MODEL_PATH}")


class XGBRiskEngine:
    """
    Singleton risk engine. Loads XGBoost from disk exactly once.
    """
    _instance = None
    _model = None
    _explainer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XGBRiskEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if not os.path.exists(MODEL_PATH):
            train_and_save_model()
            
        print(f"Loading model from {MODEL_PATH}")
        self._model = joblib.load(MODEL_PATH)
        self._explainer = shap.TreeExplainer(self._model)

    def predict_risk(self, transaction_dict: dict) -> tuple[float, dict]:
        """
        Takes a transaction dict, builds a feature array, and returns:
        1. risk_score (0.0 to 1.0)
        2. shap_values (dict of top 5 feature names -> absolute SHAP value impact)
        """
        features = np.zeros((1, NUM_FEATURES))
        
        high_risk_states = ["Bihar", "Jharkhand", "Assam", "West Bengal", "Odisha"]
        high_risk_merchants = ["Gambling", "Cryptocurrency", "Online Gaming", "Foreign Exchange"]
        device_risk_map = {"Desktop": 0.2, "Mobile": 0.3, "ATM": 0.4, "POS Mobile Device": 0.5, "Voice Assistant": 0.7}
        
        amount = float(transaction_dict.get("amount_usd", transaction_dict.get("Transaction_Amount", 1000.0)))
        device = transaction_dict.get("transaction_device", transaction_dict.get("Transaction_Device", "Desktop"))
        merchant = transaction_dict.get("merchant_category", transaction_dict.get("Merchant_Category", "Retail"))
        state = transaction_dict.get("state", transaction_dict.get("State", "Maharashtra"))
        city = transaction_dict.get("city", transaction_dict.get("City", "Mumbai"))
        balance = float(transaction_dict.get("account_balance", transaction_dict.get("Account_Balance", 10000.0)))
        age = int(transaction_dict.get("age", transaction_dict.get("Age", 35)))
        tx_time = str(transaction_dict.get("transaction_time", transaction_dict.get("Transaction_Time", "12:00:00")))
        
        try:
            hour = int(tx_time.split(":")[0])
        except:
            hour = 12
        
        # --- DETERMINISTIC FEATURES (No random noise) ---
        features[0, 0] = (amount % 100) / 100.0
        features[0, 1] = min(amount / 20000.0, 1.0)
        features[0, 2] = 0.9 if state in high_risk_states else 0.3
        features[0, 3] = (age * 365.25) / 20000.0
        features[0, 4] = 0.7 if (hour < 6 or hour > 22) else 0.2
        features[0, 5] = 0.9 if merchant in high_risk_merchants else 0.3
        features[0, 6] = device_risk_map.get(device, 0.3)
        features[0, 7] = 0.8 if hour >= 0 and hour < 6 else 0.3
        features[0, 8] = 0.3
        features[0, 9] = min(balance / (amount + 1.0), 10) / 10.0
        features[0, 10] = 0.8 if age < 25 or age > 60 else 0.3
        features[0, 11] = 0.9 if state in high_risk_states else 0.3
        features[0, 12] = hour / 24.0
        features[0, 13] = 0.0 # Placeholder for is_weekend if not in dict
        features[0, 14] = 1.0 if amount > 10000 else 0.0
        
        assert self._model is not None
        probs = self._model.predict_proba(features)
        risk_score = float(probs[0, 1])
        
        # --- NEW DATASET ADAPTATION: factor in explicit ML indicators ---
        ml_indicators = transaction_dict.get("money_laundering_indicators", "")
        if isinstance(ml_indicators, str) and len(ml_indicators) > 5:
            # If explicit indicators are provided (from SAR CSV), boost risk score
            if any(k in ml_indicators.lower() for k in ["high_value", "offshore", "rapid", "structuring"]):
                risk_score = max(risk_score, 0.92)  # High Confidence RED
            else:
                risk_score = max(risk_score, 0.75)  # AMBER
        elif float(amount) > 50000:
            risk_score = max(risk_score, 0.70)  # AMBER fallback for high amount

        assert self._explainer is not None
        shap_vals = self._explainer.shap_values(features)
        
        if isinstance(shap_vals, list):
            sv = shap_vals[1][0]
        else:
            sv = shap_vals[0]
            
        top_indices = np.argsort(np.abs(sv))[-5:]
        
        shap_dict = {}
        for idx in top_indices:
            feat_name = FEATURE_NAMES[idx]
            impact = float(sv[idx])
            shap_dict[feat_name] = impact
            
        return risk_score, shap_dict
