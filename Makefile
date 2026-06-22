SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

PYTHON := .\.venv\Scripts\python.exe
TENSORBOARD := .\.venv\Scripts\tensorboard.exe
CLI := src\cli.py

SCENARIO ?= basic
TIMESTEPS ?=
N_STEPS ?=
NUM_ENVS ?=
SEED ?=
RESUME ?= auto
CHECKPOINT ?=
SELECT ?= best
STEPS ?=
EPISODES ?=
LIMIT ?= 20
EVAL_FREQ ?=
EVAL_EPISODES ?= 5
FROM_SCRATCH ?= 0
ALLOW_SCENARIO_RESUME ?= 0
NO_SAVE_BEST ?= 0
RUN_ID ?=
JSON ?= 0
NO_RENDER ?= 0
ONLY ?= both
PROMOTE_EPISODES ?= 50

TRAIN_FLAGS = --scenario $(SCENARIO) $(if $(TIMESTEPS),--timesteps $(TIMESTEPS),) $(if $(N_STEPS),--n-steps $(N_STEPS),) $(if $(NUM_ENVS),--num-envs $(NUM_ENVS),) $(if $(SEED),--seed $(SEED),) $(if $(RESUME),--resume $(RESUME),) $(if $(EVAL_FREQ),--eval-freq $(EVAL_FREQ),) $(if $(EVAL_EPISODES),--eval-episodes $(EVAL_EPISODES),) $(if $(filter 1 true yes,$(FROM_SCRATCH)),--from-scratch,) $(if $(filter 1 true yes,$(ALLOW_SCENARIO_RESUME)),--allow-scenario-resume,) $(if $(filter 1 true yes,$(NO_SAVE_BEST)),--no-save-best,)
EVALUATE_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select $(SELECT) $(if $(STEPS),--steps $(STEPS),) $(if $(EPISODES),--episodes $(EPISODES),) $(if $(filter 1 true yes,$(NO_RENDER)),--no-render,) $(if $(filter 1 true yes,$(JSON)),--json,)
INSPECT_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select $(SELECT)
PROMOTE_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select $(SELECT) --episodes $(PROMOTE_EPISODES)
HYDRATE_FLAGS = --config default $(if $(SCENARIO),--scenario $(SCENARIO),) --only $(ONLY)
INSPECT_RUN_FLAGS = --run-id "$(RUN_ID)" $(if $(filter 1 true yes,$(JSON)),--json,)
CANCEL_EXIT_CODES = @(130, 3221225786, -1073741510)

.PHONY: help venv install setup bootstrap lint typecheck test check precommit \
	list-checkpoints list-runs inspect evaluate evaluate-last play train train-from-scratch \
	train-latest tensorboard sync-artifacts sync-local-only \
	sync-failed sync-dry-run inspect-run promote hydrate

help:
	@echo "Preparacion:"
	@echo "  make venv                		# crea .venv"
	@echo "  make install             		# instala dependencias"
	@echo "  make setup               		# venv + install"
	@echo "  make bootstrap           		# setup + check"
	@echo "  make check               		# ruff + mypy + unittest"
	@echo ""
	@echo "Entrenamiento:"
	@echo "  make train               		# entrena con resume=auto"
	@echo "  make train-from-scratch  		# entrena desde cero"
	@echo "  make train-latest        		# fuerza resume latest"
	@echo "  make tensorboard         		# abre TensorBoard"
	@echo ""
	@echo "Evaluacion:"
	@echo "  make evaluate            		# evalua select=best"
	@echo "  make evaluate-last       		# evalua select=last"
	@echo "  make play                		# alias de evaluate"
	@echo "  make inspect             		# inspecciona metadata del checkpoint"
	@echo "  make inspect-run         		# resumen consolidado por RUN_ID"
	@echo "  make promote             		# reevaluar y promover checkpoint"
	@echo ""
	@echo "Storage y handoff:"
	@echo "  make sync-artifacts      		# sync de una corrida por RUN_ID"
	@echo "  make sync-local-only     		# sync batch de local_only"
	@echo "  make sync-failed         		# reintenta failed"
	@echo "  make sync-dry-run        		# preview sin subir"
	@echo "  make hydrate             		# restaura alias/soporte desde S3"
	@echo ""
	@echo "Inventario:"
	@echo "  make list-checkpoints    		# lista checkpoints"
	@echo "  make list-runs           		# lista corridas"
	@echo ""
	@echo "Recetas comunes:"
	@echo "  make train-from-scratch SEED=42 TIMESTEPS=1500000"
	@echo "  make evaluate CHECKPOINT=artifacts\\checkpoints\\doom_foundation_agent_best.zip EPISODES=50 NO_RENDER=1 JSON=1"
	@echo "  make promote CHECKPOINT=artifacts\\checkpoints\\auto\\doom_foundation_agent_1250000_steps.zip PROMOTE_EPISODES=50"
	@echo "  make inspect-run RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ JSON=1"
	@echo "  make hydrate ONLY=promoted"
	@echo ""
	@echo "Variables utiles:"
	@echo "  SCENARIO=basic"
	@echo "  TIMESTEPS=1500000"
	@echo "  N_STEPS=2048"
	@echo "  NUM_ENVS=1"
	@echo "  SEED=42"
	@echo "  STEPS=2000"
	@echo "  EPISODES=50"
	@echo "  CHECKPOINT=artifacts\\checkpoints\\doom_foundation_agent_best.zip"
	@echo "  RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ"
	@echo "  SELECT=best|last|exact"
	@echo "  NO_RENDER=1"
	@echo "  JSON=1"
	@echo "  ONLY=active|promoted|both"

