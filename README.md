# Agent Quality Ratchet

**Code quality that only goes up.** A language-agnostic quality enforcement tool for AI-assisted development.

Measures code quality metrics, stores floors, and fails if quality regresses. Works with Claude Code (hooks + skills) and Codex (scripts + config). All commands support `--json` for structured output, making the tool agent-native.

## Install

**Option A: Copy one file (recommended)**

```bash
# From inside your project root
curl -o ratchet.py https://raw.githubusercontent.com/Emuthmartinez/agent-quality-ratchet/main/ratchet.py
```

**Option B: Clone the repo**

```bash
git clone https://github.com/Emuthmartinez/agent-quality-ratchet.git
cp agent-quality-ratchet/ratchet.py /path/to/your/project/
```

**Option C: Full Claude Code integration**

```bash
# Copy the engine
curl -o ratchet.py https://raw.githubusercontent.com/Emuthmartinez/agent-quality-ratchet/main/ratchet.py

# Copy the Claude Code skill (enables /quality-ratchet command)
mkdir -p .claude/skills/quality-ratchet
curl -o .claude/skills/quality-ratchet/SKILL.md \
  https://raw.githubusercontent.com/Emuthmartinez/agent-quality-ratchet/main/.claude/skills/quality-ratchet/SKILL.md

# Copy the SessionStart hook (shows quality status every session)
mkdir -p .claude/hooks
curl -o .claude/hooks/ratchet-orient.sh \
  https://raw.githubusercontent.com/Emuthmartinez/agent-quality-ratchet/main/.claude/hooks/ratchet-orient.sh
```

