# FSAA (Alpha)

**Repository:** [github.com/Nemeca99/FSAA](https://github.com/Nemeca99/FSAA)

FSAA is a **control plane / supervisor** for **AIOS** workloads: policy-guarded IPC, brainstem supervision, and observability. The installable package lives under **`src/fsaa/`**. This repo may also contain other workspace-adjacent trees; CI and `fsaa verify` only gate **`src/fsaa`**, **`scripts/`**, and **`tests/`**.

## Quickstart

**Bash / zsh**

```bash
export WORKSPACE_ROOT=/path/to/workspace   # parent of automation/, chat.py, AIOS_Luna_Aria/
cd /path/to/this/repo
pip install -e ".[dev]"
fsaa validate-policy
fsaa verify
```

**Windows PowerShell** (example workspace on `L:`)

```powershell
$env:WORKSPACE_ROOT = "L:\Continue"
Set-Location L:\Continue\FSAA
pip install -e ".[dev]"
fsaa validate-policy
fsaa verify
```

## Installed commands

| Command | Purpose |
| --- | --- |
| `fsaa` | `fsaa verify`, `fsaa validate-policy` |
| `fsaa-brainstem` | Bounded supervisor (same defaults as `main_fsaa.py`) |
| `fsaa-luna` / `fsaa-aria` | Start workspace Luna/Aria mains (`WORKSPACE_ROOT`) |
| `fsaa-real-poc` | Real PoC runner |
| `fsaa-ab-turn-token` | Turn-token A/B harness |
| `fsaa-turn-token` | CPU/GPU turn-token pilot |
| `fsaa-supervisor` | Full supervisor CLI |
| `fsaa-policy-guard` | Policy guard smoke test |

**Rebuild rule (contributors):** Package code is a **standalone** `fsaa` tree; integration with Luna/automation is via **`WORKSPACE_ROOT`** only. See **[docs/rebuild_doctrine.md](docs/rebuild_doctrine.md)**.

## Architecture

- [docs/adr/ADR-0001-dual-lexicon.md](docs/adr/ADR-0001-dual-lexicon.md)
- [docs/telemetry_schema.md](docs/telemetry_schema.md)
- Supervisor: `python -m fsaa.control_plane.supervisor` or `fsaa-supervisor`

## License

Apache-2.0 — see [LICENSE](LICENSE).
