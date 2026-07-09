# Tabla de metricas por escenario

Fuente: evaluaciones offline de checkpoints promovidos y corridas validadas del repositorio.

> Nota: `mean_reward` no debe compararse de forma directa entre escenarios con mecanicas distintas.

| Escenario | Estado | Calidad | Episodios | Mean reward | Std reward | Mean episode length | Fuente | Nota |
|---|---|---|---:|---:|---:|---:|---|---|
| `basic` | Oficial | Bueno | 50 | -11.84 | 11.26 | 13.84 | offline_cli | Baseline oficial cerrada. |
| `defend_the_center` | Oficial | Bueno | 50 | 9.90 | 1.37 | 634.12 | offline_cli | Referencia fuerte de Fase 2. |
| `health_gathering` | Oficial | Bueno | 50 | 1580.28 | 736.36 | 1581.04 | offline_cli | Muy buen resultado para supervivencia. |
| `take_cover` | Oficial | Bueno | 50 | 331.90 | 178.23 | 331.90 | offline_cli | Referencia fuerte de evasion. |
| `defend_the_line` | Oficial | Bueno | 50 | 27.06 | 7.43 | 1026.78 | offline_cli | Mejor cierre estable de Fase 3. |
| `basic_audio` | Provisional | Regular | 50 | -64.84 | 111.19 | 66.48 | offline_cli | Mejorado tras segundo tramo; sigue inestable. |
| `basic_notifications` | Provisional | Regular | 50 | -73.60 | 120.65 | 75.16 | offline_cli | Aprendio algo, pero conserva sesgo y varianza alta. |

## Lectura rapida

- oficiales fuertes: `basic`, `defend_the_center`, `health_gathering`, `take_cover`, `defend_the_line`
- provisionales: `basic_audio`, `basic_notifications`
- mejor resultado absoluto no comparable entre escenarios: `health_gathering`
- mejor cierre estable de Fase 3: `defend_the_line`
- escenarios sensoriales ya no son prioridad inmediata
