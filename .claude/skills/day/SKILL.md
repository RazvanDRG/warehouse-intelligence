---
name: day
description: Start a planned day from the project plan (docs/plan.md, a copy of the Word or PDF named in CONNECT.md). Loads only that day.
argument-hint: "[week] [day, e.g. 1 Mon or 3; empty = the next day from the last handoff]"
disable-model-invocation: true
---
1. Run `python ~/.claude/dev-kit/hooks/plan_sync.py` (`py -3` on Windows if `python` is missing). It refreshes `docs/plan.md` if the plan changed. If it says "needs Claude", do what its second line says first.
2. List the headings only: `grep -n "^#" docs/plan.md`. Which day: week "$0" and day "$1" when given; otherwise the `next` day on the `Plan:` line of the last entry in `docs/progress.md` (say which day you picked and why). Find it there (the plan may say Week/Day or Săptămâna/Ziua), then read only the lines of that day's section.
3. Read the last entry of `docs/progress.md` if it is not already in context.
4. Follow-ups for this day: `grep -n -A3 "Follow-ups" docs/tasks/*.md` and keep the lines whose target is this day (by its name, like "Week 2 Wed", or its code, like d3.w2).
5. Reply in at most 6 lines: the task, its size (S, M, L), the workflow (/quick, /feature, /design, /fix, /db-change) and the user decisions it involves. Otherwise a short plan.
   For medium or high risk (database, money or stock, auth, contracts, the system it builds on, CI, deploys), end with the full task line in a code block, ready to paste, one line:
   `/task <Week N Day> (d<day>.w<week>): <what the day builds, in plain words>. <where: folders, from the architecture section>. <the follow-ups from step 4>. <the limits from CLAUDE.md that apply: Never and Always ask before lines, read-only systems, where tests run>.`
   The code: w is the week number, d the day's number in that week (Mon 1 to Sun 7, or the plan's own day number).
6. Ask with AskUserQuestion before changing anything: Go / Change the plan / Explain more. On Go with a task line: kit commands run only when the user types them, so say in one line: type /task, pick it from the list, then paste the rest of the line.
