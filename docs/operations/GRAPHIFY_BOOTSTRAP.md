# Graphify Bootstrap — New Repo or All Projects

**Status:** operational  
**Owner:** platform maintainer  
**Reference repo:** `D:\sanmitra_unified-Next` (canonical graphify wiring)

Use this when opening a **new** codebase in Cursor (NexTrade, SSDV, RagaAware, another SanMitra clone, etc.) so agents query the knowledge graph before grep/read.

---

## 1. One-time: Cursor User Rule (all projects)

Paste into **Cursor → Settings → Rules → User Rules** so every chat prefers graphify when a graph exists:

```markdown
## graphify (all projects)

Before Read/Grep/Glob/Bash to explore source code, run graphify when `graphify-out/graph.json` exists in the workspace root:
- `graphify query "<question>"`
- `graphify path "<A>" "<B>"`
- `graphify explain "<concept>"`

Skip graphify only when the graph does not exist yet, the user says not to use it, or you already ran graphify this turn for the same question.

After editing code, run `graphify update .` in that repo root.

Include the same instruction in every subagent prompt that explores code.
```

This complements (does not replace) per-repo `.cursor/rules/graphify.mdc`.

---

## 2. Per-repo bootstrap (5 minutes)

From the **project root** (example: `D:\my-project`):

### Step A — Install CLI (once per machine)

```powershell
pip install graphifyy
# or: uv tool install graphifyy
graphify --help
```

SanMitra uses: `C:\Users\Muralidhar\.local\bin\graphify.EXE` (also wired in `.claude/settings.json` hook-guard).

### Step B — Build the graph

```powershell
cd D:\my-project
graphify . --update
# First time on a large repo: graphify . --mode deep   (slower, richer INFERRED edges)
```

Outputs:

| Path | Purpose |
| --- | --- |
| `graphify-out/graph.json` | Query/path/explain input |
| `graphify-out/GRAPH_REPORT.md` | Broad architecture (fallback only) |
| `graphify-out/wiki/index.md` | Agent navigation (preferred over raw grep) |

Add `graphify-out/` to `.gitignore` if the graph is large and regenerated locally/CI; **keep** the rule files in git.

### Step C — Copy Cursor rule

```powershell
mkdir .cursor\rules -Force
copy D:\sanmitra_unified-Next\docs\templates\cursor-graphify.mdc .cursor\rules\graphify.mdc
```

Or symlink if you maintain one golden template.

### Step D — Optional agent policy files

For repos that use Claude Code / Codex / Copilot instructions, copy the short block from SanMitra:

| File | Action |
| --- | --- |
| `AGENTS.md` | Add `## graphify` section (see SanMitra `AGENTS.md` tail) |
| `CLAUDE.md` | Same short rules |
| `.github/copilot-instructions.md` | Same short rules |
| `.agents/rules/graphify.md` | Claude Code / Antigravity always-on rule |

SanMitra canonical copies live under `D:\sanmitra_unified-Next\`.

### Step E — Verify

```powershell
graphify query "How is authentication handled?"
graphify path "login" "database"
```

Open the repo in Cursor; confirm **Rules** shows `graphify` as always applied.

---

## 3. Daily discipline

| When | Command |
| --- | --- |
| After code edits in a session | `graphify update .` |
| Architecture / "where is X?" question | `graphify query "..."` first |
| Relationship between two symbols | `graphify path "A" "B"` |
| Unfamiliar module name | `graphify explain "ModuleName"` |

Do **not** treat dirty `graphify-out/` as a reason to skip graphify — only skip when output is known wrong or user opts out.

---

## 4. Subagent prompt snippet

When spawning Task/explore agents, paste:

```text
MANDATORY graphify: Before Read/Grep/Glob, run graphify query/path/explain when graphify-out/graph.json exists. After code changes, graphify update .
```

---

## 5. SanMitra unified-Next (this repo)

Already wired:

- `.cursor/rules/graphify.mdc` (always apply)
- `AGENTS.md`, `CLAUDE.md`, `.agents/rules/graphify.md`
- Graph at `graphify-out/` (regenerate with `graphify update .` after edits)

Other D: projects must use **their own** `.venv` (see `.cursor/rules/python-venv.mdc`) — do not share global Python with SanMitra.

---

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `graphify-out/graph.json` missing | Run `graphify .` or `graphify update .` from repo root |
| Agent still greps first | Confirm User Rule + `.cursor/rules/graphify.mdc`; restart chat |
| Graph stale after big refactor | `graphify . --update` or full `graphify .` |
| CLI not found | Install `graphifyy`; ensure `graphify` is on PATH |

---

## Related

- Skill: `C:\Users\Muralidhar\.agents\skills\graphify\SKILL.md`
- Template: `docs/templates/cursor-graphify.mdc`
- SanMitra policy: `AGENTS.md` § graphify
