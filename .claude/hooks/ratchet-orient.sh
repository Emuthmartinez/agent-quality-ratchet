#!/bin/bash
# SessionStart hook: Print quality ratchet status.
# Works in Claude Code via hooks. For Codex, read .ratchet-state.json directly.
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" 2>/dev/null
python3 ratchet.py orient 2>/dev/null || true
