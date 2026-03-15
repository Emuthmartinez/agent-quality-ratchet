# AGENTS.md

## Quality Ratchet

### Quick Commands
- Check (before handoff): `python ratchet.py check`
- Measure (after improvements): `python ratchet.py measure`
- Orient (session start): `python ratchet.py orient`
- Tech debt: `python ratchet.py debt`
- Growth debt: `python ratchet.py debt --growth`

### Rules
- `python ratchet.py check` is a mandatory gate before task completion
- Violations can only decrease, tests can only increase
- After fixing violations, re-run `python ratchet.py measure` to lower the floor

### Skills
| Skill | Claude Code | Codex |
|-------|-------------|-------|
| **quality-ratchet** | `/quality-ratchet` | read `.claude/skills/quality-ratchet/SKILL.md` then run `python ratchet.py` commands |
