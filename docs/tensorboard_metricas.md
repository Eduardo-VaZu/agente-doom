# TensorBoard y metricas

Esta guia sirve como leyenda practica para leer TensorBoard sin adivinar que significa cada grafico.

No cambia el modelo ni obliga a reentrenar. Solo documenta como interpretar las metricas que ya produce el proyecto.

## Idea general

En este repo, TensorBoard mezcla cuatro grupos de señales:

- `rollout/`: que pasa mientras el agente entrena
- `eval/`: que pasa cuando se pausa a evaluar el checkpoint actual
- `train/`: que pasa dentro de la optimizacion de PPO
- `time/`: velocidad y progreso de la corrida

## Como abrir TensorBoard

```powershell
make tensorboard
```

TensorBoard lee desde:

```text
artifacts/runs/<run_id>/tensorboard/
```

## Leyenda rapida por grupo

## `rollout/`

Estas metricas describen el comportamiento observado durante el entrenamiento normal, no en evaluacion offline.

- `rollout/ep_len_mean`
  Longitud media de los episodios recientes durante entrenamiento.

- `rollout/ep_rew_mean`
  Recompensa media reciente durante entrenamiento.

Como leerlas:
- si `ep_len_mean` baja en `basic`, normalmente el agente resuelve el episodio mas rapido
- si `ep_rew_mean` mejora y se estabiliza, el entrenamiento suele ir por buen camino

## `eval/`

Estas metricas vienen de las evaluaciones periodicas del callback. Son mas utiles para comparar checkpoints que `rollout/`.

- `eval/mean_reward`
  Recompensa media del checkpoint actual durante la evaluacion.

- `eval/std_reward`
  Variabilidad de la recompensa entre episodios de evaluacion.

- `eval/mean_episode_length`
  Longitud media de episodio durante evaluacion.

- `eval/episodes`
  Cantidad de episodios usados en esa evaluacion.

- `eval/best_mean_reward_so_far`
  Mejor reward medio visto hasta ese punto dentro de la corrida.

- `eval/reward_gap_vs_best`
  Diferencia entre la evaluacion actual y el mejor punto visto antes.

- `eval/evaluation_index`
  Numero secuencial de evaluacion dentro de la corrida.

- `eval/is_new_best`
  Vale `1` si esa evaluacion produjo nuevo mejor checkpoint, `0` si no.

Como leerlas:
- `mean_reward` menos negativo suele ser mejor en `basic`
- `std_reward` mas bajo suele significar comportamiento mas estable
- `mean_episode_length` mas bajo suele significar que el agente resuelve antes
- si `reward_gap_vs_best` cae mucho, el agente tuvo retroceso respecto a su mejor punto

## `eval/actions/`

Estas metricas explican como se reparte la politica entre acciones top del escenario.

- `eval/actions/attack_count`
- `eval/actions/move_left_attack_count`
- `eval/actions/move_right_attack_count`
  Conteos brutos de uso por accion durante evaluacion.

- `eval/actions/attack_percentage`
- `eval/actions/move_left_attack_percentage`
- `eval/actions/move_right_attack_percentage`
  Porcentaje de uso por accion durante evaluacion.

- `eval/actions/dominant_action_percentage`
  Porcentaje de la accion dominante en esa evaluacion.

- `eval/actions/unique_top_actions`
  Cuantas acciones distintas aparecen con uso relevante.

Como leerlas:
- si una sola accion domina demasiado tiempo, puede haber sesgo
- en `basic`, una mezcla razonable entre `MOVE_LEFT+ATTACK` y `MOVE_RIGHT+ATTACK` suele verse mas sana que una politica monotona
- mucho `ATTACK` quieto puede indicar desperdicio de accion

## `train/`

Estas metricas describen la optimizacion interna de PPO. Sirven para diagnostico, no para elegir checkpoint final por si solas.

- `train/loss`
  Perdida total reportada por PPO.

- `train/value_loss`
  Error de la red de valor.

- `train/policy_gradient_loss`
  Magnitud del ajuste de la politica.

- `train/entropy_loss`
  Medida ligada a exploracion. En PPO suele verse negativa por implementacion.

- `train/approx_kl`
  Cuanto se movio la politica respecto a la anterior.

- `train/clip_fraction`
  Cuanto de la actualizacion quedo afectado por clipping.

- `train/clip_range`
  Rango de clipping configurado.

- `train/explained_variance`
  Que tan bien la red de valor explica el retorno observado.

- `train/learning_rate`
  Learning rate activo de la corrida.

- `train/n_updates`
  Numero acumulado de updates del optimizador.

Como leerlas:
- `explained_variance` mas alto suele ser buena señal para la red de valor
- `approx_kl` y `clip_fraction` demasiado altos pueden sugerir updates agresivos
- estas metricas ayudan a diagnosticar, pero no reemplazan `eval/mean_reward`

## `time/`

Estas metricas ayudan a ver progreso y costo operativo.

- `time/fps`
  Velocidad de entrenamiento en frames por segundo.

- `time/iterations`
  Iteraciones acumuladas de entrenamiento.

- `time/time_elapsed`
  Tiempo transcurrido de corrida.

- `time/total_timesteps`
  Pasos acumulados ejecutados.

Como leerlas:
- `fps` sirve para comparar throughput entre corridas o configuraciones
- `total_timesteps` es la referencia mas clara para ubicar donde paso algo

## Que metricas usar como verdad principal

Para decisiones de promotion o comparacion entre checkpoints:

1. `eval/mean_reward`
2. `eval/std_reward`
3. `eval/mean_episode_length`
4. evaluacion offline aparte con `50` episodios

No usar como verdad principal:

- inspeccion visual aislada
- un pico puntual de `rollout/ep_rew_mean`
- una sola grafica interna de `train/`

## Leyenda corta para presentacion

Si quieres una explicacion breve al exponer, usa esta version:

- `eval/mean_reward`: rendimiento medio del agente al evaluarlo
- `eval/std_reward`: que tan estable es ese rendimiento
- `eval/mean_episode_length`: cuanto tarda en resolver el episodio
- `rollout/ep_rew_mean`: como va aprendiendo mientras entrena
- `time/fps`: velocidad de entrenamiento
- `eval/actions/*`: que acciones esta prefiriendo la politica

## Regla practica del proyecto

Si agregamos nueva documentacion o mejores nombres de metricas:

- no cambia el modelo ya entrenado
- no afecta checkpoints existentes
- no obliga a reentrenar desde cero

Solo habria que reentrenar si quieres que futuras corridas registren tags nuevos dentro de TensorBoard.
