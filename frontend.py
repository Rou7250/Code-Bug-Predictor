"""
frontend.py - Professional Streamlit UI for the bug predictor.
"""
import requests
import streamlit as st

API = "http://localhost:8000"
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
        :root {
            --ink: #F4F7FB;
            --muted: #9FB0C3;
            --paper: #050608;
            --card: rgba(10, 14, 18, 0.92);
            --line: rgba(140, 167, 196, 0.16);
            --accent: #22C38E;
            --accent-dark: #178A64;
            --alert: #FF6B57;
            --warm: #FFB34D;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(255, 179, 77, 0.10), transparent 24%),
                radial-gradient(circle at top right, rgba(34, 195, 142, 0.12), transparent 20%),
                linear-gradient(180deg, #040507 0%, #090C10 42%, #050608 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #06080B 0%, #0B1117 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        [data-testid="stSidebar"] * {
            color: #F7F3EB;
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }

        .hero {
            background: linear-gradient(135deg, rgba(6, 9, 13, 0.98), rgba(12, 19, 28, 0.98));
            color: #F4F7FB;
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 28px;
            padding: 2rem 2.2rem;
            box-shadow: 0 24px 52px rgba(0, 0, 0, 0.38);
            margin-bottom: 1.4rem;
            overflow: hidden;
            position: relative;
        }

        .hero::after {
            content: "";
            position: absolute;
            width: 240px;
            height: 240px;
            right: -60px;
            top: -80px;
            background: radial-gradient(circle, rgba(34, 195, 142, 0.22), transparent 70%);
        }

        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: 0.18rem;
            font-size: 0.76rem;
            color: rgba(244, 247, 251, 0.62);
            margin-bottom: 0.5rem;
        }

        .hero-title {
            font-family: Georgia, "Palatino Linotype", serif;
            font-size: 2.5rem;
            line-height: 1.05;
            margin: 0 0 0.7rem 0;
        }

        .hero-subtitle {
            max-width: 48rem;
            color: rgba(244, 247, 251, 0.78);
            font-size: 1.02rem;
            line-height: 1.65;
            margin: 0;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin: 1.2rem 0 1rem 0;
        }

        .summary-card, .panel-card, .history-card, .feature-card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 24px;
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
        }

        .summary-card {
            padding: 1rem 1.1rem;
        }

        .summary-label, .panel-label, .mini-label {
            font-size: 0.75rem;
            letter-spacing: 0.08rem;
            text-transform: uppercase;
            color: var(--muted);
        }

        .summary-value {
            margin-top: 0.35rem;
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 700;
        }

        .panel-card {
            padding: 1.15rem 1.2rem;
            margin-bottom: 1rem;
        }

        .section-title {
            color: var(--ink);
            font-family: Georgia, "Palatino Linotype", serif;
            font-size: 1.35rem;
            margin-bottom: 0.35rem;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 0.9rem;
        }

        .risk-card {
            border-radius: 24px;
            padding: 1.25rem 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.07);
            background: linear-gradient(180deg, rgba(13, 18, 24, 0.94), rgba(8, 12, 16, 0.94));
            margin-bottom: 1rem;
        }

        .risk-score {
            font-size: 2.85rem;
            font-weight: 800;
            line-height: 1;
            margin: 0.35rem 0 0.2rem 0;
        }

        .risk-track {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.10);
            overflow: hidden;
            margin-top: 0.85rem;
        }

        .risk-fill {
            height: 100%;
            border-radius: 999px;
        }

        .issue-card {
            border-left: 4px solid var(--warm);
            background: rgba(24, 19, 12, 0.92);
            padding: 0.85rem 0.95rem;
            border-radius: 16px;
            color: var(--ink);
            margin-bottom: 0.65rem;
        }

        .bug-line-card {
            background: rgba(13, 18, 24, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 0.9rem;
            margin-bottom: 0.65rem;
        }

        .status-pill {
            display: inline-block;
            padding: 0.32rem 0.7rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04rem;
            text-transform: uppercase;
        }

        .history-card {
            padding: 1rem 1.1rem;
            margin-bottom: 0.85rem;
        }

        .metric-band {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
        }

        .feature-card {
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.75rem;
        }

        .feature-value {
            font-size: 1.28rem;
            font-weight: 700;
            color: var(--ink);
            margin-top: 0.25rem;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        .stTextArea textarea {
            background: rgba(9, 12, 16, 0.96);
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            color: #F4F7FB;
        }

        .stTextArea textarea {
            font-family: Consolas, "Courier New", monospace;
            font-size: 0.95rem;
            background: #0A0D12 !important;
            color: #F4F7FB !important;
            caret-color: #22C38E;
        }

        label, .stMarkdown, p, span, div {
            color: inherit;
        }

        .stTextArea textarea::placeholder,
        input::placeholder {
            color: #7E90A3;
        }

        [data-testid="stCodeBlock"] {
            background: #070A0E !important;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
        }

        .stButton > button, .stFormSubmitButton > button {
            border-radius: 999px;
            border: none;
            background: linear-gradient(135deg, #22C38E, #178A64);
            color: #F7FBFD;
            font-weight: 700;
            min-height: 3rem;
            box-shadow: 0 12px 28px rgba(34, 195, 142, 0.22);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.6rem;
            background: transparent;
            margin-bottom: 1rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            background: rgba(11, 15, 20, 0.84);
            border: 1px solid rgba(255, 255, 255, 0.07);
            padding: 0.75rem 1rem;
            color: var(--ink);
            font-weight: 700;
        }

        .stTabs [aria-selected="true"] {
            background: #0F1D2A !important;
            color: #F4F7FB !important;
            border-color: rgba(34, 195, 142, 0.35) !important;
        }

        @media (max-width: 900px) {
            .summary-grid, .metric-band {
                grid-template-columns: 1fr;
            }

            .hero-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Engineering Review Workspace</div>
            <div class="hero-title">Code Bug Predictor + Fix Generator</div>
            <p class="hero-subtitle">
                Review code across Python, Java, C, C++, and JavaScript with a cleaner analysis workspace.
                The interface stays focused on fast triage, readable fixes, and practical engineering signals.
            </p>
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
