"""
frontend.py - Professional Streamlit UI for the bug predictor.
"""
import requests
import streamlit as st

import os
API = os.getenv("API_URL", "http://127.0.0.1:8000")
LANGUAGE_OPTIONS = ["Python", "Java", "C", "C++", "JavaScript"]
EDITOR_LANGUAGE_MAP = {
    "Python": "python",
    "Java": "java",
    "C": "c",
    "C++": "cpp",
    "JavaScript": "javascript",
}
RISK_COLORS = {"Low": "#1F8A70", "Medium": "#E68A00", "High": "#C84C3B"}

st.set_page_config(page_title="Code Bug Predictor", page_icon="BP", layout="wide")


@st.cache_data(ttl=10, show_spinner=False)
def fetch_health(api_url: str) -> dict:
    response = requests.get(f"{api_url}/health", timeout=3)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=20, show_spinner=False)
def fetch_history(api_url: str, limit: int = 20) -> list[dict]:
    response = requests.get(f"{api_url}/history", params={"limit": limit}, timeout=5)
    response.raise_for_status()
    return response.json()


def clear_history_request(api_url: str) -> int:
    response = requests.delete(f"{api_url}/history", timeout=5)
    response.raise_for_status()
    return int(response.json().get("deleted", 0))


@st.cache_data(ttl=20, show_spinner=False)
def fetch_metrics(api_url: str) -> dict:
    response = requests.get(f"{api_url}/metrics", timeout=5)
    response.raise_for_status()
    return response.json()


