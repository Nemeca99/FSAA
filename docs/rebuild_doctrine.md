# FSAA_v2 rebuild doctrine (read before changing code)

This tree is **not** a strangler migration or shim layer. It is a **full parallel implementation**: behavior and contracts match the old FSAA/automation stack, but **no file is “the old file with edits.”** Legacy code is **reference only** (read to understand semantics, parity tests, JSONL shapes).

## Non‑negotiables

| Rule | Meaning |
|------|--------|
| **Standalone package** | Everything lives under this repo’s `src/fsaa/`. |
| **No legacy imports** | No `import` from the old FSAA package tree, workspace-only automation scripts, legacy supervisor folders, or Luna/Aria shim trees. |
| **No path cheats** | No `sys.path` hacks, no re-exports of legacy modules, no “thin wrapper” that calls old code. |
| **Workspace only via env** | Paths outside this repo enter only through **`WORKSPACE_ROOT`** and documented env overrides (`FSAA_IPC_SCHEMA`, `FSAA_OBSERVABILITY_DIR`, …). |
| **Preserve behavior, not text** | JSONL formats, guard verdicts, scheduler semantics, audit hashing must stay compatible; **implementation is rewritten**. |
| **Verify gate** | `fsaa verify` green; no forbidden legacy path **strings** in-tree (see `scripts/verify_no_external_roots.py`). |

## What “reference only” means

- **Do:** Open old files **side-by-side** to confirm logic, edge cases, and on-wire formats.
- **Do:** Port algorithms and re-type paths through `FsaaPaths` / `get_paths()`.
- **Don’t:** Copy-paste large chunks and tweak imports.
- **Don’t:** Leave TODOs or stub returns for production paths.

## Copy-paste prompt block (for Cursor / other agents)

Use this **verbatim** when you start a task so the tool optimizes for a **clean twin**, not “minimal diff to legacy”:

---

**FSAA_v2 doctrine — overrides any prior plan:**

- **Goal:** This repo (`FSAA_v2`) is a **complete standalone rebuild** of FSAA. **Legacy trees are reference only** (read for behavior); **they are not dependencies**.
- **Forbidden:** shims, re-exports, `sys.path` hacks, imports or string path references to any legacy sibling tree (old FSAA package, workspace automation dir, legacy supervisor sources).
- **Allowed external context:** `WORKSPACE_ROOT` (and documented `FSAA_*` env vars) only.
- **Deliverable:** Rewritten modules under `fsaa.*`, same observable behavior (logs, guards, supervisor semantics, audit hashes) under tests; **`fsaa verify` passes** with zero forbidden legacy path literals in `FSAA_v2`.
- **Do not** optimize for “minimal disruption to legacy”; optimize for **correct standalone package**.

---

## If the model drifts toward shims

Say explicitly: **“That violates `docs/rebuild_doctrine.md` — no calls into legacy code; port the behavior into `fsaa.*`.”**
