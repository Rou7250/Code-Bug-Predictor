"""
llm.py - Offline-first code analysis with optional Gemini support.
"""
import ast
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv(Path(__file__).resolve().with_name(".env"))

try:
    import google.generativeai as genai

    GEMINI_OK = True
except ImportError:
    GEMINI_OK = False

API_ENV_VAR = "GEMINI_API_KEY"
USE_GEMINI_ENV_VAR = "USE_GEMINI"
MODEL_NAME = "gemini-2.0-flash"
_model = None

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "cpp": "c++",
    "cxx": "c++",
    "cc": "c++",
}

SCHEMA = """{
  \"issues\": [\"short issue description\", ...],
  \"fixed_code\": \"complete corrected python code\",
  \"explanation\": \"2-3 sentence explanation of root causes and fixes\"
}"""


def _normalize_language(language: str) -> str:
    value = (language or "generic").strip().lower()
    return LANGUAGE_ALIASES.get(value, value)


def _is_python(language: str) -> bool:
    return _normalize_language(language) == "python"


def _is_c_like(language: str) -> bool:
    return _normalize_language(language) in {"java", "c", "c++", "javascript", "typescript", "go", "rust", "generic"}


def _should_use_gemini() -> bool:
    value = os.getenv(USE_GEMINI_ENV_VAR, "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_api_key() -> str:
    return os.getenv(API_ENV_VAR, "").strip()


def gemini_enabled() -> bool:
    return _should_use_gemini() and GEMINI_OK and bool(_get_api_key())


def _get_model():
    global _model
    if _model is not None:
        return _model

    if not _should_use_gemini():
        return None

    api_key = _get_api_key()
    if not api_key or not GEMINI_OK:
        return None

    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel(MODEL_NAME)
    return _model


def _build_prompt(code: str, syntax_err: str, language: str) -> str:
    note = f"\nKnown syntax error: {syntax_err}" if syntax_err else ""
    return f"""You are a senior {language} bug detection expert.{note}

Analyze this {language} code for bugs, anti-patterns, and runtime errors.
Also return a corrected full version of the code.

```{language}
{code[:4000]}
```

Respond with ONLY a JSON object matching this exact schema:
{SCHEMA}"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract JSON from Gemini response")


def _normalize_response(result: dict, original_code: str) -> dict:
    if not isinstance(result, dict):
        result = {}

    issues = result.get("issues", [])
    if isinstance(issues, str):
        issues = [issues]
    elif not isinstance(issues, list):
        issues = [str(issues)]

    fixed_code = result.get("fixed_code", original_code)
    if not isinstance(fixed_code, str) or not fixed_code.strip():
        fixed_code = original_code

    explanation = result.get("explanation", "")
    if not isinstance(explanation, str):
        explanation = str(explanation)

    return {
        "issues": [str(item) for item in issues if str(item).strip()],
        "fixed_code": fixed_code,
        "explanation": explanation.strip(),
    }


def _friendly_error_message(error: Exception) -> str:
    text = str(error).strip()
    lower_text = text.lower()

    if "429" in text or "quota" in lower_text or "rate limit" in lower_text:
        return "Gemini quota exceeded or rate limit reached. Offline analysis was used instead."
    if "403" in text or "permission" in lower_text or "api key not valid" in lower_text:
        return "Gemini rejected the request. Check whether the API key in `.env` is valid."
    if "deadline" in lower_text or "timed out" in lower_text or "timeout" in lower_text:
        return "Gemini request timed out. Offline analysis was used instead."
    if not text:
        return "Gemini failed unexpectedly. Offline analysis was used instead."

    return f"Gemini failed. Offline analysis was used instead. Details: {text[:120]}"


def _fix_unterminated_string_line(line: str) -> str:
    single_quotes = len(re.findall(r"(?<!\\)'", line))
    double_quotes = len(re.findall(r'(?<!\\)"', line))

    if single_quotes % 2 == 1 and double_quotes % 2 == 0:
        return line + "'"
    if double_quotes % 2 == 1 and single_quotes % 2 == 0:
        return line + '"'
    return line


def _balance_trailing_brackets(code: str) -> str:
    pairs = {"(": ")", "[": "]", "{": "}"}
    reverse_pairs = {v: k for k, v in pairs.items()}
    stack = []

    for char in code:
        if char in pairs:
            stack.append(char)
        elif char in reverse_pairs and stack and stack[-1] == reverse_pairs[char]:
            stack.pop()

    closing = []
    while stack:
        closing.append(pairs[stack.pop()])
    return code + "".join(closing)


def _complete_known_empty_call(line: str) -> str:
    match = re.match(
        r"^(?P<indent>\s*)(?P<call>(?:System|system)\.out\.(?:print|println|printf))\s*;?\s*$",
        line,
    )
    if match:
        return f"{match.group('indent')}{match.group('call')}()"
    return line


def _should_add_semicolon(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith((";", "{", "}", ":", ",")):
        return False
    if stripped.startswith(("#", "//", "/*", "*")):
        return False
    if re.match(r"^(if|for|while|else|switch|try|catch|finally|class|interface|enum|namespace|do)\b", stripped):
        return False
    return bool(re.search(r"[A-Za-z0-9_\])\"']$", stripped))


def _repair_basic_syntax(code: str, syntax_err: str, language: str) -> str:
    repaired = code

    if "unterminated string literal" in syntax_err.lower() or "unterminated string" in syntax_err.lower():
        lines = repaired.splitlines()
        if lines:
            lines[-1] = _fix_unterminated_string_line(lines[-1])
            repaired = "\n".join(lines)

    repaired = _balance_trailing_brackets(repaired)

    if _is_c_like(language):
        lines = []
        for raw_line in repaired.splitlines():
            raw_line = _complete_known_empty_call(raw_line)
            stripped = raw_line.strip()
            if _should_add_semicolon(stripped):
                lines.append(raw_line + ";")
            else:
                lines.append(raw_line)
        repaired = "\n".join(lines)

    return repaired


def _basic_fix_python(code: str) -> str:
    fixed = code
    fixed = re.sub(r"==\s*None", "is None", fixed)
    fixed = re.sub(r"!=\s*None", "is not None", fixed)
    fixed = re.sub(r"(?m)^(\s*)except\s*:\s*$", r"\1except Exception:", fixed)
    fixed = re.sub(r"range\s*\(\s*len\(([^)]+)\)\s*\+\s*1\s*\)", r"range(len(\1))", fixed)
    return fixed


def _basic_fix_c_like(code: str, language: str) -> str:
    fixed = code
    fixed = re.sub(r"\bfor\s*\(([^;]*;[^;]*?)<=\s*([A-Za-z_][\w.]*?(?:length|size|count))", r"for(\1< \2", fixed)

    if _normalize_language(language) in {"javascript", "typescript"}:
        fixed = re.sub(r"==\s*null", "=== null", fixed)
        fixed = re.sub(r"!=\s*null", "!== null", fixed)

    return fixed


def _basic_fix_code(code: str, language: str) -> str:
    fixed = _repair_basic_syntax(code, "", language)
    if _is_python(language):
        return _basic_fix_python(fixed)
    return _basic_fix_c_like(fixed, language)


def _analyze_python_issues(code: str, syntax_err: str) -> list[str]:
    issues = []
    if syntax_err:
        issues.append(f"Syntax error detected: {syntax_err}")

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append("Avoid bare `except:` because it catches every exception.")

        if isinstance(node, ast.Compare):
            values = [node.left, *node.comparators]
            if any(isinstance(value, ast.Constant) and value.value is None for value in values):
                for op in node.ops:
                    if isinstance(op, ast.Eq):
                        issues.append("Use `is None` instead of `== None`.")
                    if isinstance(op, ast.NotEq):
                        issues.append("Use `is not None` instead of `!= None`.")

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(
                        f"Mutable default argument found in `{node.name}()`. Use `None` and create the object inside the function."
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if node.args:
                arg = node.args[0]
                if (
                    isinstance(arg, ast.BinOp)
                    and isinstance(arg.op, ast.Add)
                    and isinstance(arg.right, ast.Constant)
                    and arg.right.value == 1
                ):
                    issues.append("Possible off-by-one error in `range(len(...)+1)`.")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            right = node.right
            if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == "len":
                issues.append("Division by `len(...)` may raise `ZeroDivisionError` for empty input.")

    return issues


def _analyze_c_like_issues(code: str, syntax_err: str, language: str) -> list[str]:
    issues = []
    if syntax_err:
        issues.append(f"Syntax issue detected: {syntax_err}")

    lines = code.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if re.search(r"\bfor\s*\([^;]*;[^;]*<=\s*[A-Za-z_][\w.]*?(length|size|count)", line):
            issues.append("Possible off-by-one loop boundary with `<=`.")
        if re.search(r"/\s*[A-Za-z_]\w*", line) and not re.search(r"/\s*\d+(\.\d+)?", line):
            issues.append("Potential division-by-zero risk if the divisor can become zero.")
        if language in {"javascript", "typescript"} and re.search(r"\b(if|while)\s*\([^)]*[^=!<>]=[^=][^)]*\)", line):
            issues.append("Possible assignment inside a condition.")
        if language in {"javascript", "typescript"} and ("== null" in line or "!= null" in line):
            issues.append("Prefer strict null comparison in JavaScript/TypeScript when possible.")
        if language == "c" and "gets(" in line:
            issues.append("Unsafe `gets()` call can overflow the destination buffer.")
        if language == "c" and re.search(r"\bstrcpy\s*\(", line):
            issues.append("Unchecked `strcpy()` may overflow the destination buffer.")
        if _should_add_semicolon(line) and _is_c_like(language):
            issues.append("Possible missing semicolon.")

    return issues


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _build_offline_issues(code: str, syntax_err: str, language: str) -> list[str]:
    language = _normalize_language(language)
    if _is_python(language):
        return _dedupe_keep_order(_analyze_python_issues(code, syntax_err))
    return _dedupe_keep_order(_analyze_c_like_issues(code, syntax_err, language))


def build_basic_response(code: str, syntax_err: str = "", language: str = "python", reason: str = "") -> dict:
    language = _normalize_language(language)
    repaired = _repair_basic_syntax(code, syntax_err, language)
    fixed_code = _basic_fix_python(repaired) if _is_python(language) else _basic_fix_c_like(repaired, language)

    issues = _build_offline_issues(code, syntax_err, language)
    if not issues:
        issues = [f"No critical bug pattern detected by offline analysis for {language}."]

    explanation_parts = []
    if reason:
        explanation_parts.append(reason)
    explanation_parts.append(
        f"This result was generated by offline rule-based analysis for {language}, so the interface stays the same but the fix quality is simpler than Gemini."
    )
    if fixed_code != code:
        explanation_parts.append("Safe automatic fixes were applied where the pattern was clear, such as simple syntax repairs, missing semicolons, null comparisons, and common loop mistakes.")
    else:
        explanation_parts.append("The code was already valid for the rules checked, or no safe automatic rewrite was available.")

    return {
        "issues": issues,
        "fixed_code": fixed_code,
        "explanation": " ".join(explanation_parts).strip(),
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(ValueError),
    reraise=True,
)
def _call_gemini(prompt: str) -> dict:
    model = _get_model()
    if model is None:
        raise ValueError("Gemini model unavailable")

    response = model.generate_content(prompt)
    return _extract_json(response.text)


def analyze_code(code: str, syntax_err: str = "", language: str = "python") -> dict:
    language = _normalize_language(language)

    if not _should_use_gemini():
        return build_basic_response(
            code,
            syntax_err,
            language,
            "Gemini is disabled. Offline analysis is active.",
        )

    if not GEMINI_OK:
        return build_basic_response(
            code,
            syntax_err,
            language,
            "Gemini SDK is not installed or could not be imported.",
        )

    if not _get_api_key():
        return build_basic_response(
            code,
            syntax_err,
            language,
            "GEMINI_API_KEY not configured.",
        )

    try:
        result = _call_gemini(_build_prompt(code, syntax_err, language))
        normalized = _normalize_response(result, code)
        if not normalized["explanation"]:
            normalized["explanation"] = "Gemini returned a response without explanation text."
        return normalized
    except Exception as e:
        return build_basic_response(
            code,
            syntax_err,
            language,
            _friendly_error_message(e),
        )
