---
name: start
description: Start a work session on Warehouse Intelligence with only the context it needs.
argument-hint: "[what to work on, optional]"
disable-model-invocation: true
---
0. Git check: `git fetch origin -q` (gets the latest state from GitHub, changes nothing locally), then `git status -sb`. If this branch is behind origin, say so first and ask with AskUserQuestion: Update with `git pull --ff-only` (recommended) / Continue as it is / Explain more. If `.claude/current-task.json` exists and its branch is not the current one, say so: its scope is not enforced here.
1. The last handoff note is usually already in context (loaded at session start). Only if it is not, read the last entry of `docs/progress.md` (`tail -n 20`).
2. Task: "$ARGUMENTS". If empty and there is a current task, continue it: read its contract (docs/tasks/<id>.md) and name the next unmet criterion. Otherwise propose the next step: the `next` day on the `Plan:` line of the last progress entry when there is one (name the week and day), else the progress entry and the current focus in CLAUDE.md. If `docs/plan.md` exists (the plan named in CONNECT.md), list its headings (`grep -n "^#" docs/plan.md`) and read only the section the next step belongs to, never the whole plan. Same for `docs/architecture.md`: only the section that step builds.
3. Size it (S, M, L, bug, database) and name the workflow: /quick, /feature, /design, /fix or /db-change. Offer a task file (/task) only for medium or high risk (database, money or stock, auth, contracts, System 1, CI, deploys); otherwise a short plan.
4. Name any user decisions it touches, using the Kit rules in CLAUDE.md and the systems in CONNECT.md: critical files, databases, the system it builds on, contracts.
5. Reply in at most 6 lines, then ask with AskUserQuestion: Go / Pick another task / Explain more.
