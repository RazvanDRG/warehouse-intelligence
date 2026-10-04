# Connect

The links between the kit, the system you build, the system it builds on and your plan. Each line is a path: absolute, or relative to this file's folder. The kit keeps this file on its list (~/.claude/dev-kit/CONNECTIONS.md), so the link works both ways.

- `Kit` is the kit. The installed copy, ~/.claude/dev-kit, works for every project.
- `This system` is the system you build here (the AI system). Its rules are in that folder's CLAUDE.md.
- `Builds on` is the folder of a system it builds on (System 1), one line per system, or `none`. Claude reads, tests and starts it freely and asks before changing it. Add `(read-only)` to forbid changes. Its name and API come from its own CLAUDE.md.
- `Plan` is your plan for this system (Word, PDF, Markdown or text), or `none`. The kit keeps a text copy in docs/plan.md, refreshed whenever the file changes, so /day and /start read one day at a time. It never changes the original.

Kit: C:\Users\razva\.claude\dev-kit
This system: E:\CV-uri\Proiecte CV\warehouse-intelligence
Builds on: E:\CV-uri\Proiecte CV\fastapi-auth-orders; API localhost:8000 and warehouse-api-pzhs.onrender.com
Plan: E:\CV-uri\Proiecte CV\warehouse-intelligence documents\10-Week Plan v2 Warehouse Intelligence.docx
