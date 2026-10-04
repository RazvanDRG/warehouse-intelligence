#!/usr/bin/env python3
"""Fail when code outside the allowed client files talks to a protected system.

Reads the systems this project builds on from CONNECT.md ("Builds on:"), the door from CLAUDE.md ("Calls ... only from:")
and .claude/guard.json, and checks every system that has "clients"
(the only files allowed to call that system). Any other source file that mentions the system's
URLs or markers (env var names, client class names) is a violation. Catches code written by people
too, not only by Claude.

Copy this file into the project (for example tools/boundary_check.py) and run it in `make check` and CI:
    python tools/boundary_check.py [project-dir]
Exit 0 when clean, 1 with file:line for every violation. Standard library only.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", "bin", "obj", ".next",
             "coverage", ".pytest_cache", ".mypy_cache", "target", ".claude"}
# a mention here is not a second door: tests mock the URL, config and docs describe it
BOUNDARY_ALLOWED = ["tests/*", "*/tests/*", "*test_*.py", "*_test.py", "*.test.ts", "*.spec.ts", "*.test.js",
                    "*config*.py", "*settings*.py", "*config*.json", "*appsettings*.json", "*.env*", "*docker-compose*.yml",
                    "*compose*.yml", "*.md", ".system-changes/*"]  # prepared copies for the other system, not a door
SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".cs", ".java", ".kt", ".go", ".rs", ".rb", ".php",
              ".sh", ".ps1", ".sql", ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg"}


def load_config(root: Path) -> dict:
    try:
        text = (root / ".claude" / "guard.json").read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(text)
    except ValueError as exc:
        sys.exit(f"boundary_check: .claude/guard.json is not valid JSON ({exc})")


# ---- the link (CONNECT.md) and this system's rules (CLAUDE.md): same parser as the guard, kept in sync by tests

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore") if path.is_file() else ""
    except OSError:
        return ""


CONNECT_DEFAULT = "CONNECT.md"
CONNECT_OLD = "KIT.md"
RULES_FILE = "CLAUDE.md"
THIS_KEYS = ("this system", "ai system", "system")
FIELD = re.compile(r"^\s*(?:[-*]\s*)?\**([A-Za-z][A-Za-z0-9 ()/]*?)\**\s*:\s*(.+?)\s*$")


def real(path) -> Path:
    try:
        return Path(path).resolve()
    except (OSError, RuntimeError):
        return Path(os.path.abspath(path))


def fields(path: Path):
    """('field', value) for each 'Field: value' line. Unfilled <placeholders> are dropped, the rest of the line kept."""
    out = []
    for line in read_text(path).splitlines():
        m = FIELD.match(line)
        value = re.sub(r"<[^>]+>", "", m.group(2)).strip() if m else ""
        if value.strip(" ,;|"):
            out.append((m.group(1).strip().lower(), value))
    return out


def path_globs(value: str):
    """'core/agent/, gateway.py and src/*.ts' -> ['core/agent/**', '**/gateway.py', 'src/*.ts']"""
    out = []
    for token in re.split(r"[,;]\s*|\s+and\s+", value):
        t = token.strip().strip("`'\"").rstrip(". ")
        if not re.fullmatch(r"[\w./*\\-]+", t or "-") or not ("/" in t or "*" in t or re.search(r"\.\w{1,6}$", t)):
            continue
        t = t.replace("\\", "/")
        out.append(t + "**" if t.endswith("/") else t if "/" in t else "**/" + t)
    return out


def looks_like_path(text: str) -> bool:
    """A folder: '../s1', '~/s1', 'C:\\Users\\me\\s1', '/home/me/s1' or 'D:/work/s1'. A name: 'System 1'."""
    return bool(re.match(r"(\.{1,2}[\\/]|~[\\/]?|[A-Za-z]:[\\/]|/)", text)) or (bool(re.search(r"[\\/]", text)) and " " not in text)


def parse_system(value: str):
    """'../s1', '../s1 (read-only)', '../s1; API localhost:8000', or the long form
    'System 1; folder ../s1; API localhost:8000 and api.x.com; only a/client.py may call it; ask'"""
    if re.match(r"^\s*(none|no)\b", value, re.I):
        return None
    parts = [p.strip() for p in value.split(";") if p.strip()]
    if not parts:
        return None
    system = {"name": "", "paths": [], "urls": [], "clients": [], "markers": [], "mode": "ask"}
    first = parts[0].strip("`'\"")  # a path pasted with quotes ("C:\\My Projects\\System1") still counts
    mode = re.search(r"\s*\((read-only|read only|deny|ask)\)\s*$", first, re.I)
    if mode:
        system["mode"] = "ask" if mode.group(1).lower() == "ask" else "deny"
        first = first[:mode.start()].strip().strip("`'\"")
    if looks_like_path(first):
        system["paths"].append(first.strip("`'\""))
    else:
        system["name"] = first
    for part in parts[1:]:
        low = part.lower()
        if low.startswith(("folder", "path")):
            system["paths"] += [p for p in part.split()[1:2]]
        elif low.startswith(("api", "database", "db ", "url")):
            rest = re.sub(r"^(api|database|db|urls?)(\s+(urls?|host|hosts))?\s*:?\s*", "", part, flags=re.I)
            system["urls"] += [u.strip() for u in re.split(r",\s*|\s+and\s+", rest) if u.strip()]
        elif "may call it" in low or low.startswith(("only ", "client")):
            files = re.sub(r"^(only|clients?:?)\s+", "", part, flags=re.I)
            system["clients"] += path_globs(re.sub(r"\s+may call it.*$", "", files, flags=re.I))
        elif low.startswith("markers"):
            system["markers"] += [m.strip() for m in re.split(r"[,\s]+", part)[1:] if m.strip()]
        elif low in ("deny", "read-only", "read only"):
            system["mode"] = "deny"
    return system


def own_rules(folder: Path):
    """Name and API hosts a system states in its own rules (CLAUDE.md, or an older full CONNECT.md)."""
    name, urls = "", []
    for file in (RULES_FILE, CONNECT_DEFAULT):
        for key, value in fields(folder / file):
            if key == "project" and not name:
                name = re.split(r":\s", value)[0].strip()
            elif key in ("api", "api urls", "api hosts"):
                urls += [u.strip(" `.") for u in re.split(r",\s*|\s+and\s+", value) if u.strip(" `.")]
    if not name:
        heading = re.search(r"(?m)^#\s+(.+?)\s*$", read_text(folder / RULES_FILE))
        name = heading.group(1) if heading else folder.name
    return name, urls


def resolve_from(base: Path, value: str) -> Path:
    """A path as written in a Connect file: absolute, '~/...', or relative to the Connect file's folder."""
    path = Path(os.path.expanduser(value.strip().strip("`'\"")))
    return path if path.is_absolute() else Path(base) / path


