# Agent Quality Ratchet

**Code quality that only goes up.** A language-agnostic quality enforcement tool for AI-assisted development.

Measures code quality metrics, stores floors, and fails if quality regresses. Works with Claude Code (hooks + skills) and Codex (scripts + config).

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
# Install
pip install agent-quality-ratchet  # or just copy the scripts

# Initialize (measures current state as baseline)
ratchet init

# Check (fails if quality regressed)
ratchet check

# After improvements, lower the floor
ratchet measure

# See what to work on (ranked by business impact)
ratchet debt

# Weekly trend report
ratchet report
```

## Configuration

Create `.ratchet.yaml` in your project root:

```yaml
language: python  # python | dart | typescript | ruby | go

metrics:
  lint_violations:
    tool: ruff          # or: dart-analyze, eslint, rubocop, golangci-lint
    direction: down
  test_count:
    tool: pytest        # or: flutter-test, jest, rspec, go-test
    direction: up
  coverage:
    tool: pytest-cov    # or: lcov, istanbul, simplecov, go-cover
    direction: up
    floor: 50           # optional: minimum acceptable
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

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python ratchet.py orient"
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
| Ruby | rubocop | rspec | simplecov | rubocop Metrics |
| Go | golangci-lint | go test | go cover | gocyclo |

## Files

| File | Purpose | Versioned? |
|------|---------|------------|
| `.ratchet.yaml` | Configuration (language, metrics, priorities) | Yes |
| `.ratchet-state.json` | Enforced floors (machine-updated) | Yes |
| `.ratchet-history.jsonl` | Weekly trend data | Optional |
| `ratchet.py` | Core engine (single file, zero deps) | Yes |

## Design Principles

1. **Single file, zero dependencies** — `ratchet.py` runs with just Python 3.10+ stdlib
2. **Language tools are external** — ratchet calls ruff/eslint/etc. as subprocesses
3. **Config over code** — `.ratchet.yaml` defines what to measure
4. **Floors are monotonic** — violations down, tests up, coverage up. Never backwards.
5. **Business-aware** — tech debt ranked by impact, not just severity

## License

MIT
