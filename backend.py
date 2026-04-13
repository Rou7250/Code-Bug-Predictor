"""
api.py — FastAPI backend. Clean separation: models, DB, features, ML, LLM.
"""
import sys, os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import CodeRequest, AnalysisResponse, HistoryItem, MetricsResponse, LineBug
from database import init_db, save_analysis, get_history, clear_history
from features import extract_features, extract_line_bugs, normalize_language
from ml import predict, get_metrics, train
from llm import analyze_code, build_basic_response, gemini_enabled

LLM_TIMEOUT_SECONDS = 12
LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Bug Predictor API", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}


def _find_unbalanced_delimiter(code: str) -> str:
    pairs = {"(": ")", "[": "]", "{": "}"}
    reverse_pairs = {v: k for k, v in pairs.items()}
    stack = []

    for char in code:
        if char in pairs:
            stack.append(char)
        elif char in reverse_pairs:
            if not stack or stack[-1] != reverse_pairs[char]:
                return f"Unexpected closing delimiter `{char}`"
            stack.pop()

    if stack:
        return f"Missing closing delimiter `{pairs[stack[-1]]}`"
    return ""


def _has_unterminated_quote(code: str) -> str:
    single_count = 0
    double_count = 0
    escaped = False

    for char in code:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'":
            single_count += 1
        elif char == '"':
            double_count += 1

    if single_count % 2 == 1 or double_count % 2 == 1:
        return "Unterminated string literal detected"
    return ""


def _generic_syntax_check(code: str, language: str) -> str:
    quote_error = _has_unterminated_quote(code)
    if quote_error:
        return quote_error

    delimiter_error = _find_unbalanced_delimiter(code)
    if delimiter_error:
        return delimiter_error

    if language in {"java", "c", "c++", "javascript", "typescript"}:
        for line_number, raw_line in enumerate(code.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith(("#", "//", "/*", "*")):
                continue
            if line.endswith((";", "{", "}", ":", ",")):
                continue
            if line.startswith(("if", "for", "while", "else", "switch", "try", "catch", "finally", "class")):
                continue
            if any(token in line for token in ("=", "return", "break", "continue", "console.", "printf", "cout", "System.out")):
                return f"Line {line_number}: possible missing semicolon"

    return ""


def _syntax_check(code: str, language: str) -> str:
    if language == "python":
        try:
            compile(code, "<string>", "exec")
            return ""
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
    return _generic_syntax_check(code, language)


def _fallback_llm_result(code: str, syntax_error: str, line_bugs: list[LineBug], language: str, reason: str) -> dict:
    fallback = build_basic_response(code, syntax_error, language, reason)
    if line_bugs:
        merged_issues = [lb.issue for lb in line_bugs[:5]]
        for issue in fallback["issues"]:
            if issue not in merged_issues:
                merged_issues.append(issue)
        fallback["issues"] = merged_issues
    return fallback


def _run_llm_with_timeout(code: str, syntax_error: str, language: str, line_bugs: list[LineBug]) -> dict:
    if not gemini_enabled():
        return analyze_code(code, syntax_error, language)

    future = LLM_EXECUTOR.submit(analyze_code, code, syntax_error, language)
    try:
        return future.result(timeout=LLM_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        future.cancel()
        return _fallback_llm_result(
            code,
            syntax_error,
            line_bugs,
            language,
            f"LLM analysis timed out after {LLM_TIMEOUT_SECONDS} seconds. Showing fast static analysis only.",
        )
    except Exception as e:
        return _fallback_llm_result(
            code,
            syntax_error,
            line_bugs,
            language,
            f"LLM analysis failed: {str(e)[:200]}",
        )


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(req: CodeRequest, background_tasks: BackgroundTasks):
    code = req.code
    language = normalize_language(req.language)

    # 1. Syntax check
    syntax_error = _syntax_check(code, language)

    # 2. Feature extraction
    features = extract_features(code, language)

    # 3. ML prediction
    try:
        bug_prob, confidence = predict(features)
    except Exception as e:
        raise HTTPException(502, f"ML model error: {e}")

    # 4. Line-level bug detection
    line_bugs = [LineBug(**lb) for lb in extract_line_bugs(code, language)]

    # 5. LLM analysis
    llm = _run_llm_with_timeout(code, syntax_error, language, line_bugs)

    result = {
        "syntax_error":    syntax_error,
        "bug_probability": bug_prob,
        "confidence":      confidence,
        "issues":          llm["issues"],
        "line_bugs":       line_bugs,
        "fixed_code":      llm["fixed_code"],
        "explanation":     llm["explanation"],
        "features":        features,
    }

    background_tasks.add_task(
        save_analysis,
        code,
        {**result, "line_bugs": [lb.model_dump() for lb in line_bugs]},
    )
    return result


@app.get("/history", response_model=list[HistoryItem])
def history(limit: int = 20):
    return get_history(limit)


@app.delete("/history")
def delete_history():
    deleted = clear_history()
    return {"deleted": deleted}


@app.get("/metrics", response_model=MetricsResponse)
def metrics():
    return get_metrics()


@app.post("/train")
def retrain(background_tasks: BackgroundTasks):
    background_tasks.add_task(train)
    return {"status": "Training started in background. Check /metrics for results."}