def this_system(link: Path, root: Path = None) -> Path:
    """The folder the Connect file names as 'This system' (default: the Connect file's own folder)."""
    value = next((v for k, v in fields(link) if k in THIS_KEYS), "")
    folder = resolve_from(link.parent, value) if value else Path(link).parent
    if root is not None and not folder.is_dir():  # Connect copied to another computer: the open project is the system
        folder = Path(root)
    return real(folder)


def parse_connect(path: Path, root: Path = None) -> dict:
    """The Connect file (Kit, This system, Builds on, Plan) plus this system's own rules (its CLAUDE.md),
    in the same shape as guard.json. Paths in it are relative to its own folder. Old full files still work."""
    root = Path(root or Path(path).parent)
    link = fields(path)
    this = this_system(path, root)
    try:
        prefix = this.relative_to(real(root)).as_posix()
        prefix = "" if prefix == "." else prefix + "/"
    except ValueError:
        prefix = ""
    rules = fields(this / RULES_FILE) if real(this / RULES_FILE) != real(path) else []
    cfg = {"critical_paths": [], "db_paths": [], "protected_systems": []}
    doors = []
    for source, pre in ((link, ""), (rules, prefix)):
        for key, value in source:
            if key.startswith("critical"):
                cfg["critical_paths"] += [pre + g for g in path_globs(value)]
            elif key.startswith("database files"):
                cfg["db_paths"] += [pre + g for g in path_globs(value)]
            elif key.startswith("calls") and key.endswith("only from"):
                doors.append((key[5:-9].strip(), [pre + g for g in path_globs(value)]))
            elif key.startswith("builds on") and source is link:
                system = parse_system(value)
                if system:
                    cfg["protected_systems"].append(system)
    for system in cfg["protected_systems"]:
        system["paths"] = [str(real(resolve_from(Path(path).parent, p))) for p in system["paths"]]
        if system["paths"]:
            name, urls = own_rules(Path(system["paths"][0]))
            system["name"] = system["name"] or name
            system["urls"] += [u for u in urls if u not in system["urls"]]
        system["name"] = system["name"] or "another system"
    for who, globs in doors:
        named = [s for s in cfg["protected_systems"] if who and who in s["name"].lower()]
        for system in named or cfg["protected_systems"]:
            system["clients"] += globs
    return {k: v for k, v in cfg.items() if v}


def matches(rel: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/").lstrip("/")
    return fnmatch.fnmatch(rel, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:]))


def url_pattern(url: str) -> str:
    host, _, port = re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/")[0].partition(":")
    return r"(?<![\w.-])" + re.escape(host) + (r":" + re.escape(port) + r"(?!\d)" if port else r"(?::\d+)?") + r"(?![\w.-])"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    config = load_config(root)
    link = root / str(config.get("connect") or (CONNECT_DEFAULT if (root / CONNECT_DEFAULT).is_file() or not (root / CONNECT_OLD).is_file() else CONNECT_OLD))
    connected = parse_connect(link, root)
    systems = [s for s in (config.get("protected_systems", []) or []) + connected.get("protected_systems", [])
               if isinstance(s, dict) and s.get("clients")]
    if not systems:
        print("boundary_check: no protected system lists \"clients\"; nothing to check")
        return 0
    checks = []
    for s in systems:
        needles = [re.compile(url_pattern(u), re.I) for u in s.get("urls", []) if isinstance(u, str) and u.strip()]
        needles += [re.compile(re.escape(m)) for m in s.get("markers", []) if isinstance(m, str) and len(m) > 2]
        checks.append((s.get("name", "another system"), list(s["clients"]) + list(s.get("allow_paths", [])), needles))
    violations = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath, name)
            rel = path.relative_to(root).as_posix()
            if path.suffix.lower() not in SOURCE_EXT or rel == "tools/boundary_check.py":
                continue
            try:
                lines = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
            except OSError:
                continue
            if any(fnmatch.fnmatch(rel.lower(), p) for p in BOUNDARY_ALLOWED):
                continue
            for system, clients, needles in checks:
                if any(matches(rel, c) for c in clients):
                    continue
                for number, line in enumerate(lines, 1):
                    if any(n.search(line) for n in needles):
                        print(f"{rel}:{number}: talks to {system} outside its clients ({', '.join(clients)}): {line.strip()[:100]}")
                        violations += 1
    if violations:
        print(f"\nboundary_check: {violations} direct reference(s). Route these calls through the allowed client.")
        return 1
    print("boundary_check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
