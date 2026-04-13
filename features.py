import ast
import re

from radon.complexity import cc_visit
from radon.metrics import h_visit

FEATURE_KEYS = [
    "lines", "blank_lines", "comment_lines", "code_lines",
    "loops", "nested_loops", "conditions", "try_except",
    "bare_except", "functions", "classes", "lambdas",
    "complexity", "halstead_bugs", "halstead_effort",
    "nested_depth", "returns", "global_vars", "assertions",
]

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "cpp": "c++",
    "cxx": "c++",
    "cc": "c++",
}


def normalize_language(language: str) -> str:
    value = (language or "generic").strip().lower()
    return LANGUAGE_ALIASES.get(value, value)


def extract_features(code: str, language: str = "python") -> dict:
    language = normalize_language(language)
    if language == "python":
        return _extract_python_features(code)
    return _extract_generic_features(code, language)


def _extract_python_features(code: str) -> dict:
    f = _base_features(code, "python")

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return f

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            f["loops"] += 1
            if any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node) if child is not node):
                f["nested_loops"] += 1
        elif isinstance(node, ast.If):
            f["conditions"] += 1
        elif isinstance(node, ast.Try):
            f["try_except"] += 1
            for handler in node.handlers:
                if handler.type is None:
                    f["bare_except"] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            f["classes"] += 1
        elif isinstance(node, ast.Lambda):
            f["lambdas"] += 1
        elif isinstance(node, ast.Return):
            f["returns"] += 1
        elif isinstance(node, ast.Global):
            f["global_vars"] += len(node.names)
        elif isinstance(node, ast.Assert):
            f["assertions"] += 1

    f["nested_depth"] = _max_depth(tree)

    try:
        cc = cc_visit(code)
        f["complexity"] = max((block.complexity for block in cc), default=1)
    except Exception:
        f["complexity"] = 1

    try:
        h = h_visit(code)
        if h:
            f["halstead_bugs"] = round(h.total.bugs, 4)
            f["halstead_effort"] = round(h.total.effort, 2)
    except Exception:
        pass

    return f


