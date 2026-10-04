---
name: start
description: Start a work session on Warehouse Intelligence with only the context it needs.
argument-hint: "[what to work on, optional]"
disable-model-invocation: true
---
1. The last handoff note is usually already in context (loaded at session start). Only if it is not, read the last entry of `docs/progress.md` (`tail -n 20`).
2. Task: "$ARGUMENTS". If empty, propose the next step from the progress entry and the current focus in CLAUDE.md. If `docs/plan.md` exists (the plan named in CONNECT.md), list its headings (`grep -n "^#" docs/plan.md`) and read only the section the next step belongs to, never the whole plan.
3. Size it (S, M, L, bug, database) and name the workflow: /quick, /feature, /design, /fix or /db-change.
4. Name any user decisions it touches, using the Kit rules in CLAUDE.md and the systems in CONNECT.md: critical files, databases, the system it builds on, contracts.
5. Reply in at most 6 lines and wait for "go".
