# 🐛 Code Bug Predictor v2 — Production

## Architecture

```
bug_predictor_v2/
├── backend/
│   ├── api.py         FastAPI — routes, validation, orchestration
│   ├── models.py      Pydantic request/response schemas
│   ├── database.py    SQLAlchemy ORM + SQLite (save/query history)
│   ├── features.py    19-feature AST + radon extractor + line-bug detector
│   ├── ml.py          GradientBoosting training pipeline + eval metrics
│   ├── dataset.py     Real data: stdlib + packages labeled by pylint
│   └── llm.py         Gemini with retry + JSON enforcement
├── frontend/
│   └── app.py         Streamlit UI (Analyze | History | Metrics tabs)
├── data/              training_data.csv, model.pkl, metrics.json (auto-created)
└── requirements.txt
```

## Data Pipeline (Real Data)

```
Python stdlib (118 files)          ──┐
Installed packages (11k+ files)    ──┤ pylint score
                                     │  >= 7.0  → label 0 (clean)
                                     │  <  4.0  → label 1 (buggy)
Bug injection on clean files       ──┘  (off-by-one, wrong ops, comparisons)
         ↓
data/training_data.csv  (400 real samples)
         ↓
GradientBoostingClassifier (200 estimators)
train/test split + 5-fold CV
         ↓
data/metrics.json  { accuracy, F1, precision, recall, cv_f1_mean }
```

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your_key_from_aistudio.google.com"
```

## Run

```bash
# Terminal 1 — Backend
uvicorn backend:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run frontend.py
```

Open http://localhost:8501

## API Endpoints

| Method | Path       | Description                        |
|--------|------------|------------------------------------|
| GET    | /health    | Health check                       |
| POST   | /analyze   | Full analysis (ML + LLM + AST)     |
| GET    | /history   | Last N analyses from SQLite        |
| GET    | /metrics   | Model accuracy/F1/precision/recall |
| POST   | /train     | Retrain model (background task)    |

## What's New in v2

- ✅ Real training data (pylint-labeled Python stdlib + packages)
- ✅ 19 features (vs 8 in v1)
- ✅ Line-level bug detection (5 AST heuristics)
- ✅ Evaluation metrics saved (accuracy, F1, precision, recall, CV-F1)
- ✅ SQLAlchemy ORM (database.py separate from api.py)
- ✅ Pydantic models.py for all schemas
- ✅ LLM retry with tenacity (3 attempts, exponential backoff)
- ✅ 3-strategy JSON extraction from LLM responses
- ✅ Confidence score (Low/Medium/High)
- ✅ Streamlit tabs: Analyze | History | Metrics
- ✅ Background model retraining via /train endpoint
