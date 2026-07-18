# Demo — Escenarios cerrados (guía rápida)

Orden recomendado: arrancar con `deadly_corridor` o `health_gathering_supreme` (más vistosos), dejar `basic` para el final o como referencia rápida.

**Importante:** usar `STEPS`, no `EPISODES`. `EPISODES` corre por un camino de evaluación offline sin el delay de cámara lenta (`sleep`); `STEPS` sí lo respeta y abre la ventana en vivo a velocidad reducida.

## Comandos

```
make play SCENARIO=deadly_corridor STEPS=300
make play SCENARIO=health_gathering_supreme STEPS=300
make play SCENARIO=defend_the_line STEPS=300
make play SCENARIO=health_gathering STEPS=300
make play SCENARIO=take_cover STEPS=300
make play SCENARIO=defend_the_center STEPS=300
make play SCENARIO=basic STEPS=300
```

`STEPS=300` ≈ 2.5 min por escenario (delay actual `0.5s`/paso en `src/doom_agent/services/evaluator.py`, constante `DEMO_STEP_DELAY_SECONDS`). Ajustar el número según tiempo disponible. `Ctrl+C` corta antes de terminar los steps si hace falta pasar al siguiente.

Cada comando carga el checkpoint **promovido** (mejor) de ese escenario automáticamente (`--select best`), no reentrena nada — cero riesgo de romper algo.

## Métricas de referencia (para comentar mientras corre)

| Escenario | mean_reward | Nota |
|---|---|---|
| `deadly_corridor` | 43.62 ± 16.62 | Dificultad máxima (skill 5), combate avanzando bajo fuego |
| `health_gathering_supreme` | 416.02 ± 85.45 | Transfer learning desde `health_gathering` |
| `defend_the_line` | 27.06 ± 7.43 | Defensa de posición, bajo ruido |
| `health_gathering` | 1580.28 ± 736.36 | Supervivencia, resultado muy fuerte |
| `take_cover` | 331.90 ± 178.23 | Evasión de proyectiles |
| `defend_the_center` | 9.90 ± 1.38 | Combate estático, bajo ruido |
| `basic` | −11.84 ± 11.26 | Baseline del proyecto |

## Backup — video pregrabado (si falla algo en vivo)

```
deadly_corridor:
  artifacts\runs\doom_foundation_agent__deadly_corridor__20260714T175934084462Z\videos\

health_gathering_supreme:
  artifacts\runs\doom_foundation_agent__health_gathering_supreme__20260714T071306043795Z\videos\

defend_the_line:
  artifacts\runs\doom_foundation_agent__defend_the_line__20260703T231100240178Z\videos\

health_gathering:
  artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\videos\

take_cover:
  artifacts\runs\doom_foundation_agent__take_cover__20260703T140745071243Z\videos\

defend_the_center:
  artifacts\runs\doom_foundation_agent__defend_the_center__20260625T085706691704Z\videos\

basic:
  artifacts\runs\doom_foundation_agent__20260622T024012285164Z\videos\
```

Cada carpeta tiene varios `.mp4` (progreso por step de entrenamiento) — usar el de mayor número de step, es el más entrenado.

## Informe completo

Métricas, metodología y el piloto de nivel real documentado: https://claude.ai/code/artifact/be9295f8-11e2-4ab7-be89-a8e550a2755b