venv:
	@py -3.13 -m venv .venv

install:
	@& "$(PYTHON)" -m pip install --upgrade pip
	@& "$(PYTHON)" -m pip install -r requirements.txt

setup: venv install

bootstrap: setup check

lint:
	@& "$(PYTHON)" -m ruff check .

typecheck:
	@& "$(PYTHON)" -m mypy

test:
	@& "$(PYTHON)" -m unittest discover -s tests -v

check: lint typecheck test

precommit:
	@& "$(PYTHON)" -m pre_commit install

tensorboard:
	@& "$(TENSORBOARD)" --logdir artifacts\runs; if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "TensorBoard detenido por usuario."; exit 0 } else { exit $$LASTEXITCODE }

sync-artifacts:
	@if (-not "$(RUN_ID)") { throw "Debes pasar RUN_ID=<run_id>." }
	@& "$(PYTHON)" "$(CLI)" sync-artifacts --run-id "$(RUN_ID)"

sync-local-only:
	@& "$(PYTHON)" "$(CLI)" sync-artifacts --all-local-only --limit $(LIMIT)

sync-failed:
	@& "$(PYTHON)" "$(CLI)" sync-artifacts --all-failed --limit $(LIMIT)

sync-dry-run:
	@if (-not "$(RUN_ID)") { throw "Debes pasar RUN_ID=<run_id>." }
	@& "$(PYTHON)" "$(CLI)" sync-artifacts --run-id "$(RUN_ID)" --dry-run

list-checkpoints:
	@& "$(PYTHON)" "$(CLI)" list-checkpoints --limit $(LIMIT)

list-runs:
	@& "$(PYTHON)" "$(CLI)" list-runs --limit $(LIMIT)

inspect:
	@& "$(PYTHON)" "$(CLI)" inspect-checkpoint $(INSPECT_FLAGS)

inspect-run:
	@if (-not "$(RUN_ID)") { throw "Debes pasar RUN_ID=<run_id>." }
	@& "$(PYTHON)" "$(CLI)" inspect-run $(INSPECT_RUN_FLAGS)

train:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS); if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "Entrenamiento cancelado por usuario."; exit 0 } else { exit $$LASTEXITCODE }

train-from-scratch:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS) --from-scratch; if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "Entrenamiento cancelado por usuario."; exit 0 } else { exit $$LASTEXITCODE }

train-latest:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS) --resume latest; if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "Entrenamiento cancelado por usuario."; exit 0 } else { exit $$LASTEXITCODE }

evaluate:
	@& "$(PYTHON)" "$(CLI)" evaluate $(EVALUATE_FLAGS); if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "Evaluacion cancelada por usuario."; exit 0 } else { exit $$LASTEXITCODE }

evaluate-last:
	@& "$(PYTHON)" "$(CLI)" evaluate $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select last $(if $(STEPS),--steps $(STEPS),) $(if $(EPISODES),--episodes $(EPISODES),) $(if $(filter 1 true yes,$(NO_RENDER)),--no-render,) $(if $(filter 1 true yes,$(JSON)),--json,); if ($$LASTEXITCODE -eq 0) { exit 0 } elseif ($(CANCEL_EXIT_CODES) -contains $$LASTEXITCODE) { Write-Host "Evaluacion cancelada por usuario."; exit 0 } else { exit $$LASTEXITCODE }

promote:
	@& "$(PYTHON)" "$(CLI)" promote-checkpoint $(PROMOTE_FLAGS)

hydrate:
	@& "$(PYTHON)" "$(CLI)" hydrate-workspace $(HYDRATE_FLAGS)

play: evaluate
