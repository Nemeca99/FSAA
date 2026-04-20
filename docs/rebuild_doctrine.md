# FSAA package rebuild doctrine (read before changing code)

The **`src/fsaa/`** tree is a **standalone implementation**: behavior and contracts match the workspace stack (Luna, automation, observability), but **package code must not import** from ad-hoc trees in this repo outside `fsaa.*`. Other folders here may hold research, demos, or legacy helpers; **`fsaa verify`** only checks **`src/fsaa`**, **`scripts/`**, and **`tests/`**.

## Non‑negotiables

| Rule | Meaning |
|------|--------|
| **Package surface** | Production logic lives under this repo’s `src/fsaa/`. |
| **No path cheats in package** | No `sys.path` hacks or re-exports that call non-`fsaa` code from `src/fsaa`. |
| **Workspace only via env** | Paths outside the package enter through **`WORKSPACE_ROOT`** and documented `FSAA_*` overrides. |
| **Preserve behavior** | JSONL shapes, guard verdicts, supervisor semantics stay compatible where tested. |
| **Verify gate** | `fsaa verify` green; `scripts/verify_no_external_roots.py` scans `src/fsaa`, `scripts`, `tests` only. |

## Copy-paste prompt block (for agents)

---

**FSAA doctrine — overrides any prior plan:**

- **Goal:** `src/fsaa` is the **canonical Python package**. Workspace trees (e.g. `AIOS_Luna_Aria`, `automation` under `WORKSPACE_ROOT`) are **runtime context**, not import targets from package code.
- **Forbidden in `src/fsaa`:** shims to random repo folders, string path references to `Continue/...` import cheats, legacy `Steel_Brain` imports (use `fsaa.policy.guard` / `fsaa.control_plane.supervisor`).
- **Allowed:** `WORKSPACE_ROOT` and documented `FSAA_*` env vars.
- **Deliverable:** Modules under `fsaa.*`, tests passing, **`fsaa verify`** green.

---

## If the model drifts toward shims

Say explicitly: **“That violates `docs/rebuild_doctrine.md` — port behavior into `fsaa.*`.”**