Then add the hook to `.claude/settings.json` (see [SessionStart Hook](#as-a-sessionstart-hook) below).

### Requirements

- **Python 3.10+** (stdlib only — zero pip dependencies)
- Your project's language tools installed separately:
  - Python: `ruff`, `pytest`, `pytest-cov`
  - Dart: `dart`, `flutter`
  - TypeScript: `eslint`, `jest` (via `npx`)

## How It Works

```
init → floor → enforce → improve → measure (floor tightens permanently)
```

1. **Init** — measure current violations, tests, coverage, complexity as baseline
2. **Enforce** — `check` fails if any metric regresses below the floor
3. **Improve** — fix violations, add tests during normal work
4. **Tighten** — `measure` locks in improvements as the new floor

Violations can only go **down**. Tests can only go **up**. Coverage can only go **up**.

## Usage

```bash
python ratchet.py init              # Measure baseline (first time)
python ratchet.py check             # Fail if quality regressed (mandatory gate)
python ratchet.py measure           # Re-measure and tighten floors
python ratchet.py orient            # One-line status (for hooks)
python ratchet.py report            # Full current vs floor comparison
python ratchet.py debt              # Tech debt ranked by business impact
python ratchet.py debt --growth     # Growth-path items only
python ratchet.py debt --reliability # Reliability items only
python ratchet.py history           # Trend over time

# Add --json to any command for structured output
python ratchet.py check --json
python ratchet.py debt --growth --json
```

### Workflow

```bash
# 1. First time in a project
python ratchet.py init

# 2. Before every PR/handoff (mandatory)
python ratchet.py check     # exits non-zero if regressed

# 3. After you fix violations or add tests
python ratchet.py measure   # tightens the floor

# 4. Find what to work on next
python ratchet.py debt --growth
```

## Agent-Native Design

Every command supports `--json` for structured output that agents can consume programmatically:

```bash
python ratchet.py check --json
# {
#   "status": "pass",
#   "command": "check",
#   "metrics": [
#     {"metric": "lint_violations", "current": 0, "floor": 0, "delta": 0, "ok": true},
#     {"metric": "test_count", "current": 5590, "floor": 5567, "delta": 23, "ok": true}
#   ],
#   "failures": []
# }

python ratchet.py debt --growth --json
# {
#   "command": "debt",
#   "filter": "growth",
#   "items": [
#     {"file": "app/services/onboarding.py", "category": "complexity",
#      "impact": "growth", "score": 17.0,
#      "description": "`generate_plan` complexity 30 (target: 10)"}
#   ]
# }

python ratchet.py orient --json
# {
#   "command": "orient",
#   "lint_violations": 0,
#   "test_count": 5590,
#   "coverage_percent": 53.0,
#   "top_debt": {"file": "...", "impact": "reliability", "score": 18.2, ...}
# }
```

### Capability Map

| Agent Outcome | Command | What It Returns |
|---------------|---------|-----------------|
| Verify no regressions | `check --json` | Pass/fail with per-metric deltas and failures list |
| Tighten floors | `measure --json` | New floor values after improvement |
| Find impactful debt | `debt --json` | Ranked items with file, function, impact, score |
| Session context | `orient --json` | Current violations, tests, coverage, top debt item |
| Full comparison | `report --json` | Current vs floor for all metrics |
| Trend analysis | `history --json` | All historical measurement entries |
| Set baseline | `init --json` | Initial floor values |

## Configuration

Create `.ratchet.yaml` in your project root (optional — sensible defaults are built in):

```yaml
language: python  # python | dart | typescript

metrics:
  lint_violations:
    tool: ruff          # or: dart-analyze, eslint
    direction: down
  test_count:
    tool: pytest        # or: flutter-test, jest
    direction: up
  coverage:
    tool: pytest-cov    # or: lcov, istanbul
    direction: up
  complexity:
    tool: ruff-c90      # or: dart-analyze, eslint-complexity
    threshold: 15       # functions above this complexity are violations
    direction: down

# Business-impact weighting for tech debt prioritization
priorities:
  growth: 3.0           # files matching growth keywords get 3x weight
  reliability: 2.0
  cost: 1.5
  retention: 2.0
  default: 1.0

# Keyword-to-impact mapping (matches against file paths)
impact_keywords:
  growth: [onboarding, funnel, activation, signup, registration]
  reliability: [chat, recommendation, generation, streaming]
  cost: [model, embedding, openai, anthropic, ai_service]
  retention: [notification, engagement, daily, weekly]
```

See `examples/` for ready-to-use configs for Python, Dart, and TypeScript.

### Auto-Detection

Without a `.ratchet.yaml`, the tool:
- Defaults to Python (ruff/pytest/pytest-cov)
- Auto-detects source directory (`app/` > `src/` > `lib/` > `.`)
- Uses sensible defaults for priorities and keywords

## Claude Code Integration

### As a Skill (recommended)

Copy `.claude/skills/quality-ratchet/SKILL.md` to your project's `.claude/skills/quality-ratchet/`. Then use:

```
/quality-ratchet
```

The skill is outcome-oriented — it tells the agent what to achieve, not just what commands to type.

### As a SessionStart Hook

Copy `.claude/hooks/ratchet-orient.sh` and add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/ratchet-orient.sh"
      }]
    }]
  }
}
```

Every Claude Code session starts with quality context:
```
Ratchet: 0 violations | 5567 tests | 53% coverage
Top debt: [growth] generate_first_week_plan complexity 30 (target: 10)
```

### CLAUDE.md Integration

Add to your project's `CLAUDE.md`:

```markdown
## Quality Ratchet
- Before handoff: `python ratchet.py check` (must pass)
- After improvements: `python ratchet.py measure`
- For prioritization: `python ratchet.py debt --growth`
- All commands support `--json` for structured output
```

## Codex Integration

Codex can't run hooks, but it CAN:

1. **Read** `.ratchet-state.json` for current floors
2. **Read** `.ratchet.yaml` for configuration
3. **Run** `python ratchet.py check` after changes
4. **Run** `python ratchet.py debt --growth` for prioritization

Add to your `AGENTS.md`:

```markdown
## Quality Ratchet
- Before handoff: `python ratchet.py check` (must pass)
- After improvements: `python ratchet.py measure`
- For prioritization: `python ratchet.py debt`
```

## Supported Languages

| Language | Lint | Tests | Coverage | Complexity |
|----------|------|-------|----------|------------|
| Python | ruff | pytest | pytest-cov | ruff C90 (mccabe) |
| Dart | dart analyze | flutter test | lcov | AST-based |
| TypeScript | eslint | jest | istanbul | eslint complexity |

## Files

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| `ratchet.py` | Core engine (single file, zero deps) | Yes |
| `.ratchet.yaml` | Configuration (language, metrics, priorities) | Yes |
| `.ratchet-state.json` | Enforced floors (auto-updated by measure/init) | Yes |
| `.ratchet-history.jsonl` | Trend data (appended by measure/init) | Optional |

## Design Principles

1. **Single file, zero dependencies** — runs with Python 3.10+ stdlib only
2. **Agent-native** — all commands support `--json` for structured output
3. **Language tools are external** — calls ruff/eslint/dart as subprocesses
4. **Config over code** — `.ratchet.yaml` defines what to measure
5. **Floors are monotonic** — violations down, tests up, coverage up. Never backwards.
6. **Business-aware** — tech debt ranked by impact (growth 3x, reliability 2x), not just severity
7. **Source auto-detection** — finds `app/`, `src/`, `lib/` automatically

## License

MIT
