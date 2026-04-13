"""
ml.py — Training pipeline using REAL data (stdlib + packages labeled by pylint).
Model   : GradientBoostingClassifier (best accuracy/F1 on tabular code features)
Metrics : accuracy, F1, precision, recall — saved to data/metrics.json
"""
import os, csv, json, pickle
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from features import FEATURE_KEYS

DATA_DIR    = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_PATH    = os.path.join(DATA_DIR, "training_data.csv")
MODEL_PATH  = os.path.join(DATA_DIR, "model.pkl")
SCALER_PATH = os.path.join(DATA_DIR, "scaler.pkl")
METRICS_PATH= os.path.join(DATA_DIR, "metrics.json")
MODEL_VER   = "2.0"
_MODEL_CACHE = None
_SCALER_CACHE = None
_CACHE_SIGNATURE = None


def load_csv():
    if not os.path.exists(CSV_PATH):
        return None, None
    X, y = [], []
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            X.append([float(row.get(k, 0)) for k in FEATURE_KEYS])
            y.append(int(row["label"]))
    return np.array(X), np.array(y)


def train():
    global _MODEL_CACHE, _SCALER_CACHE, _CACHE_SIGNATURE
    from dataset import build_dataset
    print("Building real dataset...")
    build_dataset(target=200)

    X, y = load_csv()
    if X is None or len(X) < 50:
        raise RuntimeError("Not enough training data")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42
    )
    model.fit(X_tr_s, y_tr)
    y_pred = model.predict(X_te_s)

    metrics = {
        "accuracy":         round(accuracy_score(y_te, y_pred), 4),
        "f1":               round(f1_score(y_te, y_pred), 4),
        "precision":        round(precision_score(y_te, y_pred), 4),
        "recall":           round(recall_score(y_te, y_pred), 4),
        "training_samples": len(X),
        "model_version":    MODEL_VER,
    }

    # Cross-val F1 on full set
    cv_f1 = cross_val_score(model, scaler.transform(X), y, cv=5, scoring="f1")
    metrics["cv_f1_mean"] = round(cv_f1.mean(), 4)

    os.makedirs(DATA_DIR, exist_ok=True)
    pickle.dump(model, open(MODEL_PATH, "wb"))
    pickle.dump(scaler, open(SCALER_PATH, "wb"))
    json.dump(metrics, open(METRICS_PATH, "w"), indent=2)
    _MODEL_CACHE = model
    _SCALER_CACHE = scaler
    _CACHE_SIGNATURE = (
        os.path.getmtime(MODEL_PATH),
        os.path.getmtime(SCALER_PATH),
    )

    print(f"Model trained | Accuracy:{metrics['accuracy']}  F1:{metrics['f1']}  CV-F1:{metrics['cv_f1_mean']}")
    return model, scaler, metrics


def load_model():
    global _MODEL_CACHE, _SCALER_CACHE, _CACHE_SIGNATURE
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        signature = (
            os.path.getmtime(MODEL_PATH),
            os.path.getmtime(SCALER_PATH),
        )
        if _MODEL_CACHE is not None and _SCALER_CACHE is not None and _CACHE_SIGNATURE == signature:
            return _MODEL_CACHE, _SCALER_CACHE

        _MODEL_CACHE = pickle.load(open(MODEL_PATH, "rb"))
        _SCALER_CACHE = pickle.load(open(SCALER_PATH, "rb"))
        _CACHE_SIGNATURE = signature
        return _MODEL_CACHE, _SCALER_CACHE
    return None, None


def _heuristic_predict(features: dict):
    """Fast fallback when no trained model is available yet."""
    score = 0.0
    score += min(features.get("complexity", 0) * 3.0, 25.0)
    score += min(features.get("nested_depth", 0) * 4.0, 16.0)
    score += min(features.get("loops", 0) * 2.0, 10.0)
    score += min(features.get("nested_loops", 0) * 6.0, 18.0)
    score += min(features.get("try_except", 0) * 2.0, 8.0)
    score += min(features.get("bare_except", 0) * 12.0, 20.0)
    score += min(features.get("global_vars", 0) * 3.0, 9.0)
    score += min(features.get("halstead_bugs", 0) * 35.0, 12.0)
    score += 8.0 if features.get("lines", 0) > 150 else 0.0

    pct = round(min(score, 95.0), 2)
    confidence = "Low" if pct < 35 else "Medium" if pct < 65 else "High"
    return pct, confidence


def predict(features: dict):
    model, scaler = load_model()
    if model is None:
        return _heuristic_predict(features)

    vec = np.array([[features.get(k, 0) for k in FEATURE_KEYS]])
    vec_s = scaler.transform(vec)
    prob = float(model.predict_proba(vec_s)[0][1])
    pct = round(prob * 100, 2)
    confidence = "Low" if pct < 35 else "Medium" if pct < 65 else "High"
    return pct, confidence


def get_metrics() -> dict:
    if os.path.exists(METRICS_PATH):
        metrics = json.load(open(METRICS_PATH))
        metrics["trained"] = metrics.get("training_samples", 0) > 0
        return metrics
    return {
        "trained": False,
        "accuracy": 0,
        "f1": 0,
        "precision": 0,
        "recall": 0,
        "training_samples": 0,
        "model_version": MODEL_VER,
    }


if __name__ == "__main__":
    train()
