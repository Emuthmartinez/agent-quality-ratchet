---
name: quality-ratchet
description: Enforce code quality floors that only improve. Measure violations, tests, coverage, complexity — fail if any metric regresses. Includes business-impact tech debt prioritization. Works with any language (Python, Dart, TypeScript).
user-invocable: true
---

You are the quality enforcement system for this project.

## Outcomes You Achieve

### Prevent quality regression
Before any handoff, PR, or task completion, verify quality hasn't regressed:
```bash
python ratchet.py check --json
```
If `status` is `"fail"`, fix the regressions before proceeding. Never skip this gate.

### Lock in improvements
After you've improved code quality (fixed violations, added tests, increased coverage), permanently lower the floor:
```bash
python ratchet.py measure --json
```

### Find highest-impact work
When deciding what to work on, prioritize by business impact:
```bash
python ratchet.py debt --json             # All items ranked by score
python ratchet.py debt --growth --json    # Growth-path items only
```
Use the structured output to identify the file and function to fix next.

### Understand current state
At session start or when you need context:
```bash
python ratchet.py orient --json
```

### Initialize a new project
First time in a project:
```bash
python ratchet.py init --json
```

## Capability Map

| Agent Outcome | Command | Structured Output |
|---------------|---------|-------------------|
| Check for regressions | `check --json` | `{status, metrics[], failures[]}` |
| Lock in improvements | `measure --json` | `{status, metrics[]}` |
| Find impactful debt | `debt --json` | `{items[{file, category, impact, score, description}]}` |
| Get current status | `orient --json` | `{lint_violations, test_count, coverage_percent, top_debt}` |
| Full comparison | `report --json` | `{status, metrics[{metric, current, floor, delta, ok}]}` |
| View trend | `history --json` | `{entries[{date, lint_violations, test_count, ...}]}` |
| Set baseline | `init --json` | `{status, metrics[]}` |

## How the Ratchet Works

1. Floors stored in `.ratchet-state.json` — machine-enforced minimums
2. Config in `.ratchet.yaml` — language, metrics, priority weights
3. Violations can only go DOWN, tests/coverage can only go UP
4. All commands accept `--json` for structured output

## Decision Guide

- **Before handoff** → `check`
- **After improvements** → `measure`
- **What to work on** → `debt --growth`
- **Session start** → `orient`

## Codex Usage

Codex cannot run hooks. Instead:
1. Read `.ratchet-state.json` for current floors
2. After changes: `python ratchet.py check`
3. If regressed: fix before submitting
4. After fixing: `python ratchet.py measure`
