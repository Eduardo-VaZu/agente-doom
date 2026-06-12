# AGENTS.md — Agente Doom

## Platform & Setup

- **Windows x64, Python 3.12**. Use `py` launcher.
- Venv lives at `.venv`. Install: `py -m venv .venv && .\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- All commands use `.\.venv\Scripts\python.exe` prefix (or `.\.venv\Scripts\<tool>.exe` for tensorboard).

## Commands

```powershell
# Make shortcuts
make help
make check
make train SCENARIO=basic
make list-scenarios

# Lint -> Typecheck -> Test (CI order)
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Unified CLI (preferred for all operations)
.\.venv\Scripts\python.exe src\cli.py <command>

# Legacy entrypoints (backward compat only, delegate to doom_agent.cli)
.\.venv\Scripts\python.exe src\train.py
.\.venv\Scripts\python.exe src\evaluate.py

# TensorBoard
.\.venv\Scripts\tensorboard.exe --logdir artifacts\tensorboard

# Pre-commit install
.\.venv\Scripts\python.exe -m pre_commit install
```

## CLI Subcommands

| Command | Purpose |
|---|---|
| `train` | Train normal flow by scenario. Recommended: `train --scenario <scenario>` |
| `evaluate` | Evaluate a checkpoint (`--select best\|last`) |
| `sweep` | Advanced sequential hyperparameter sweep (`--learning-rates`, `--n-steps-values`, `--batch-sizes`, `--seeds`) |
| `list-scenarios` | Show available scenarios for normal flow |
| `list-profiles` | Backward-compatible alias of `list-scenarios` |
| `list-checkpoints` | List known checkpoints |
| `list-runs` | List training run reports |
| `inspect-checkpoint` | Show checkpoint metadata JSON |

## Architecture

- **Package**: `src/doom_agent/` — subpackages: `cli`, `config`, `envs`, `models`, `services`, `shared`, `utils`
- **Legacy wrappers**: `src/train.py`, `src/evaluate.py`, `src/config.py`, `src/environment.py`, `src/model.py` — thin shims for backward compat
- **Profiles & scenarios**: `configs/training_profiles.toml` — editable TOML catalog, no code changes needed
- **Scenarios**: `data/scenarios/*.cfg` + `*.wad` (basic, deadly_corridor, defend_the_center, health_gathering)
- **Artifacts** (gitignored): `artifacts/checkpoints/`, `artifacts/checkpoints/auto/`, `artifacts/reports/`, `artifacts/tensorboard/`, `artifacts/videos/`

## Key Behaviors

- **Auto-resume**: Training resumes from last compatible checkpoint by default. Use `--from-scratch` to force fresh training.
- **Public training flow**: normal training uses implicit `default` profile plus explicit `--scenario`.
- **RecurrentPPO trains in `n_steps` blocks**: effective timesteps may exceed requested. Both values are printed.
- **Checkpoint naming**: includes `__<scenario>` suffix when `--scenario` differs from profile default to avoid collisions.
- **Curriculum profiles**: stages train sequentially; each stage resumes from the `best_model` of the previous stage.
- **`--from-scratch` + explicit `--resume` are mutually exclusive** — the CLI rejects this combination.
- **Action space**: uses curated button combinations (discrete), not raw multidiscrete. Presets avoid opposing buttons (e.g., left+right).

## Tooling Config

- **mypy**: strict mode on `src`, `tests`, and legacy wrappers. Config in `pyproject.toml`. Ignores missing imports for `cv2`, `vizdoom`, `sb3_contrib`, `stable_baselines3`.
- **ruff**: rules `E, F, I, B, UP`; ignores `E501` (line length handled by formatter) and `UP040` (TypeAlias). Line length 100.
- **pre-commit**: runs `ruff check --fix`, `ruff format`, `mypy` (all pass_filenames=false).
- **CI** (`.github/workflows/ci.yml`): 3 parallel Windows jobs — lint (ruff), typing (mypy), tests (unittest).

## Testing

- Uses `unittest` (not pytest). Tests insert `src` into `sys.path` manually.
- Test files create temp dirs under `artifacts/test-temp/` and clean up in `finally` blocks.
- Environment tests actually instantiate ViZDoom — may be slow or require ViZDoom native libs.

## Training Flow (training_profiles.toml)

| Flow/Profile | Purpose | Timesteps | Notes |
|---|---|---|---|
| `default` | Public normal training | Scenario-specific | render+video on, use with `--scenario` |
