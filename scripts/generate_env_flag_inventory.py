"""Generate `docs/ENV-FLAGS.md` — the COMPLETE env-flag inventory, mechanically.

Why this exists
---------------
`CLAUDE.md`'s env-flag table documents the flags that recent ROUNDS touched — 55 of
them. Measured 2026-08-15 at R349, `app/` reads **~190** environment flags, and **50
default-ON flags that shape the wire answer or its references are absent from that
table** (`REGENOLD_ADAPTIVE_REF_CLAMP`, `REGENOLD_QA_REF_BUDGET`,
`REGENOLD_REFS_RECONCILE`, `REGENOLD_PROSE_NAMED_REFS`, …). Since
`railway.toml [deploy.envs]` has never applied, **the code default is what the
deployed service runs** — so an undocumented default-ON flag is live behaviour
nobody has written down.

Inlining 190 rows into `CLAUDE.md` would bloat a file that is loaded into every
session. So the load-bearing subset stays in `CLAUDE.md` and the exhaustive
inventory lives here, regenerated on demand:

    py -3.12 scripts/generate_env_flag_inventory.py

This script is pure-stdlib and does a STATIC read — it never imports `app`, so it
cannot be fooled by import-time side effects and needs no environment.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
OUT = ROOT / "docs" / "ENV-FLAGS.md"

TRUTHY = {"1", "true", "yes", "on"}
FALSEY = {"0", "false", "no", "off", ""}
PREFIXES = ("REGENOLD_", "P2P_", "NEO4J_", "GROUNDED_", "BEDROCK_", "AWS_", "COHERE_",
            "OPENAI_", "GROQ_", "GEMINI_", "WRAPPER_")

# Areas, in the order they appear in the request pipeline.
AREAS: list[tuple[str, str]] = [
    ("app/routes", "Route — scope gate, citation post-passes, response shaping"),
    ("app/engines", "Engine — retrieval, rerank, expansion, Stage-2 generation"),
    ("app/data", "Data — knowledge base, BM25, prompts"),
    ("app/llm", "LLM transport — providers, fallback chains, judges"),
    ("app/graph", "Graph — Neo4j / embedded backend"),
    ("app/integrations", "Integrations — scope classifier, models, email"),
    ("app/evidence", "Evidence store — audit chain"),
    ("app", "Application — boot, health, misc"),
]


class Hit:
    __slots__ = ("flag", "default", "path", "line", "scope")

    def __init__(self, flag: str, default: str | None, path: str, line: int, scope: str):
        self.flag, self.default = flag, default
        self.path, self.line, self.scope = path, line, scope

    @property
    def state(self) -> str:
        d = self.default
        if d is None:
            return "*required*"
        if d.lower() in TRUTHY:
            return "**ON**"
        if d.lower() in FALSEY:
            return "OFF" if d != "" else "*(empty)*"
        return f"`{d}`"


def _literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        return None if node.value is None else str(node.value)
    return None


def scan(path: pathlib.Path) -> list[Hit]:
    """Find every getenv/environ.get whose flag name resolves to a literal."""
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    # module-level `_ENV_CONST = "FLAG_NAME"` indirection
    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            val = _literal(node.value)
            if isinstance(tgt, ast.Name) and val and val.isupper() and val.startswith(PREFIXES):
                consts[tgt.id] = val

    # map line -> enclosing def, so a reader can jump to the gate helper
    scopes: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((node.lineno, node.end_lineno or node.lineno, node.name))
    scopes.sort(key=lambda s: s[1] - s[0])  # innermost wins

    def scope_of(line: int) -> str:
        for lo, hi, name in scopes:
            if lo <= line <= hi:
                return f"`{name}()`"
        return "module level"

    hits: list[Hit] = []
    rel = path.relative_to(ROOT).as_posix()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        fn = node.func
        is_getenv = isinstance(fn, ast.Attribute) and (
            fn.attr == "getenv"
            or (fn.attr == "get" and isinstance(fn.value, ast.Attribute)
                and fn.value.attr == "environ")
        )
        if not is_getenv:
            continue
        first = node.args[0]
        flag = _literal(first)
        if flag is None and isinstance(first, ast.Name):
            flag = consts.get(first.id)
        if not flag or not flag.startswith(PREFIXES):
            continue
        default = _literal(node.args[1]) if len(node.args) > 1 else None
        hits.append(Hit(flag, default, rel, node.lineno, scope_of(node.lineno)))
    return hits


def area_of(rel: str) -> str:
    for prefix, label in AREAS:
        if rel.startswith(prefix + "/"):
            return label
    return "Other"


def main() -> int:
    all_hits: list[Hit] = []
    for py in sorted(APP.rglob("*.py")):
        all_hits.extend(scan(py))

    # collapse to one row per flag, keeping every distinct default seen
    by_flag: dict[str, list[Hit]] = {}
    for h in all_hits:
        by_flag.setdefault(h.flag, []).append(h)

    documented = set(
        re.findall(r"\|\s*`([A-Z][A-Z0-9_]+)`\s*\|", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    )

    conflicts = {
        f: sorted({h.default for h in hs}, key=lambda d: (d is None, d or ""))
        for f, hs in by_flag.items()
        if len({h.default for h in hs}) > 1
    }

    on_undocumented = sorted(
        f for f, hs in by_flag.items()
        if f not in documented and any((h.default or "").lower() in TRUTHY for h in hs)
    )

    lines: list[str] = []
    add = lines.append
    add("# Environment flag inventory — every flag `app/` reads")
    add("")
    add("**Generated** by `scripts/generate_env_flag_inventory.py`. Do not hand-edit —")
    add("regenerate instead. `CLAUDE.md`'s env table stays the curated, load-bearing")
    add("subset with the measurement history; this file is the exhaustive index.")
    add("")
    add("⚠ **The code default is what the deployed service runs.**")
    add("`railway.toml [deploy.envs]` has never applied (Railway's `[deploy]` schema has")
    add("no `envs` key), and `.env` is gitignored so the container ships no dotenv. A")
    add("Railway *service variable* set from the dashboard overrides these and is invisible")
    add("here — that is the only override path.")
    add("")
    add(f"**{len(by_flag)}** flags read across `app/`. "
        f"**{len(documented & set(by_flag))}** appear in the `CLAUDE.md` table. "
        f"**{len(on_undocumented)}** are default-ON and undocumented there.")
    add("")

    if conflicts:
        add("## ⚠ Flags read with MORE THAN ONE default")
        add("")
        add("Two call sites disagreeing about a default is the *one concept, two")
        add("definitions* defect — whichever site runs first decides the behaviour.")
        add("")
        add("| Flag | Defaults seen | Sites |")
        add("| --- | --- | --- |")
        for f in sorted(conflicts):
            sites = ", ".join(f"`{h.path}:{h.line}`" for h in by_flag[f])
            vals = ", ".join(f"`{v!r}`" for v in conflicts[f])
            add(f"| `{f}` | {vals} | {sites} |")
        add("")

    if on_undocumented:
        add("## Default-ON and absent from the `CLAUDE.md` table")
        add("")
        add("Each of these shapes live behaviour on every request with no entry in the")
        add("curated table. Listed so the gap is explicit rather than implied.")
        add("")
        add(", ".join(f"`{f}`" for f in on_undocumented))
        add("")

    add("## Full inventory, by pipeline stage")
    add("")
    seen_area: set[str] = set()
    for _, label in AREAS:
        rows = sorted(
            (f for f in by_flag if area_of(by_flag[f][0].path) == label),
            key=str.lower,
        )
        rows = [f for f in rows if f not in seen_area]
        if not rows:
            continue
        seen_area.update(rows)
        add(f"### {label}")
        add("")
        add("| Flag | Default | Read at | In `CLAUDE.md` |")
        add("| --- | --- | --- | --- |")
        for f in rows:
            hs = by_flag[f]
            h = hs[0]
            where = f"`{h.path}:{h.line}` {h.scope}"
            if len(hs) > 1:
                where += f" *(+{len(hs) - 1} more)*"
            add(f"| `{f}` | {h.state} | {where} | {'yes' if f in documented else '—'} |")
        add("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(by_flag)} flags, "
          f"{len(on_undocumented)} default-ON undocumented, {len(conflicts)} default conflicts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