def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;500;700&display=swap');

        :root {
            --ink: #FFFFFF;
            --muted: #A0AAB5;
            --bg-base: #0B0E14;
            --glass-bg: rgba(20, 25, 35, 0.4);
            --glass-border: rgba(255, 255, 255, 0.08);
            --accent-1: #00F0FF;
            --accent-2: #7000FF;
            --accent-3: #FF0055;
            --warm: #FF9900;
        }

        /* Full page background animation */
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        [data-testid="stAppViewContainer"] {
            background: linear-gradient(-45deg, #05070a, #0d131f, #050b14, #12091c);
            background-size: 400% 400%;
            animation: gradientShift 20s ease infinite;
            color: var(--ink);
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stSidebar"] {
            background: rgba(10, 12, 16, 0.6) !important;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid var(--glass-border) !important;
        }

        [data-testid="stSidebar"] * {
            font-family: 'Inter', sans-serif;
        }

        .block-container {
             padding-top: 2rem;
             max-width: 1400px;
        }

        /* Glassmorphism Cards */
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease, border-color 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 240, 255, 0.15);
            border-color: rgba(0, 240, 255, 0.3);
        }

        .hero {
            background: linear-gradient(135deg, rgba(20, 25, 35, 0.5) 0%, rgba(10, 15, 25, 0.8) 100%);
            border: 1px solid var(--glass-border);
            border-radius: 32px;
            padding: 3rem;
            margin-bottom: 2rem;
            overflow: hidden;
            position: relative;
            backdrop-filter: blur(20px);
        }

        .hero::before {
            content: "";
            position: absolute;
            top: -50%; left: -50%; right: -50%; bottom: -50%;
            background: conic-gradient(from 180deg at 50% 50%, var(--accent-1) 0deg, var(--accent-2) 180deg, var(--accent-3) 360deg);
            filter: blur(120px);
            opacity: 0.15;
            z-index: 0;
            animation: spin 15s linear infinite;
        }

        @keyframes spin {
            100% { transform: rotate(360deg); }
        }

        .hero-content {
            position: relative;
            z-index: 1;
        }

        .hero-title {
            font-family: 'Outfit', sans-serif;
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(to right, #ffffff, #a0aab5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            line-height: 1.1;
            letter-spacing: -1px;
        }

        .hero-subtitle {
            font-size: 1.2rem;
            color: var(--muted);
            max-width: 600px;
            line-height: 1.6;
        }
        
        .hero-kicker {
            color: var(--accent-1);
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }

        .summary-grid, .metric-band {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .summary-card, .panel-card, .history-card, .feature-card, .risk-card {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            transition: all 0.3s ease;
        }

        .summary-card { padding: 1.5rem; display: flex; flex-direction: column; align-items: flex-start; }
        .summary-card:hover { transform: translateY(-4px); border-color: var(--accent-2); background: rgba(30, 35, 50, 0.6); box-shadow: 0 10px 30px rgba(112, 0, 255, 0.2); }

        .summary-label, .mini-label, .panel-label {
            font-family: 'Outfit', sans-serif;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--muted);
        }

        .summary-value {
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.5rem;
            background: linear-gradient(to right, #00F0FF, #7000FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .panel-card { padding: 2rem; margin-bottom: 1.5rem; }
        
        .section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .section-title::before {
            content: '';
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--accent-1);
            box-shadow: 0 0 10px var(--accent-1);
        }

        .section-copy { color: var(--muted); margin-bottom: 1.5rem; line-height: 1.6; }

        .stButton > button, .stFormSubmitButton > button {
            background: linear-gradient(90deg, #00F0FF 0%, #7000FF 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-family: 'Outfit', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            padding: 0.8rem 2rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(112, 0, 255, 0.3) !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
        }

        .stButton > button:hover, .stFormSubmitButton > button:hover {
            transform: scale(1.02) translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0, 240, 255, 0.5) !important;
            background: linear-gradient(90deg, #00F0FF -20%, #7000FF 80%) !important;
        }

        .stTextArea textarea, div[data-baseweb="select"] > div {
            background: rgba(0,0,0,0.4) !important;
            border: 1px solid var(--glass-border) !important;
            color: #FFFFFF !important;
            border-radius: 12px !important;
            font-family: 'Inter', monospace !important;
            transition: border-color 0.3s;
        }
        
        div[data-baseweb="select"] * {
            color: #FFFFFF !important;
        }
        
        .stTextArea textarea:focus, div[data-baseweb="select"] > div:focus-within {
            border-color: var(--accent-1) !important;
            box-shadow: 0 0 0 1px var(--accent-1) !important;
        }

        .risk-card { padding: 2.5rem; position: relative; overflow: hidden; }
        .risk-score { font-family: 'Outfit', sans-serif; font-size: 4rem; font-weight: 800; line-height: 1; margin: 1rem 0;}
        .risk-track { height: 12px; background: rgba(255,255,255,0.05); border-radius: 20px; overflow: hidden; margin-top: 1.5rem; }
        .risk-fill { height: 100%; border-radius: 20px; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
        
        .issue-card, .bug-line-card {
            background: rgba(255, 153, 0, 0.05);
            border-left: 4px solid var(--warm);
            padding: 1rem 1.2rem;
            border-radius: 0 12px 12px 0;
            margin-bottom: 0.8rem;
            transition: transform 0.2s;
        }
        .issue-card:hover { transform: translateX(5px); background: rgba(255, 153, 0, 0.1); border-left-color: var(--accent-1); }
        
        .bug-line-card { border-left-color: var(--accent-3); background: rgba(255, 0, 85, 0.05); }
        .bug-line-card:hover { transform: translateX(5px); background: rgba(255, 0, 85, 0.1); border-left-color: var(--accent-2);}
        
        .feature-card { padding: 1.5rem; text-align: center; }
        .feature-value { font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 700; background: linear-gradient(to right, #fff, #ccc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

        .history-card { padding: 1.5rem; cursor: pointer; }
        .history-card:hover { border-color: var(--accent-1); transform: translateX(5px) translateY(-2px); box-shadow: 0 10px 20px rgba(0, 240, 255, 0.1); }
        .status-pill { border-radius: 20px; padding: 0.4rem 0.8rem; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 0.85rem; }

        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem; background: transparent; padding-bottom: 0.5rem; margin-bottom: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px; background: rgba(255,255,255,0.03); color: var(--muted);
            padding: 0.8rem 1.5rem; font-family: 'Outfit', sans-serif; font-weight: 600;
            border: 1px solid transparent; transition: all 0.3s;
        }
        .stTabs [aria-selected="true"] {
            background: var(--glass-bg) !important;
            color: #fff !important;
            border: 1px solid var(--accent-1) !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
        }
        .stTabs [data-baseweb="tab"]:hover { background: rgba(255,255,255,0.08); color: #fff; }
        
        /* Loading overlay */
        .stSpinner > div > div { border-top-color: var(--accent-1) !important; }
        
        /* Typography overrides for default text */
        p, div, span, label { color: inherit; }
        
        [data-testid="stCodeBlock"] {
            background: #000000 !important;
            border: 1px solid var(--glass-border);
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-content">
                <div class="hero-kicker">✦ Next-Gen Workspace</div>
                <div class="hero-title">Code Bug Predictor</div>
                <p class="hero-subtitle">
                    AI-driven analysis for detecting bugs, risks, and security flaws across multiple languages.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_cards():
    st.markdown(
        """
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-label">Supported Languages</div>
                <div class="summary-value">5 Production Paths</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Analysis Modes</div>
                <div class="summary-value">Syntax, Risk, Fix</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Current Engine</div>
                <div class="summary-value">Offline-First Review</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(api_url: str):
    with st.sidebar:
        st.markdown("### Workspace Controls")
        st.caption("Connect to the API, refresh the model, and verify service health before running analysis.")

        try:
            health = fetch_health(api_url)
            st.success(f"API Online - v{health.get('version', '?')}")
        except Exception:
            st.error("API Offline - run `uvicorn backend:app --reload`")

        st.text_input("API URL", value=api_url, key="api_url")
        st.markdown("---")
        st.markdown("### Quick Notes")
        st.markdown("- Review simple syntax issues instantly")
        st.markdown("- Keep the same backend response flow")
        st.markdown("- Use history and metrics for follow-up")

        if st.button("Retrain Model", use_container_width=True):
            try:
                requests.post(f"{api_url}/train", timeout=5)
                fetch_metrics.clear()
                st.info("Training started in background...")
            except Exception:
                st.error("Cannot reach API")


def render_risk_card(probability: float, confidence: str):
    color = RISK_COLORS.get(confidence, "#8B98A7")
    st.markdown(
        f"""
        <div class="risk-card">
            <div class="panel-label">Bug Probability</div>
            <div class="risk-score" style="color:{color};">{probability}%</div>
            <div style="color:#B6C3D1;font-weight:700;">{confidence} Risk Confidence</div>
            <div class="risk-track">
                <div class="risk-fill" style="width:{probability}%; background:{color};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_issue_list(issues: list[str]):
    if not issues:
        st.info("No issues reported in the latest analysis.")
        return

    st.markdown('<div class="section-title">Detected Issues</div>', unsafe_allow_html=True)
    for issue in issues:
        st.markdown(f'<div class="issue-card">{issue}</div>', unsafe_allow_html=True)


def render_line_bugs(line_bugs: list[dict]):
    if not line_bugs:
        return

    st.markdown('<div class="section-title">Line-Level Findings</div>', unsafe_allow_html=True)
    for item in line_bugs:
        st.markdown(
            f"""
            <div class="bug-line-card">
                <div class="mini-label">Line {item['line']}</div>
                <div style="font-family:Consolas, 'Courier New', monospace; color:#F4F7FB; margin:0.3rem 0;">{item['code']}</div>
                <div style="color:#A9B9C8;">{item['issue']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_features(features: dict):
    st.markdown('<div class="section-title">Extracted Features</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for index, (name, value) in enumerate(features.items()):
        with cols[index % 4]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="mini-label">{name.replace("_", " ").title()}</div>
                    <div class="feature-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_history_card(item: dict):
    color = (
        "#1F8A70"
        if item["bug_probability"] < 35
        else "#D9822B"
        if item["bug_probability"] < 65
        else "#C84C3B"
    )
    issues_preview = ", ".join(item["issues"][:2]) or "No issues captured"
    if len(item["issues"]) > 2:
        issues_preview += f" +{len(item['issues']) - 2} more"

    st.markdown(
        f"""
        <div class="history-card">
            <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start;">
                <div>
                    <div class="mini-label">Analysis #{item['id']}</div>
                    <div style="color:#F4F7FB; font-weight:700; margin-top:0.25rem;">{issues_preview}</div>
                </div>
                <span class="status-pill" style="background:{color}20; color:{color}; border:1px solid {color}40;">
                    {item['bug_probability']}% {item['confidence']}
                </span>
            </div>
            <div style="margin-top:0.7rem; color:#9FB0C3;">{item['created_at'][:19]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: dict):
    cards = [
        ("Accuracy", f"{metrics['accuracy'] * 100:.1f}%"),
        ("F1 Score", f"{metrics['f1'] * 100:.1f}%"),
        ("Precision", f"{metrics['precision'] * 100:.1f}%"),
        ("Recall", f"{metrics['recall'] * 100:.1f}%"),
    ]
    st.markdown('<div class="metric-band">', unsafe_allow_html=True)
    cols = st.columns(4)
    for column, (label, value) in zip(cols, cards):
        with column:
            st.markdown(
                f"""
                <div class="summary-card">
                    <div class="summary-label">{label}</div>
                    <div class="summary-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


SAMPLE = """def calculate_stats(numbers):
    total = 0
    for i in range(len(numbers) + 1):   # off-by-one
        total += numbers[i]

    avg = total / len(numbers)           # ZeroDivisionError if empty

    def helper(data=[]):                 # mutable default argument
        data.append(avg)
        return data

    if avg == None:                      # should use 'is None'
        return 0
    return avg, helper()
"""

inject_styles()
api_url = st.session_state.get("api_url", API)
render_sidebar(api_url)
render_hero()
render_summary_cards()

tab_analyze, tab_history, tab_metrics = st.tabs(["Analyze", "History", "Model Metrics"])

with tab_analyze:
    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Source Input</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Choose a language, paste your code, and run the analyzer. The layout is redesigned, but the processing flow remains the same.</div>',
            unsafe_allow_html=True,
        )

        with st.form("analyze_form"):
            language = st.selectbox("Language", LANGUAGE_OPTIONS, index=0)
            code = st.text_area(
                "Code",
                value=st.session_state.get("code_input", SAMPLE),
                height=390,
                placeholder=f"Paste {language} code here...",
                key="code_input",
            )
            analyze = st.form_submit_button("Run Analysis", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Analysis Workspace</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Risk scoring, syntax validation, issue summaries, and generated fixes appear here after the request completes.</div>',
            unsafe_allow_html=True,
        )

        if analyze:
            if not code.strip():
                st.warning("Please enter code before running analysis.")
            else:
                with st.spinner("Analyzing code..."):
                    try:
                        response = requests.post(
                            f"{api_url}/analyze",
                            json={"code": code, "language": language.lower()},
                            timeout=45,
                        )
                        response.raise_for_status()
                        st.session_state["last_result"] = response.json()
                        st.session_state["last_language"] = language
                        fetch_history.clear()
                    except requests.ConnectionError:
                        st.error("Cannot connect to API. Start it with `uvicorn backend:app --reload`.")
                        st.stop()
                    except requests.HTTPError as exc:
                        try:
                            detail = response.json().get("detail", str(exc))
                        except Exception:
                            detail = str(exc)
                        st.error(f"API Error: {detail}")
                        st.stop()
                    except Exception as exc:
                        st.error(f"Unexpected error: {exc}")
                        st.stop()

        data = st.session_state.get("last_result")
        last_language = st.session_state.get("last_language", "Python")

        if not data:
            st.info("Run an analysis to populate this workspace.")
        else:
            render_risk_card(data["bug_probability"], data["confidence"])

            if data["syntax_error"]:
                st.error(f"Syntax Error - {data['syntax_error']}")

            render_issue_list(data["issues"])

            if data["explanation"]:
                st.markdown('<div class="section-title">Explanation</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="panel-card" style="margin-top:0.6rem;">{data["explanation"]}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)

    data = st.session_state.get("last_result")
    if data:
        lower_left, lower_right = st.columns([1, 1], gap="large")

        with lower_left:
            render_line_bugs(data.get("line_bugs", []))
            if data.get("features"):
                render_features(data["features"])

        with lower_right:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Fixed Code</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-copy">Safe fixes and rewritten output are rendered below using the selected language highlighter.</div>',
                unsafe_allow_html=True,
            )
            st.code(data["fixed_code"], language=EDITOR_LANGUAGE_MAP.get(last_language, "text"))
            with st.expander("Raw JSON Response"):
                st.json(data)
            st.markdown('</div>', unsafe_allow_html=True)

with tab_history:
    top_left, top_right = st.columns([0.7, 0.3])
    with top_left:
        st.markdown('<div class="section-title">Recent Analyses</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Use the history timeline to review recent risk calls and issue summaries.</div>',
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("Refresh History", use_container_width=True):
            fetch_history.clear()
        if st.button("Clear History", use_container_width=True, type="secondary"):
            try:
                deleted = clear_history_request(api_url)
                fetch_history.clear()
                st.success(f"Deleted {deleted} history item(s).")
                st.rerun()
            except Exception:
                st.warning("Could not clear history - is the API running?")

    try:
        history_items = fetch_history(api_url, limit=20)
        if not history_items:
            st.info("No history yet. Analyze some code first.")
        else:
            for item in history_items:
                render_history_card(item)
    except Exception:
        st.warning("Could not load history - is the API running?")

with tab_metrics:
    top_left, top_right = st.columns([0.8, 0.2])
    with top_left:
        st.markdown('<div class="section-title">Model Performance</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">This panel surfaces the current model summary and training footprint in a cleaner dashboard format.</div>',
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("Refresh Metrics", use_container_width=True):
            fetch_metrics.clear()

    try:
        metrics = fetch_metrics(api_url)
        if not metrics.get("trained") or metrics.get("training_samples", 0) == 0:
            st.info("Model not trained yet. Click Retrain Model in the sidebar.")
        else:
            render_metric_cards(metrics)
            st.caption(
                f"Model v{metrics.get('model_version', '?')} | "
                f"Trained on {metrics.get('training_samples', 0)} real code samples | "
                f"CV F1: {metrics.get('cv_f1_mean', 0) * 100:.1f}%"
            )
    except Exception:
        st.warning("Could not load metrics - is the API running?")