def _extract_generic_features(code: str, language: str) -> dict:
    f = _base_features(code, language)

    f["loops"] = _count_matches(code, [r"\bfor\s*\(", r"\bwhile\s*\("])
    f["conditions"] = _count_matches(code, [r"\bif\s*\(", r"\bswitch\s*\("])
    f["try_except"] = _count_matches(code, [r"\btry\b", r"\bcatch\s*\("])
    f["functions"] = _count_matches(
        code,
        [
            r"\bfunction\s+\w+\s*\(",
            r"\b[A-Za-z_]\w*\s+[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{",
        ],
    )
    f["classes"] = _count_matches(code, [r"\bclass\s+\w+"])
    f["returns"] = _count_matches(code, [r"\breturn\b"])
    f["assertions"] = _count_matches(code, [r"\bassert\b"])
    f["bare_except"] = 0
    f["nested_depth"] = _estimate_brace_depth(code)
    f["nested_loops"] = _count_matches(
        code,
        [
            r"\bfor\s*\([^)]*\)\s*\{[^{}]*(for|while)\s*\(",
            r"\bwhile\s*\([^)]*\)\s*\{[^{}]*(for|while)\s*\(",
        ],
    )

    keywords = f["loops"] + f["conditions"] + f["try_except"] + f["functions"] + f["classes"]
    operators = len(re.findall(r"==|!=|<=|>=|&&|\|\||[+\-*/%<>]=?|=", code))
    f["complexity"] = max(1, keywords + max(1, operators // 12))

    tokens = re.findall(r"[A-Za-z_]\w+|==|!=|<=|>=|&&|\|\||[{}()\[\];,.+\-*/%<>:=]", code)
    unique_tokens = len(set(tokens))
    total_tokens = len(tokens)
    f["halstead_bugs"] = round(min(total_tokens / 1200, 5), 4)
    f["halstead_effort"] = round(unique_tokens * max(total_tokens, 1) * 0.5, 2)

    return f


def _base_features(code: str, language: str) -> dict:
    f = {k: 0 for k in FEATURE_KEYS}
    lines = code.splitlines()
    comment_markers = _comment_prefixes(language)
    f["lines"] = len(lines)
    f["blank_lines"] = sum(1 for line in lines if not line.strip())
    f["comment_lines"] = sum(1 for line in lines if _is_comment_line(line, comment_markers))
    f["code_lines"] = f["lines"] - f["blank_lines"] - f["comment_lines"]
    return f


def _comment_prefixes(language: str) -> tuple[str, ...]:
    if language == "python":
        return ("#",)
    return ("//", "/*", "*")


def _is_comment_line(line: str, comment_markers: tuple[str, ...]) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(marker) for marker in comment_markers)


def _count_matches(code: str, patterns: list[str]) -> int:
    return sum(len(re.findall(pattern, code)) for pattern in patterns)


def _estimate_brace_depth(code: str) -> int:
    depth = 0
    max_depth = 0
    for char in code:
        if char in "({[":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char in ")}]" and depth > 0:
            depth -= 1
    return max_depth


def _max_depth(node, depth=0):
    scope = (ast.For, ast.While, ast.If, ast.With, ast.Try, ast.ExceptHandler)
    max_depth = depth
    for child in ast.iter_child_nodes(node):
        next_depth = depth + 1 if isinstance(child, scope) else depth
        max_depth = max(max_depth, _max_depth(child, next_depth))
    return max_depth


def extract_line_bugs(code: str, language: str = "python") -> list[dict]:
    language = normalize_language(language)
    if language == "python":
        return _extract_python_line_bugs(code)
    return _extract_generic_line_bugs(code, language)


def _extract_python_line_bugs(code: str) -> list[dict]:
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    lines = code.splitlines()

    for node in ast.walk(tree):
        line_number = getattr(node, "lineno", None)
        if line_number is None or line_number > len(lines):
            continue
        line_text = lines[line_number - 1].strip()

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({"line": line_number, "code": line_text, "issue": "Bare `except:` catches everything including SystemExit/KeyboardInterrupt"})

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if not isinstance(node.right, ast.Constant):
                issues.append({"line": line_number, "code": line_text, "issue": "Potential ZeroDivisionError - divisor is not a constant"})

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if node.args and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                issues.append({"line": line_number, "code": line_text, "issue": "Possible off-by-one: range(len(x)+1) accesses out-of-bounds index"})

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append({"line": node.lineno, "code": line_text, "issue": f"Mutable default argument in `{node.name}()` - shared across all calls"})

        if isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and comp.value is None:
                    issues.append({"line": line_number, "code": line_text, "issue": "Use `is None` instead of `== None`"})

    return _dedupe_line_bugs(issues)


def _extract_generic_line_bugs(code: str, language: str) -> list[dict]:
    issues = []
    lines = code.splitlines()

    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        if language in {"javascript", "typescript"} and re.search(r"\b(if|while)\s*\([^)]*[^=!<>]=[^=][^)]*\)", line):
            issues.append({"line": index, "code": line, "issue": "Possible assignment inside condition; use `===`/`!==` or compare explicitly"})

        if language in {"java", "c", "c++", "javascript", "typescript"} and re.search(r"\bfor\s*\([^;]*;[^;]*<=\s*[\w.]+(length|size|count)?", line):
            issues.append({"line": index, "code": line, "issue": "Possible off-by-one loop boundary with `<=`"})

        if re.search(r"/\s*[A-Za-z_]\w*", line) and not re.search(r"/\s*\d+(\.\d+)?", line):
            issues.append({"line": index, "code": line, "issue": "Potential division-by-zero risk if divisor can be zero"})

        if language == "c" and "gets(" in line:
            issues.append({"line": index, "code": line, "issue": "Unsafe `gets()` usage can overflow buffers"})

        if language == "c" and re.search(r"\bstrcpy\s*\(", line):
            issues.append({"line": index, "code": line, "issue": "Unchecked `strcpy()` may overflow destination buffer"})

        if language in {"javascript", "typescript"} and ("== null" in line or "!= null" in line):
            issues.append({"line": index, "code": line, "issue": "Loose null comparison detected; prefer strict equality where possible"})

        if language in {"java", "c", "c++", "javascript", "typescript"} and _looks_like_missing_semicolon(line):
            issues.append({"line": index, "code": line, "issue": "Possible missing semicolon"})

    return _dedupe_line_bugs(issues)


def _looks_like_missing_semicolon(line: str) -> bool:
    if line.endswith((";", "{", "}", ":", ",")):
        return False
    if line.startswith(("#", "//", "/*", "*")):
        return False
    if re.match(r"^(if|for|while|switch|else|do|try|catch|finally|class|interface|enum|namespace)\b", line):
        return False
    return bool(re.search(r"[A-Za-z0-9_\])\"]$", line))


def _dedupe_line_bugs(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        key = (item["line"], item["issue"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
