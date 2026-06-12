SHELL := cmd.exe
.SHELLFLAGS := /d /c

PYTHON := .\.venv\Scripts\python.exe
TENSORBOARD := .\.venv\Scripts\tensorboard.exe
CLI := src\cli.py

SCENARIO ?= basic
TIMESTEPS ?=
SEED ?=
RESUME ?= auto
CHECKPOINT ?=
SELECT ?= best
STEPS ?=
LIMIT ?= 20
LEARNING_RATES ?=
N_STEPS_VALUES ?=
BATCH_SIZES ?=
SEEDS ?=
EVAL_FREQ ?=
EVAL_EPISODES ?= 5
FROM_SCRATCH ?= 0
ALLOW_SCENARIO_RESUME ?= 0
NO_SAVE_BEST ?= 0

TRAIN_FLAGS = --scenario $(SCENARIO) \
	$(if $(TIMESTEPS),--timesteps $(TIMESTEPS),) \
	$(if $(SEED),--seed $(SEED),) \
	$(if $(RESUME),--resume $(RESUME),) \
	$(if $(EVAL_FREQ),--eval-freq $(EVAL_FREQ),) \
	$(if $(EVAL_EPISODES),--eval-episodes $(EVAL_EPISODES),) \
	$(if $(filter 1 true yes,$(FROM_SCRATCH)),--from-scratch,) \
	$(if $(filter 1 true yes,$(ALLOW_SCENARIO_RESUME)),--allow-scenario-resume,) \
	$(if $(filter 1 true yes,$(NO_SAVE_BEST)),--no-save-best,)

EVALUATE_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) \
	--select $(SELECT) \
	$(if $(STEPS),--steps $(STEPS),)

INSPECT_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) \
	--select $(SELECT)

SWEEP_FLAGS = --scenario $(SCENARIO) \
	$(if $(TIMESTEPS),--timesteps $(TIMESTEPS),) \
	$(if $(LEARNING_RATES),--learning-rates $(LEARNING_RATES),) \
	$(if $(N_STEPS_VALUES),--n-steps-values $(N_STEPS_VALUES),) \
	$(if $(BATCH_SIZES),--batch-sizes $(BATCH_SIZES),) \
	$(if $(SEEDS),--seeds $(SEEDS),) \
	$(if $(EVAL_FREQ),--eval-freq $(EVAL_FREQ),) \
	$(if $(EVAL_EPISODES),--eval-episodes $(EVAL_EPISODES),) \
	$(if $(filter 1 true yes,$(NO_SAVE_BEST)),--no-save-best,)

.PHONY: help venv install lint typecheck test check precommit tensorboard \
	list-scenarios list-profiles list-checkpoints list-runs inspect evaluate \
	train train-basic train-defend train-deadly train-health sweep

help:
	@echo Targets principales:
	@echo   make install            # instala dependencias en .venv
	@echo   make check              # ruff + mypy + unittest
	@echo   make list-scenarios     # lista escenarios del flujo normal
	@echo   make train SCENARIO=basic
	@echo   make train-basic ^| train-defend ^| train-deadly ^| train-health
	@echo   make evaluate SCENARIO=deadly_corridor
	@echo   make inspect SCENARIO=health_gathering
	@echo   make sweep SCENARIO=basic LEARNING_RATES=0.0001,0.0002 N_STEPS_VALUES=1024,2048

venv:
	@py -m venv .venv

install:
	@"$(PYTHON)" -m pip install --upgrade pip
	@"$(PYTHON)" -m pip install -r requirements.txt

lint:
	@"$(PYTHON)" -m ruff check .

typecheck:
	@"$(PYTHON)" -m mypy

test:
	@"$(PYTHON)" -m unittest discover -s tests -v

check: lint typecheck test

precommit:
	@"$(PYTHON)" -m pre_commit install

tensorboard:
	@"$(TENSORBOARD)" --logdir artifacts\tensorboard

list-scenarios:
	@"$(PYTHON)" "$(CLI)" list-scenarios

list-profiles:
	@"$(PYTHON)" "$(CLI)" list-profiles

list-checkpoints:
	@"$(PYTHON)" "$(CLI)" list-checkpoints --limit $(LIMIT)

list-runs:
	@"$(PYTHON)" "$(CLI)" list-runs --limit $(LIMIT)

inspect:
	@"$(PYTHON)" "$(CLI)" inspect-checkpoint $(INSPECT_FLAGS)

evaluate:
	@"$(PYTHON)" "$(CLI)" evaluate $(EVALUATE_FLAGS)

train:
	@"$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS)

train-basic:
	@"$(PYTHON)" "$(CLI)" train --scenario basic

train-defend:
	@"$(PYTHON)" "$(CLI)" train --scenario defend_the_center

train-deadly:
	@"$(PYTHON)" "$(CLI)" train --scenario deadly_corridor

train-health:
	@"$(PYTHON)" "$(CLI)" train --scenario health_gathering

sweep:
	@"$(PYTHON)" "$(CLI)" sweep $(SWEEP_FLAGS)
