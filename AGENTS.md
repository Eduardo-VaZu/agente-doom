# AGENTS.md — Agente Doom

## Platform & Setup

- **Windows x64, Python 3.12**. Use `py` launcher.
- Venv lives at `.venv`.
- Main command prefix: `.\.venv\Scripts\python.exe`

## Commands

```powershell
# Make shortcuts
make help
make check
make train
make train-from-scratch
make evaluate SCENARIO=basic
make inspect SCENARIO=basic
make list-checkpoints LIMIT=10

# Lint -> Typecheck -> Test
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Unified CLI
.\.venv\Scripts\python.exe src\cli.py <command>

# Legacy wrappers
.\.venv\Scripts\python.exe src\train.py
.\.venv\Scripts\python.exe src\evaluate.py
```

## CLI Subcommands

| Command | Purpose |
|---|---|
| `train` | Train current `foundation` model on active scenario |
| `evaluate` | Evaluate a checkpoint (`--select best\|last`) |
| `inspect-checkpoint` | Show checkpoint metadata JSON |
| `list-checkpoints` | List known checkpoints |
| `list-runs` | List historical training run reports |

## Removed Commands

- `sweep`
- `list-scenarios`
- `list-profiles`

`src/train.py` stays as compatibility wrapper for current training flow.

## Architecture

- **Package**: `src/doom_agent/` — subpackages: `cli`, `config`, `envs`, `models`, `services`, `shared`, `utils`
- **Legacy wrappers**: `src/train.py`, `src/evaluate.py`, `src/config.py`, `src/environment.py`, `src/model.py`
- **Profiles & scenarios**: `configs/base.toml` + `configs/scenarios/*.toml`
- **Scenarios**: `data/scenarios/*.cfg` + `*.wad`
- **Artifacts**: `artifacts/checkpoints/`, `artifacts/checkpoints/auto/`, `artifacts/reports/`, `artifacts/tensorboard/`, `artifacts/videos/`

## Key Behaviors

- **Foundation model**: training flow builds single model identity named `foundation`.
- **Single active scenario**: current catalog keeps only `basic` active while architecture is stabilized.
- **Checkpoint naming**: non-`basic` scenarios use suffix `__<scenario>`.
- **Evaluation fallback**: `evaluate` and `inspect-checkpoint` can resolve checkpoints from `default + scenario`.
- **Action space**: curated discrete button combinations; presets avoid opposing buttons.

## Tooling Config

- **mypy**: strict mode on `src`, `tests`, and legacy wrappers.
- **ruff**: rules `E, F, I, B, UP`.
- **pre-commit**: runs `ruff check --fix`, `ruff format`, `mypy`.
- **CI**: Windows jobs for lint, typing, tests.

## Testing

- Uses `unittest`.
- Test files insert `src` into `sys.path`.
- Environment tests instantiate ViZDoom and may be slow.

## Scenario Catalog

`configs/base.toml` plus `configs/scenarios/*.toml` remain source of truth for scenario presets and checkpoint naming used by training, evaluation, and inspection flows.
Current active scenario: `basic`.
Future rollout order should follow [Docs/vizdoom_escenarios_oficiales.md](/E:/agente-doom/Docs/vizdoom_escenarios_oficiales.md:89).
