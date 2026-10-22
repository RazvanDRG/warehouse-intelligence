---
name: day
description: Start a planned day from the project plan (docs/plan.md, a copy of the Word or PDF named in CONNECT.md). Loads only that day.
argument-hint: "[week] [day, e.g. 1 Mon or 3]"
disable-model-invocation: true
---
1. Run `python ~/.claude/dev-kit/hooks/plan_sync.py` (`py -3` on Windows if `python` is missing). It refreshes `docs/plan.md` if the plan changed. If it says "needs Claude", do what its second line says first.
2. List the headings only: `grep -n "^#" docs/plan.md`. Find week "$0" and day "$1" there (the plan may say Week/Day or Săptămâna/Ziua), then read only the lines of that day's section.
3. Read the last entry of `docs/progress.md` if it is not already in context.
4. Reply in at most 6 lines: the task, its size (S, M, L), the workflow (/quick, /feature, /design, /fix, /db-change) and the user decisions it involves. For medium or high risk (database, money or stock, auth, contracts, System 1, CI, deploys), offer a task file (/task): the day's text gives what we're building and when it's done. Otherwise a short plan.
5. Ask with AskUserQuestion before changing anything: Go / Change the plan / Explain more.
