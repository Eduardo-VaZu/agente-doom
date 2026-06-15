SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

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
EVAL_FREQ ?=
EVAL_EPISODES ?= 5
FROM_SCRATCH ?= 0
ALLOW_SCENARIO_RESUME ?= 0
NO_SAVE_BEST ?= 0

TRAIN_FLAGS = --scenario $(SCENARIO) $(if $(TIMESTEPS),--timesteps $(TIMESTEPS),) $(if $(SEED),--seed $(SEED),) $(if $(RESUME),--resume $(RESUME),) $(if $(EVAL_FREQ),--eval-freq $(EVAL_FREQ),) $(if $(EVAL_EPISODES),--eval-episodes $(EVAL_EPISODES),) $(if $(filter 1 true yes,$(FROM_SCRATCH)),--from-scratch,) $(if $(filter 1 true yes,$(ALLOW_SCENARIO_RESUME)),--allow-scenario-resume,) $(if $(filter 1 true yes,$(NO_SAVE_BEST)),--no-save-best,)
EVALUATE_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select $(SELECT) $(if $(STEPS),--steps $(STEPS),)
INSPECT_FLAGS = $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select $(SELECT)

.PHONY: help venv install setup bootstrap lint typecheck test check precommit \
	list-checkpoints list-runs inspect evaluate evaluate-last play train train-from-scratch \
	train-latest tensorboard

help:
	@echo "Targets principales:"
	@echo "  make venv               		# crea un entorno virtual en .venv"
	@echo "  make install            		# instala dependencias en .venv"
	@echo "  make setup              		# venv + install"
	@echo "  make bootstrap          		# setup + check"
	@echo "  make check              		# ruff + mypy + unittest"
	@echo "  make train              		# entrena en SCENARIO=basic"
	@echo "  make train-from-scratch 		# entrena desde cero"
	@echo "  make train-latest       		# fuerza resume latest"
	@echo "  make evaluate           		# evalua mejor checkpoint visualmente"
	@echo "  make evaluate-last      		# evalua ultimo checkpoint visualmente"
	@echo "  make play               		# alias de evaluate"
	@echo "  make inspect            		# SCENARIO=basic"
	@echo "  make list-checkpoints   		# LIMIT=20"
	@echo "  make list-runs         		# LIMIT=20"
	@echo "  make tensorboard        		# abre TensorBoard en artifacts\\runs"
	@echo ""
	@echo "Variables utiles:"
	@echo "  SCENARIO=basic"
	@echo "  TIMESTEPS=750000"
	@echo "  SEED=42"
	@echo "  STEPS=2000"
	@echo "  CHECKPOINT=artifacts\\checkpoints\\doom_foundation_agent.zip"

venv:
	@py -m venv .venv

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
	@& "$(TENSORBOARD)" --logdir artifacts\runs

list-checkpoints:
	@& "$(PYTHON)" "$(CLI)" list-checkpoints --limit $(LIMIT)

list-runs:
	@& "$(PYTHON)" "$(CLI)" list-runs --limit $(LIMIT)

inspect:
	@& "$(PYTHON)" "$(CLI)" inspect-checkpoint $(INSPECT_FLAGS)

train:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS)

train-from-scratch:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS) --from-scratch

train-latest:
	@& "$(PYTHON)" "$(CLI)" train $(TRAIN_FLAGS) --resume latest

evaluate:
	@& "$(PYTHON)" "$(CLI)" evaluate $(EVALUATE_FLAGS)

evaluate-last:
	@& "$(PYTHON)" "$(CLI)" evaluate $(if $(CHECKPOINT),--checkpoint $(CHECKPOINT),--scenario $(SCENARIO)) --select last $(if $(STEPS),--steps $(STEPS),)

play: evaluate
