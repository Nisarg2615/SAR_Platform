"""
prediction_engine/model.py
XGBoost Risk Classifier + SHAP explainer for SAR Platform.
Trains on startup if no model exists, then loads and serves predictions.
"""

import os
import joblib
import numpy as np
import xgboost as xgb
import shap

MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgb_model.pkl")

# We simulate a 40-feature transaction profile
NUM_FEATURES = 40
FEATURE_NAMES = [f"feature_{i}" for i in range(NUM_FEATURES)]
# Assign meaningful names to the most important features for the demo
FEATURE_NAMES[0] = "transaction_frequency_7d"
FEATURE_NAMES[1] = "amount_usd"
FEATURE_NAMES[2] = "geography_risk_score"
FEATURE_NAMES[3] = "account_age_days"
FEATURE_NAMES[4] = "velocity_score"


def train_and_save_model():
    """Train a dummy XGBoost model on synthetic data and save to disk."""
    print("Training synthetic XGBoost model...")
    
    # Generate 1000 samples, 40 features
    X_train = np.random.rand(1000, NUM_FEATURES)
    
    # Let's artificially make the first 5 features predictive of risk
    # Risk is higher if the sum of the first 5 features is high
    risk_metric = np.sum(X_train[:, :5], axis=1)
    y_train = (risk_metric > 3.0).astype(int)
    
    model = xgb.XGBClassifier(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)
    
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


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
        Takes a transaction dict, builds a 40-feature array, and returns:
        1. risk_score (0.0 to 1.0)
        2. shap_values (dict of top 5 feature names -> absolute SHAP value impact)
        """
        # For the demo, we construct a fake 40-feature array based on the transaction
        # so the output is logically correlated with the demo scenarios.
        features = np.zeros((1, NUM_FEATURES))
        
        amount = float(transaction_dict.get("amount_usd", 1000.0))
        geo = transaction_dict.get("geography", "US").lower()
        tx_type = transaction_dict.get("transaction_type", "wire")
        
        # Feature 1: High amount ~ 1.0
        features[0, 1] = min(amount / 20000.0, 1.0)
        
        # Feature 2: High risk geography
        high_risk_geos = ["offshore", "panama", "cayman islands", "malta"]
        if geo in high_risk_geos:
            features[0, 2] = 0.95
            
        # Feature 0 & 4: if structuring or layering, artificially bump
        if amount > 9000 and amount < 10000:
            features[0, 0] = 0.8  # high frequency
            features[0, 4] = 0.9  # high velocity
            
        # Get probability of class 1
        probs = self._model.predict_proba(features)
        risk_score = float(probs[0, 1])
        
        # Get SHAP values
        shap_vals = self._explainer.shap_values(features)
        
        # XGBClassifier shap_values might return a list [class0_shap, class1_shap] 
        # or a single array depending on the objective. Usually it's an array for binary.
        if isinstance(shap_vals, list):
            sv = shap_vals[1][0]
        else:
            sv = shap_vals[0]
            
        # Get top 5 features by absolute SHAP impact
        top_indices = np.argsort(np.abs(sv))[-5:]
        
        shap_dict = {}
        for idx in top_indices:
            feat_name = FEATURE_NAMES[idx]
            impact = float(sv[idx])
            shap_dict[feat_name] = impact
            
        return risk_score, shap_dict
