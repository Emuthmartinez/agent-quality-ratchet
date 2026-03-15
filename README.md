# Agent Quality Ratchet

**Code quality that only goes up.** A language-agnostic quality enforcement tool for AI-assisted development.

Measures code quality metrics, stores floors, and fails if quality regresses. Works with Claude Code (hooks + skills) and Codex (scripts + config). All commands support `--json` for structured output, making the tool agent-native.

## How It Works

```
measure → floor → enforce → improve → re-measure (floor drops permanently)
```

1. **Measure** current violations, test count, coverage, complexity
2. **Store** as floor in `.ratchet-state.json`
3. **Enforce** on every session/PR — fail if any metric regresses
4. **Improve** code quality during normal work
5. **Re-measure** to lock in improvements as the new floor

Violations can only go **down**. Tests can only go **up**. Coverage can only go **up**.

## Quick Start

```bash
# Copy ratchet.py to your project root (single file, zero dependencies)
cp ratchet.py /path/to/your/project/

# Initialize (measures current state as baseline)
python ratchet.py init

# Check (fails if quality regressed)
python ratchet.py check

# After improvements, lower the floor
python ratchet.py measure

# See what to work on (ranked by business impact)
python ratchet.py debt

# Weekly trend report
python ratchet.py report
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
#     ...
#   ],
#   "failures": []
# }

python ratchet.py debt --growth --json
# {
#   "command": "debt",
#   "filter": "growth",
#   "items": [
#     {"file": "app/services/onboarding.py", "category": "complexity", "impact": "growth", "score": 17.0, ...}
#   ]
# }
```

### Capability Map

| Agent Outcome | Command | What It Returns |
|---------------|---------|-----------------|
| Check for regressions | `check --json` | Pass/fail with per-metric deltas |
| Lock in improvements | `measure --json` | New floor values |
| Find impactful debt | `debt --json` | Ranked items with file, function, score |
| Get current status | `orient --json` | Violations, tests, coverage, top debt |
| Full comparison | `report --json` | Current vs floor for all metrics |
| View trend | `history --json` | All historical entries |

## Configuration

Create `.ratchet.yaml` in your project root:

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
    threshold: 15
    direction: down

# Optional: business-impact weighting for tech debt prioritization
priorities:
  growth: 3.0           # paths matching these keywords get this weight
  reliability: 2.0
  cost: 1.5
  retention: 2.0
  default: 1.0

# Optional: keyword-to-impact mapping (content-based, not hardcoded paths)
impact_keywords:
  growth: [onboarding, funnel, activation, signup, registration]
  reliability: [chat, recommendation, generation, streaming]
  cost: [model, embedding, openai, anthropic, ai_service]
  retention: [notification, engagement, daily, weekly]
```

## Claude Code Integration

### As a Skill (recommended)

Copy `.claude/skills/quality-ratchet/SKILL.md` to your project. Then:

```
/quality-ratchet          # Interactive — shows status, suggests actions
```

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

Every session starts with quality awareness:
```
Ratchet: 0 violations | 5567 tests | 53% coverage
Top debt: [growth] _regenerate_narratives complexity 56
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

| Language | Lint Tool | Test Tool | Coverage | Complexity |
|----------|-----------|-----------|----------|------------|
| Python | ruff | pytest | pytest-cov | ruff C90 |
| Dart | dart analyze | flutter test | lcov | dart analyze |
| TypeScript | eslint | jest/vitest | istanbul | eslint complexity |

## Files

| File | Purpose | Versioned? |
|------|---------|------------|
| `.ratchet.yaml` | Configuration (language, metrics, priorities) | Yes |
| `.ratchet-state.json` | Enforced floors (machine-updated) | Yes |
| `.ratchet-history.jsonl` | Weekly trend data | Optional |
| `ratchet.py` | Core engine (single file, zero deps) | Yes |

## Design Principles

1. **Single file, zero dependencies** — `ratchet.py` runs with just Python 3.10+ stdlib
2. **Agent-native** — all commands support `--json` for structured output
3. **Language tools are external** — ratchet calls ruff/eslint/etc. as subprocesses
4. **Config over code** — `.ratchet.yaml` defines what to measure
5. **Floors are monotonic** — violations down, tests up, coverage up. Never backwards.
6. **Business-aware** — tech debt ranked by impact, not just severity

## License

MIT
