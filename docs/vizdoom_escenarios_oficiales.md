# Escenarios oficiales de ViZDoom para entrenamiento

Fecha de consulta: 2026-06-14

## Alcance

Este documento resume los escenarios oficiales por defecto documentados por ViZDoom en la
documentacion oficial de Farama Foundation.

Incluye:

- nombres oficiales de escenarios
- nombre de archivo `.cfg`
- objetivo principal
- acciones disponibles
- `doom_skill` oficial cuando aparece en documentacion
- dificultad relativa estimada para priorizar entrenamiento

No incluye:

- configuraciones auxiliares fuera del set oficial por defecto
- niveles originales de Doom
- escenarios de terceros o personalizados

## Lista oficial de escenarios por defecto

1. `basic`
2. `basic_audio`
3. `basic_notifications`
4. `deadly_corridor`
5. `deathmatch`
6. `defend_the_center`
7. `defend_the_line`
8. `health_gathering`
9. `health_gathering_supreme`
10. `my_way_home`
11. `predict_position`
12. `take_cover`

Total: 12 escenarios oficiales por defecto.

## Cobertura actual en este proyecto

Segun el catalogo actual:

- [configs/base.toml](/E:/agente-doom/configs/base.toml)
- [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml)

Escenarios ya integrados en el catalogo local:

- `basic`
- `basic_audio`
- `basic_notifications`
- `deadly_corridor`
- `defend_the_center`
- `defend_the_line`
- `health_gathering`
- `health_gathering_supreme`
- `my_way_home`
- `predict_position`
- `take_cover`

Escenarios oficiales todavia no integrados en el catalogo local:

- `deathmatch`

## Tabla de escenarios

Notas:

- `doom_skill oficial` solo aparece cuando la documentacion lo especifica explicitamente.
- `dificultad relativa` es estimada segun navegacion, observacion parcial, precision temporal,
  supervivencia y tamano del espacio de acciones.

| Escenario | Archivo cfg oficial | Objetivo principal | Acciones disponibles | `doom_skill` oficial | Dificultad relativa |
|---|---|---|---|---|---|
| `basic` | `basic.cfg` | Matar al monstruo en un mapa simple para validar aprendizaje 3D basico. | Mover izquierda, mover derecha, disparar. | No especificado | Baja |
| `basic_audio` | `basic_audio.cfg` | Encontrar y matar monstruo invisible usando audio. | Mover izquierda, mover derecha, disparar. | No especificado | Media |
| `basic_notifications` | `basic_notifications.cfg` | Matar monstruo correcto entre tres usando notificacion interna. | Mover izquierda, mover derecha, disparar. | No especificado | Media-alta |
| `deadly_corridor` | `deadly_corridor.cfg` | Avanzar por corredor hostil hasta chaleco verde sobreviviendo a enemigos laterales. | Mover adelante/atras/izquierda/derecha, girar izquierda/derecha, disparar. | 5 | Muy alta |
| `deathmatch` | `deathmatch.cfg` | Matar maxima cantidad posible antes de morir o agotar tiempo. | 16 botones binarios y 3 botones delta. | 3 | Muy alta |
| `defend_the_center` | `defend_the_center.cfg` | Permanecer al centro y matar monstruos que reaparecen. | Girar izquierda, girar derecha, disparar. | 3 | Media |
| `defend_the_line` | `defend_the_line.cfg` | Defender una linea frontal contra monstruos. | Girar izquierda, girar derecha, disparar. | 3 | Media-alta |
| `health_gathering` | `health_gathering.cfg` | Sobrevivir recogiendo botiquines en piso acido. | Girar izquierda, girar derecha, avanzar. | No especificado | Media |
| `health_gathering_supreme` | `health_gathering_supreme.cfg` | Igual que `health_gathering`, con layout mas complejo. | Girar izquierda, girar derecha, avanzar. | No especificado | Alta |
| `my_way_home` | `my_way_home.cfg` | Navegar laberinto y encontrar chaleco verde objetivo. | Girar izquierda, girar derecha, avanzar, moverse a izquierda y derecha. | 5 | Alta |
| `predict_position` | `predict_position.cfg` | Sincronizar disparo de cohete para interceptar objetivo movil. | Girar izquierda, girar derecha, disparar. | No especificado | Alta |
| `take_cover` | `take_cover.cfg` | Esquivar proyectiles y sobrevivir el mayor tiempo posible. | Mover izquierda, mover derecha. | 4 | Media |

## Prioridad sugerida para entrenamiento

Si quieres cubrir el set oficial con progresion razonable:

1. `basic`
2. `defend_the_center`
3. `health_gathering`
4. `take_cover`
5. `defend_the_line`
6. `basic_audio`
7. `basic_notifications`
8. `my_way_home`
9. `predict_position`
10. `health_gathering_supreme`
11. `deadly_corridor`
12. `deathmatch`

Esta prioridad es estimada, no oficial.

Roadmap practico de trabajo por fases:

- [plan_escenarios.md](/E:/agente-doom/docs/plan_escenarios.md:1)

## Fuentes oficiales

Fuente principal:

- Documentacion oficial Farama: [Default scenarios/environments](https://vizdoom.farama.org/environments/default/)

Fuentes de respaldo:

- Repositorio oficial de escenarios: [ViZDoom `scenarios/`](https://github.com/Farama-Foundation/ViZDoom/tree/main/scenarios)

Archivos `.cfg` oficiales:

- [`basic.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/basic.cfg)
- [`basic_audio.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/basic_audio.cfg)
- [`basic_notifications.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/basic_notifications.cfg)
- [`deadly_corridor.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/deadly_corridor.cfg)
- [`deathmatch.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/deathmatch.cfg)
- [`defend_the_center.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/defend_the_center.cfg)
- [`defend_the_line.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/defend_the_line.cfg)
- [`health_gathering.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/health_gathering.cfg)
- [`health_gathering_supreme.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/health_gathering_supreme.cfg)
- [`my_way_home.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/my_way_home.cfg)
- [`predict_position.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/predict_position.cfg)
- [`take_cover.cfg`](https://github.com/Farama-Foundation/ViZDoom/blob/main/scenarios/take_cover.cfg)
