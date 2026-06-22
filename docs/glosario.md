# Glosario corto

Este glosario fija como hablamos del proyecto en espanol sin pelearse con el codigo.

## Terminos principales

- `run`: corrida
- `run_id`: identificador unico de corrida
- `checkpoint`: checkpoint
- `best checkpoint`: mejor checkpoint de la corrida
- `promoted checkpoint`: checkpoint promovido oficial
- `active checkpoint`: checkpoint activo para continuidad operativa
- `from scratch`: desde cero
- `resume`: reanudar
- `latest`: ultimo checkpoint disponible
- `auto`: reanudacion automatica si existe un checkpoint compatible
- `sync`: sincronizar artefactos locales a `S3`
- `handoff`: transferencia operativa entre PCs
- `hydrate`: restaurar workspace desde artefactos remotos
- `report`: reporte final de corrida
- `manifest`: inventario de artefactos de una corrida
- `artifact`: artefacto
- `evaluation`: evaluacion
- `offline evaluation`: evaluacion determinista sin entrenar
- `seed`: seed
- `timesteps`: pasos solicitados o ejecutados
- `reward shaping`: ajuste de recompensa
- `action space`: espacio de acciones

## Regla practica

En documentacion y conversacion del equipo:

- se puede decir `corrida`
- se puede mantener `checkpoint`
- se puede mantener `seed`
- se puede mantener `best`

No hace falta traducir a la fuerza todo termino tecnico si en RL ya es estandar en ingles.

## Frases recomendadas

- "corrida oficial"
- "checkpoint promovido"
- "evaluacion offline de 50 episodios"
- "sync a S3"
- "hidratar la otra PC"
- "reanudar desde latest"
