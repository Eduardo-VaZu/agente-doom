# Como agregar un escenario

Esta arquitectura agrega escenarios por capas, sin tocar el core.

## Pasos

1. Agrega assets a `data/scenarios/`
   - `<escenario>.cfg`
   - `<escenario>.wad` si aplica

2. Crea config en `configs/scenarios/<escenario>.toml`

Ejemplo:

```toml
[scenario]
scenario_name = "<escenario>.cfg"
description = "Describe objetivo del escenario."
learning_rate = 0.0001
n_steps = 2048
batch_size = 64
n_epochs = 10
gamma = 0.99
gae_lambda = 0.95
ent_coef = 0.01
requested_timesteps = 250000
checkpoint_frequency = 25000
video_record_frequency = 25000
video_length = 2000
action_combo_preset = "basic_combat"

[scenario.reward_shaping]
scale = 1.0
offset = 0.0
clip_min = -1.0
clip_max = 1.0
```

3. Agrega tests minimos
   - config
   - action preset
   - carga del entorno

4. Documenta prioridad y rol del escenario
   - actualiza `Docs/vizdoom_escenarios_oficiales.md`
   - si entra a curriculum, documenta orden en `Docs/roadmap_curriculum.md`
   - actualiza estado en `Docs/scenario_registry.md`
   - registra trabajo relevante en `Docs/experiment_log.md`

## Regla

Logica especifica del escenario vive en config. Core de entrenamiento no debe cambiar para agregar un escenario normal.
