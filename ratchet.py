#!/usr/bin/env python3
"""
Agent Quality Ratchet — code quality that only goes up.

Single-file, zero-dependency quality enforcement for AI-assisted development.
Works with Claude Code (hooks + skills) and Codex (scripts + config).

Usage:
    python ratchet.py init          # Measure baseline, create .ratchet-state.json
    python ratchet.py check         # Fail if quality regressed
    python ratchet.py measure       # Re-measure and lower floors
    python ratchet.py orient        # Print one-line status (for SessionStart hooks)
    python ratchet.py report        # Full comparison report
    python ratchet.py debt          # Prioritized tech debt scan
    python ratchet.py debt --growth # Growth-path items only
    python ratchet.py history       # Show trend over time

    Add --json to any command for structured output (agent-native).
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path.cwd()
CONFIG_FILE = PROJECT_ROOT / ".ratchet.yaml"
STATE_FILE = PROJECT_ROOT / ".ratchet-state.json"
HISTORY_FILE = PROJECT_ROOT / ".ratchet-history.jsonl"

# Default config when no .ratchet.yaml exists
DEFAULT_CONFIG = {
    "language": "python",
    "metrics": {
        "lint_violations": {"tool": "ruff", "direction": "down"},
        "test_count": {"tool": "pytest", "direction": "up"},
        "coverage": {"tool": "pytest-cov", "direction": "up"},
        "complexity": {"tool": "ruff-c90", "threshold": 15, "direction": "down"},
    },
    "priorities": {
        "growth": 3.0,
        "reliability": 2.0,
        "cost": 1.5,
        "retention": 2.0,
        "default": 1.0,
    },
    "impact_keywords": {
        "growth": ["onboarding", "funnel", "activation", "signup", "registration"],
        "reliability": ["chat", "recommendation", "generation", "streaming"],
        "cost": ["model", "embedding", "openai", "anthropic", "ai_service"],
        "retention": ["notification", "engagement", "daily", "weekly"],
    },
}


def load_config() -> dict:
    """Load .ratchet.yaml merged with defaults for missing keys."""
    if CONFIG_FILE.exists():
        parsed = _parse_simple_yaml(CONFIG_FILE.read_text())
        # Merge: parsed values win, defaults fill gaps
        merged = dict(DEFAULT_CONFIG)
        merged.update({k: v for k, v in parsed.items() if v is not None})
        _validate_config(merged)
        return merged
    return DEFAULT_CONFIG


def _validate_config(config: dict) -> None:
    """Validate config values for safety."""
    lang = config.get("language", "python")
    if lang not in PLUGINS:
        config["language"] = "python"
    threshold = config.get("metrics", {}).get("complexity", {}).get("threshold", 15)
    if not isinstance(threshold, (int, float)) or threshold < 1 or threshold > 100:
        config.setdefault("metrics", {}).setdefault("complexity", {})["threshold"] = 15


def _parse_simple_yaml(text: str) -> dict:
    """Minimal YAML parser for .ratchet.yaml (no dependency on PyYAML)."""
    try:
        import yaml

        return yaml.safe_load(text) or DEFAULT_CONFIG
    except ImportError:
        # Fallback: use defaults but detect language from config
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("language:"):
                lang = line.split(":", 1)[1].strip().strip("'\"")
                config = dict(DEFAULT_CONFIG)
                config["language"] = lang
                return config
        return DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# Language-specific measurement plugins
# ---------------------------------------------------------------------------


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# --- Python ---

def _measure_python_lint() -> int:
    r = _run([sys.executable, "-m", "ruff", "check", ".", "--output-format=json"])
    try:
        return len(json.loads(r.stdout)) if r.stdout.strip() else 0
    except (json.JSONDecodeError, TypeError):
        return -1


def _measure_python_tests() -> int:
    r = _run([sys.executable, "-m", "pytest", "--co", "-q"])
    for line in (r.stdout + r.stderr).splitlines():
        if "test" in line and ("collected" in line or "selected" in line):
            for word in line.split():
                if word.isdigit():
                    return int(word)
    return 0


def _detect_source_dir() -> str:
    """Auto-detect source directory: app/ > src/ > lib/ > ."""
    for candidate in ("app", "src", "lib"):
        if Path(candidate).is_dir():
            return candidate
    return "."


def _measure_python_coverage() -> float:
    source = _detect_source_dir()
    r = _run([sys.executable, "-m", "pytest", f"--cov={source}", "--cov-report=term", "-q", "--tb=no"])
    for line in (r.stdout + r.stderr).splitlines():
        if line.strip().startswith("TOTAL"):
            for part in line.split():
                if part.endswith("%"):
                    return float(part.rstrip("%"))
    return 0.0


def _measure_python_complexity(threshold: int = 15) -> int:
    r = _run([
        sys.executable, "-m", "ruff", "check", ".", "--select", "C90",
        "--config", f"lint.mccabe.max-complexity = {threshold}",
        "--output-format=json",
    ])
    try:
        return len(json.loads(r.stdout)) if r.stdout.strip() else 0
    except (json.JSONDecodeError, TypeError):
        return 0


# --- Dart ---

def _measure_dart_lint() -> int:
    r = _run(["dart", "analyze", "--format=json"])
    try:
        data = json.loads(r.stdout) if r.stdout.strip() else {}
        return len(data.get("diagnostics", []))
    except (json.JSONDecodeError, TypeError):
        # Fallback: count lines with severity
        return sum(1 for line in r.stdout.splitlines() if "error" in line.lower() or "warning" in line.lower())


def _measure_dart_tests() -> int:
    r = _run(["flutter", "test", "--machine"])
    count = 0
    for line in r.stdout.splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "testDone" and event.get("result") == "success":
                count += 1
        except (json.JSONDecodeError, TypeError):
            pass
    return count if count > 0 else _count_test_files("test")


def _measure_dart_coverage() -> float:
    r = _run(["flutter", "test", "--coverage"])
    lcov = PROJECT_ROOT / "coverage" / "lcov.info"
    if lcov.exists():
        lines_found = lines_hit = 0
        for line in lcov.read_text().splitlines():
            if line.startswith("LF:"):
                lines_found += int(line[3:])
            elif line.startswith("LH:"):
                lines_hit += int(line[3:])
        return round(lines_hit / lines_found * 100, 1) if lines_found else 0.0
    return 0.0


def _measure_dart_complexity(threshold: int = 15) -> int:
    # Dart analyze doesn't report complexity directly; use AST-based fallback
    return _ast_complexity_scan("lib", threshold, suffix=".dart")


# --- TypeScript ---

def _measure_ts_lint() -> int:
    r = _run(["npx", "eslint", ".", "--format=json"])
    try:
        results = json.loads(r.stdout) if r.stdout.strip() else []
        return sum(len(f.get("messages", [])) for f in results)
    except (json.JSONDecodeError, TypeError):
        return -1


def _measure_ts_tests() -> int:
    r = _run(["npx", "jest", "--listTests"])
    return len([l for l in r.stdout.splitlines() if l.strip()])


def _measure_ts_coverage() -> float:
    r = _run(["npx", "jest", "--coverage", "--coverageReporters=text-summary"])
    for line in r.stdout.splitlines():
        if "Statements" in line or "Lines" in line:
            for part in line.split():
                if part.endswith("%"):
                    return float(part.rstrip("%"))
    return 0.0


def _measure_ts_complexity(threshold: int = 15) -> int:
    r = _run(["npx", "eslint", ".", "--rule", f'{{"complexity": ["error", {threshold}]}}', "--format=json"])
    try:
        results = json.loads(r.stdout) if r.stdout.strip() else []
        return sum(len([m for m in f.get("messages", []) if "complexity" in m.get("ruleId", "")]) for f in results)
    except (json.JSONDecodeError, TypeError):
        return 0


# --- Generic fallbacks ---

def _count_test_files(test_dir: str) -> int:
    count = 0
    for root, _, files in os.walk(test_dir):
        for f in files:
            if f.startswith("test_") or f.endswith("_test.py") or f.endswith("_test.dart") or f.endswith(".test.ts") or f.endswith(".spec.ts"):
                count += 1
    return count


def _ast_complexity_scan(source_dir: str, threshold: int, suffix: str = ".py") -> int:
    """AST-based complexity scan (Python files only for now)."""
    if suffix != ".py":
        return 0  # Only Python AST supported
    violations = 0
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for f in files:
            if not f.endswith(suffix):
                continue
            filepath = Path(root, f)
            try:
                if filepath.stat().st_size > 1_000_000:  # skip files > 1 MB
                    continue
            except OSError:
                continue
            try:
                tree = ast.parse(filepath.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        cc = 1
                        for child in ast.walk(node):
                            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.BoolOp)):
                                cc += 1
                            if isinstance(child, ast.BoolOp):
                                cc += len(child.values) - 1
                        if cc > threshold:
                            violations += 1
            except (SyntaxError, UnicodeDecodeError):
                pass
    return violations


# ---------------------------------------------------------------------------
# Measurement dispatch
# ---------------------------------------------------------------------------

PLUGINS = {
    "python": {
        "lint": _measure_python_lint,
        "tests": _measure_python_tests,
        "coverage": _measure_python_coverage,
        "complexity": _measure_python_complexity,
    },
    "dart": {
        "lint": _measure_dart_lint,
        "tests": _measure_dart_tests,
        "coverage": _measure_dart_coverage,
        "complexity": _measure_dart_complexity,
    },
    "typescript": {
        "lint": _measure_ts_lint,
        "tests": _measure_ts_tests,
        "coverage": _measure_ts_coverage,
        "complexity": _measure_ts_complexity,
    },
}


def measure(config: dict) -> dict:
    """Measure all configured metrics."""
    lang = config.get("language", "python")
    plugin = PLUGINS.get(lang, PLUGINS["python"])
    threshold = config.get("metrics", {}).get("complexity", {}).get("threshold", 15)

    return {
        "lint_violations": plugin["lint"](),
        "test_count": plugin["tests"](),
        "coverage_percent": plugin["coverage"](),
        "complexity_violations": plugin["complexity"](threshold),
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "language": lang,
    }


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def load_state() -> dict | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def save_state(metrics: dict) -> None:
    STATE_FILE.write_text(json.dumps(metrics, indent=2) + "\n")


def append_history(metrics: dict) -> None:
    with HISTORY_FILE.open("a") as f:
        entry = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            **{k: v for k, v in metrics.items() if k != "measured_at"},
        }
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


def check_ratchet(current: dict, floor: dict) -> list[str]:
    """Check current metrics against floor. Returns list of failures."""
    failures = []

    # These should only go DOWN
    for key in ["lint_violations", "complexity_violations"]:
        if current.get(key, 0) > floor.get(key, 0):
            failures.append(f"REGRESSION: {key} increased from {floor[key]} to {current[key]}")

    # These should only go UP
    for key in ["test_count"]:
        if current.get(key, 0) < floor.get(key, 0):
            failures.append(f"REGRESSION: {key} decreased from {floor[key]} to {current[key]}")

    # Coverage: only go up
    if current.get("coverage_percent", 0) < floor.get("coverage_percent", 0):
        failures.append(f"REGRESSION: coverage decreased from {floor['coverage_percent']}% to {current['coverage_percent']}%")

    return failures


# ---------------------------------------------------------------------------
# Tech debt prioritization
# ---------------------------------------------------------------------------


def classify_impact(filepath: str, config: dict) -> str:
    """Classify business impact using keyword patterns."""
    fp = filepath.lower()
    for impact, keywords in config.get("impact_keywords", {}).items():
        if any(kw in fp for kw in keywords):
            return impact
    return "default"


def scan_tech_debt(config: dict) -> list[dict]:
    """Scan for tech debt items, ranked by business impact."""
    lang = config.get("language", "python")
    priorities = config.get("priorities", DEFAULT_CONFIG["priorities"])
    suffix = {"python": ".py", "dart": ".dart", "typescript": ".ts"}.get(lang, ".py")
    source_dirs = config.get("source_dir", {"dart": "lib", "typescript": "src"}.get(lang, _detect_source_dir()))

    items = []

    # Complexity scan (Python only for now — AST-based)
    if suffix == ".py":
        for root, dirs, files in os.walk(source_dirs):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", ".venv", "venv")]
            for f in files:
                if not f.endswith(suffix):
                    continue
                path = os.path.join(root, f)
                try:
                    if os.path.getsize(path) > 1_000_000:  # skip files > 1 MB
                        continue
                except OSError:
                    continue
                try:
                    tree = ast.parse(Path(path).read_text())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            cc = 1
                            for child in ast.walk(node):
                                if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.BoolOp)):
                                    cc += 1
                                if isinstance(child, ast.BoolOp):
                                    cc += len(child.values) - 1
                            if cc > 10:
                                impact = classify_impact(path, config)
                                weight = priorities.get(impact, 1.0)
                                effort = 2.5 if cc > 30 else 1.0 if cc > 15 else 0.0
                                score = round(min(10, cc / 5) * weight - effort, 2)
                                items.append({
                                    "file": path,
                                    "category": "complexity",
                                    "description": f"`{node.name}` complexity {cc} (target: 10)",
                                    "impact": impact,
                                    "score": score,
                                })
                except (SyntaxError, UnicodeDecodeError):
                    pass

    # Churn scan (language-agnostic — uses git)
    r = _run(["git", "log", "--since=6 months ago", "--format=", "--name-only", "--", source_dirs])
    churn: dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if line and line.endswith(suffix):
            churn[line] = churn.get(line, 0) + 1

    for filepath, count in sorted(churn.items(), key=lambda x: -x[1])[:15]:
        if count < 15:
            continue
        impact = classify_impact(filepath, config)
        weight = priorities.get(impact, 1.0)
        items.append({
            "file": filepath,
            "category": "churn",
            "description": f"Changed {count}x in 6 months",
            "impact": impact,
            "score": round(min(10, count / 15) * weight - 1.0, 2),
        })

    items.sort(key=lambda x: -x["score"])
    return items


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_report(current: dict, floor: dict | None) -> dict:
    """Build structured report comparing current metrics to floor."""
    metrics = []
    for key, direction in [
        ("lint_violations", "down"),
        ("complexity_violations", "down"),
        ("test_count", "up"),
        ("coverage_percent", "up"),
    ]:
        curr = current.get(key, 0)
        flr = floor.get(key) if floor else None
        delta = None
        ok = True
        if flr is not None:
            delta = curr - flr
            ok = (delta <= 0) if direction == "down" else (delta >= 0)
        metrics.append({
            "metric": key, "current": curr, "floor": flr,
            "delta": delta, "ok": ok, "direction": direction,
        })
    return {
        "status": "pass" if all(m["ok"] for m in metrics) else "fail",
        "metrics": metrics,
        "language": current.get("language", "unknown"),
    }


def print_report(current: dict, floor: dict | None) -> None:
    print("\n=== Quality Ratchet Report ===\n")
    print(f"{'Metric':<25} {'Current':>10} {'Floor':>10} {'Delta':>12}")
    print("-" * 60)

    for key, direction in [
        ("lint_violations", "down"),
        ("complexity_violations", "down"),
        ("test_count", "up"),
        ("coverage_percent", "up"),
    ]:
        curr = current.get(key, 0)
        flr = floor.get(key, "—") if floor else "—"
        if floor and key in floor:
            delta = curr - floor[key]
            ok = (delta <= 0) if direction == "down" else (delta >= 0)
            fmt = f"{delta:+.1f}% {'OK' if ok else 'FAIL'}" if isinstance(curr, float) else f"{delta:+d} {'OK' if ok else 'FAIL'}"
        else:
            fmt = "no floor"
        print(f"  {key:<23} {curr:>10} {str(flr):>10} {fmt:>12}")
    print()


def print_orient(current: dict, debt: list[dict] | None = None) -> None:
    """One-line status for SessionStart hooks."""
    v = current.get("lint_violations", "?")
    t = current.get("test_count", "?")
    c = current.get("coverage_percent", "?")
    print(f"Ratchet: {v} violations | {t} tests | {c}% coverage")
    if debt:
        top = debt[0]
        print(f"Top debt: [{top['impact']}] {top['description'][:55]}")


def print_debt(items: list[dict], filter_impact: str | None = None) -> None:
    filtered = [i for i in items if i["impact"] == filter_impact] if filter_impact else items
    print(f"\n{'Score':>6}  {'Impact':<12} {'Cat':<12} {'File'}")
    print("-" * 75)
    items = filtered
    for item in items[:20]:
        print(f"{item['score']:6.1f}  {item['impact']:<12} {item['category']:<12} {item['file']}")
        print(f"        {item['description']}")
    print()


def print_history() -> None:
    if not HISTORY_FILE.exists():
        print("No history. Run `ratchet measure` at least twice.")
        return
    print(f"\n{'Date':<12} {'Lint':>6} {'Tests':>7} {'Cov':>7} {'Cmplx':>7}")
    print("-" * 45)
    for line in HISTORY_FILE.read_text().strip().splitlines():
        e = json.loads(line)
        print(f"  {e.get('date','?'):<10} {e.get('lint_violations','?'):>6} {e.get('test_count','?'):>7} {str(e.get('coverage_percent','?')):>6}% {e.get('complexity_violations','?'):>7}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _json_mode() -> bool:
    return "--json" in sys.argv


def _output(data: dict) -> None:
    """Output structured JSON (for agents) or fall through to human print."""
    if _json_mode():
        print(json.dumps(data, indent=2, default=str))


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    config = load_config()

    if cmd in ("init", "measure"):
        floor_before = load_state() if cmd == "measure" else None
        current = measure(config)
        save_state(current)
        append_history(current)
        if _json_mode():
            report = build_report(current, floor_before)
            report["command"] = cmd
            _output(report)
        else:
            print_report(current, floor_before)
            if cmd == "init":
                print(f"Baseline saved to {STATE_FILE}")
                print(f"Run `python ratchet.py check` to enforce.")
            else:
                print(f"Floor updated. Quality can only improve from here.")

    elif cmd == "check":
        floor = load_state()
        if not floor:
            if _json_mode():
                _output({"status": "error", "message": "No baseline. Run init first."})
            else:
                print("No baseline. Run `python ratchet.py init` first.")
            sys.exit(1)
        current = measure(config)
        failures = check_ratchet(current, floor)
        if _json_mode():
            report = build_report(current, floor)
            report["command"] = "check"
            report["failures"] = failures
            _output(report)
        else:
            print_report(current, floor)
            if failures:
                print("RATCHET FAILED:")
                for f in failures:
                    print(f"  {f}")
            else:
                print("RATCHET PASSED.")
        if failures:
            sys.exit(1)

    elif cmd == "orient":
        state = load_state()
        if state:
            debt = scan_tech_debt(config)
            if _json_mode():
                _output({
                    "command": "orient",
                    "lint_violations": state.get("lint_violations"),
                    "test_count": state.get("test_count"),
                    "coverage_percent": state.get("coverage_percent"),
                    "top_debt": debt[0] if debt else None,
                })
            else:
                print_orient(state, debt[:1] if debt else None)
        else:
            if _json_mode():
                _output({"command": "orient", "status": "not_initialized"})
            else:
                print("Ratchet: not initialized. Run `python ratchet.py init`")

    elif cmd == "report":
        floor = load_state()
        current = measure(config)
        if _json_mode():
            report = build_report(current, floor)
            report["command"] = "report"
            _output(report)
        else:
            print_report(current, floor)

    elif cmd == "debt":
        filter_impact = None
        if "--growth" in sys.argv:
            filter_impact = "growth"
        elif "--reliability" in sys.argv:
            filter_impact = "reliability"
        elif "--cost" in sys.argv:
            filter_impact = "cost"
        items = scan_tech_debt(config)
        if filter_impact:
            items = [i for i in items if i["impact"] == filter_impact]
        if _json_mode():
            _output({"command": "debt", "filter": filter_impact, "items": items[:20]})
        else:
            print_debt(items, filter_impact)

    elif cmd == "history":
        if _json_mode():
            entries = []
            if HISTORY_FILE.exists():
                for line in HISTORY_FILE.read_text().strip().splitlines():
                    entries.append(json.loads(line))
            _output({"command": "history", "entries": entries})
        else:
            print_history()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
