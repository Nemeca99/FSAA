# FSAA_v2 (Alpha)

**Repository:** [github.com/Nemeca99/FSAA](https://github.com/Nemeca99/FSAA)

FSAA is a **control plane / supervisor** for **AIOS runtime** workloads: policy-guarded IPC, brainstem supervision, and observability—without mutating model weights. This repository is a **standalone** Python package; it does not import legacy trees elsewhere on disk except via **`WORKSPACE_ROOT`**.

## Quickstart

**Bash / zsh**

```bash
export WORKSPACE_ROOT=/path/to/workspace   # parent of automation/, chat.py, AIOS_Luna_Aria/
cd FSAA_v2
uv pip install -e ".[dev]"                 # or: pip install -e ".[dev]"
fsaa validate-policy
fsaa verify
```

**Windows PowerShell** (example workspace on drive `L:`)

```powershell
$env:WORKSPACE_ROOT = "L:\workspace"
Set-Location L:\path\to\FSAA_v2
# Use the same Python where you installed FSAA (venv recommended):
& "$env:WORKSPACE_ROOT\.venv\Scripts\pip.exe" install -e ".[dev]"
& "$env:WORKSPACE_ROOT\.venv\Scripts\fsaa.exe" validate-policy
& "$env:WORKSPACE_ROOT\.venv\Scripts\fsaa.exe" verify
```

PowerShell does not support `export` (use `$env:NAME = "value"`) or bash-style `\` line continuation; put long commands on one line or use the backtick `` ` `` at the end of a line for continuation.

## Installation

Prerequisite: **`WORKSPACE_ROOT`** must point at the workspace directory (contains `automation/`, `chat.py`, `AIOS_Luna_Aria/`, etc.).

```bash
uv pip install -e ".[dev]"
```

After `pip install -e .`, run **`fsaa`** or **`python -m fsaa.cli.main`** with **that same interpreter** — a bare `python` on `PATH` without the package will raise `ModuleNotFoundError: No module named 'fsaa'`.

Default supervisor launcher (historical `main_fsaa` defaults): **`python -m fsaa.cli.entrypoint`**.

**Rebuild rule (AI / contributors):** FSAA_v2 is a **from-scratch** package; legacy repos are **reference only**, not dependencies. See **[docs/rebuild_doctrine.md](docs/rebuild_doctrine.md)** for the non‑negotiables and a copy‑paste prompt block.

## Architecture

- [docs/adr/ADR-0001-dual-lexicon.md](docs/adr/ADR-0001-dual-lexicon.md) — control plane vs runtime adapter
- [docs/telemetry_schema.md](docs/telemetry_schema.md) — telemetry field names
- Supervisor (`python -m fsaa.control_plane.supervisor`): default `--mode sidecar` (Luna/Aria runtimes under `WORKSPACE_ROOT`); `--mode turn_token` runs `fsaa.runtime.turn_token` with `--max-seconds` / `--cpu-turn-beats` / `--gpu-turn-beats` (see `--turn-token-*` flags). Use `FSAA_RUNTIME_ADAPTER=turn_token` for socket-based readiness.

  **PowerShell example (one line):**

  ```powershell
  $env:WORKSPACE_ROOT = "L:\workspace"; $env:FSAA_RUNTIME_ADAPTER = "turn_token"
  & "$env:WORKSPACE_ROOT\.venv\Scripts\python.exe" -m fsaa.control_plane.supervisor --mode turn_token --no-auto --loop 1 --turn-token-max-seconds 45 --turn-token-cpu-beats 4 --turn-token-gpu-beats 2
  ```

## Alpha vs Beta

**Alpha** locks naming, contracts, and verification scripts. **Beta** may add optional backends (OTel Collector export, OPA, HTTP health).

## License

Apache-2.0 — see [LICENSE](LICENSE).
