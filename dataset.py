"""
dataset.py — Real training data from local Python source files.

Sources  : Python stdlib + all installed packages (11k+ .py files)
Labeling : pylint score >= 7.0 → clean (0), < 4.0 or SyntaxError → buggy (1)
Balancing: Bug-injection on clean files to balance buggy class
           (off-by-one, wrong operator, bare-except injection)
Saves    : data/training_data.csv
"""
import os, sys, csv, ast, random, subprocess, site
from features import extract_features, FEATURE_KEYS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "training_data.csv")
COLS = FEATURE_KEYS + ["label"]


# ── File collection ────────────────────────────────────────────────────────────

def collect_files(min_b=800, max_b=30_000):
    roots = [os.path.dirname(os.__file__)] + site.getsitepackages()
    files = []
    for root in roots:
        for dp, _, fnames in os.walk(root):
            for fn in fnames:
                if not fn.endswith(".py"):
                    continue
                fp = os.path.join(dp, fn)
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    continue
                if min_b <= sz <= max_b:
                    files.append(fp)
    random.shuffle(files)
    return files


# ── Pylint labeling ────────────────────────────────────────────────────────────

def pylint_score(path):
    try:
        r = subprocess.run(
            ["pylint", path, "--score=yes",
             "--disable=C,R,W0611,W0614,W0401,E0401,W0212",
             "--output-format=text", "--msg-template="],
            capture_output=True, text=True, timeout=8
        )
        for line in (r.stdout + r.stderr).splitlines():
            if "rated at" in line:
                return float(line.split("at")[1].split("/")[0].strip())
    except Exception:
        pass
    return None


def label_file(path):
    try:
        code = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None, None
    if len(code.strip()) < 100:
        return None, None
    try:
        compile(code, path, "exec")
    except SyntaxError:
        return 1, code
    score = pylint_score(path)
    if score is None:
        return None, None
    if score >= 7.0:
        return 0, code
    if score < 4.0:
        return 1, code
    return None, None  # ambiguous


# ── Bug injection ──────────────────────────────────────────────────────────────

class BugInjector(ast.NodeTransformer):
    def __init__(self):
        self.done = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if not self.done and isinstance(node.func, ast.Name) and node.func.id == "range" and node.args:
            inner = node.args[0]
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "len":
                node.args[0] = ast.BinOp(left=inner, op=ast.Add(), right=ast.Constant(value=1))
                self.done = True
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if (not self.done and isinstance(node.op, ast.Add)
                and isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, (int, float))):
            node.op = ast.Sub(); self.done = True
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if not self.done and node.ops:
            if isinstance(node.ops[0], ast.Gt):
                node.ops[0] = ast.GtE(); self.done = True
            elif isinstance(node.ops[0], ast.Lt):
                node.ops[0] = ast.LtE(); self.done = True
        return node


def inject_bug(code):
    try:
        tree = ast.parse(code)
        inj = BugInjector()
        new_tree = inj.visit(tree)
        if not inj.done:
            return None
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)
    except Exception:
        return None


# ── Main builder ───────────────────────────────────────────────────────────────

def build_dataset(target=200, seed=42):
    random.seed(seed)
    os.makedirs(DATA_DIR, exist_ok=True)

    rows, counts, clean_pool = [], {0: 0, 1: 0}, []

    print("Scanning Python source files on this system...")
    all_files = collect_files()
    print(f"Found {len(all_files)} candidate .py files\n")

    for path in all_files:
        if counts[0] >= target and counts[1] >= target:
            break
        label, code = label_file(path)
        if label is None:
            continue
        if counts[label] >= target:
            continue
        feats = extract_features(code)
        row = {k: feats.get(k, 0) for k in FEATURE_KEYS}
        row["label"] = label
        rows.append(row)
        counts[label] += 1
        if label == 0:
            clean_pool.append(code)
        sys.stdout.write(f"\r  Clean:{counts[0]:3d}/{target}  Buggy:{counts[1]:3d}/{target}")
        sys.stdout.flush()

    print(f"\n\nInjecting real bugs to balance dataset...")
    random.shuffle(clean_pool)
    for code in clean_pool:
        if counts[1] >= target:
            break
        buggy = inject_bug(code)
        if not buggy:
            continue
        feats = extract_features(buggy)
        row = {k: feats.get(k, 0) for k in FEATURE_KEYS}
        row["label"] = 1
        rows.append(row)
        counts[1] += 1

    random.shuffle(rows)
    with open(CSV_PATH, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=COLS).writeheader()
        csv.DictWriter(f, fieldnames=COLS).writerows(rows)

    print(f"\nSaved {len(rows)} rows -> {CSV_PATH}")
    print(f"Clean: {counts[0]}  Buggy: {counts[1]}")
    return CSV_PATH


if __name__ == "__main__":
    build_dataset()
