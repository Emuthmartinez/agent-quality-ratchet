---
name: quality-ratchet
description: Enforce code quality floors that only improve. Measure violations, tests, coverage, complexity — fail if any metric regresses. Includes business-impact tech debt prioritization. Works with any language (Python, Dart, TypeScript, Ruby, Go).
user-invocable: true
---

You are the quality enforcement system for this project.

## Commands

### Initialize (first time)
```bash
python ratchet.py init
```
Measures current quality and saves as baseline floor.

### Check (mandatory before handoff)
```bash
python ratchet.py check
```
Fails if any metric regressed below the floor.

### Measure (after improvements)
```bash
python ratchet.py measure
```
Re-measures and lowers the floor permanently.

### Orient (session start)
```bash
python ratchet.py orient
```
One-line status: violations, tests, coverage + top debt item.

### Tech Debt (prioritized by business impact)
```bash
python ratchet.py debt            # All items ranked by score
python ratchet.py debt --growth   # Growth-path items only
```

### Report (full comparison)
```bash
python ratchet.py report
```

### History (trend over time)
```bash
python ratchet.py history
```

## How the Ratchet Works

1. Floors stored in `.ratchet-state.json` — machine-enforced minimums
2. Config in `.ratchet.yaml` — language, metrics, priority weights
3. Violations can only go DOWN, tests/coverage can only go UP

## Configuration (.ratchet.yaml)

```yaml
language: python  # python | dart | typescript

metrics:
  lint_violations:
    tool: ruff
    direction: down
  test_count:
    tool: pytest
    direction: up
  coverage:
    tool: pytest-cov
    direction: up
  complexity:
    tool: ruff-c90
    threshold: 15
    direction: down

priorities:
  growth: 3.0
  reliability: 2.0
  cost: 1.5
  default: 1.0

impact_keywords:
  growth: [onboarding, funnel, activation]
  reliability: [chat, recommendation]
```

## Codex Usage

Codex cannot run hooks. Instead:
1. Read `.ratchet-state.json` for current floors
2. After changes: `python ratchet.py check`
3. If regressed: fix before submitting
4. After fixing: `python ratchet.py measure`
