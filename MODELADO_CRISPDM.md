# Modelado

## 1. Seleccion De La Tecnica De Modelado

En esta etapa se selecciono el uso de **aprendizaje por refuerzo**, debido a que el agente aprende mediante la interaccion directa con el entorno y no a partir de datos previamente etiquetados. El objetivo del modelo es que el agente observe el escenario de ViZDoom, seleccione una accion, reciba una recompensa y mejore progresivamente su comportamiento.

Para este proyecto se utilizo el algoritmo **Recurrent PPO** (`Recurrent Proximal Policy Optimization`), implementado mediante `Stable-Baselines3` y `sb3-contrib`. Esta tecnica fue seleccionada porque permite trabajar con entornos secuenciales, donde las decisiones actuales pueden depender de observaciones anteriores.

Ademas, se utilizo **Gymnasium** como interfaz para estructurar el entorno de aprendizaje por refuerzo. Esto permitio representar ViZDoom bajo un formato estandar de entorno, con metodos como `reset`, `step`, `observation_space` y `action_space`.

**Herramientas y dependencias usadas:**

- `vizdoom`: permite ejecutar los escenarios de Doom donde el agente aprende.
- `gymnasium`: estandariza el entorno de aprendizaje por refuerzo.
- `stable-baselines3`: proporciona algoritmos base de aprendizaje por refuerzo.
- `sb3-contrib`: permite usar `RecurrentPPO`, version recurrente de PPO.
- `torch`: backend de redes neuronales usado por el modelo.

## 2. Supuestos Del Modelado

El modelo considera como entrada las imagenes generadas por el entorno de ViZDoom. Estas observaciones son transformadas a escala de grises, redimensionadas a **84x84 pixeles** y apiladas en grupos de **4 frames**, permitiendo que el agente identifique movimiento y cambios recientes en la escena.

Tambien se considera que las acciones del agente pueden representarse como combinaciones discretas de botones. Para evitar acciones contradictorias, el proyecto utiliza presets de acciones segun el escenario.

El uso de Gymnasium permite definir formalmente que observa el agente y que acciones puede ejecutar. En este caso, el espacio de observaciones se representa como una matriz de pixeles procesada, mientras que el espacio de acciones se define como un conjunto discreto de combinaciones validas de botones.

**Herramientas y dependencias usadas:**

- `opencv-python`: procesa los frames del juego, convierte imagenes y redimensiona observaciones.
- `numpy`: representa observaciones, acciones y arreglos numericos usados por el entorno.
- `gymnasium`: define `observation_space` y `action_space`.
- `vizdoom`: entrega los frames, botones disponibles y estado del juego.

## 3. Diseno De Prueba

La evaluacion del modelo se realiza mediante episodios de prueba dentro del entorno. Para medir el desempeno del agente se utilizan metricas como la recompensa media por episodio, la longitud media del episodio y la desviacion estandar de la recompensa.

Ademas, durante el entrenamiento se guardan checkpoints periodicos, permitiendo conservar el mejor modelo obtenido y comparar su rendimiento con otros entrenamientos.

Para el seguimiento del entrenamiento se utiliza **TensorBoard**, herramienta que permite visualizar metricas generadas durante el aprendizaje del agente. Aunque los graficos pueden agregarse posteriormente, TensorBoard permite analizar curvas de recompensa, duracion de episodios, perdidas del modelo y otros indicadores relevantes.

**Herramientas y dependencias usadas:**

- `tensorboard`: visualiza metricas del entrenamiento mediante graficos.
- `stable-baselines3`: permite evaluar politicas y registrar metricas.
- `sb3-contrib`: evalua el modelo recurrente entrenado con `RecurrentPPO`.
- `json` del proyecto: almacena reportes de evaluacion, configuracion y resultados.

## 4. Construccion Del Modelo

El modelo fue construido utilizando una politica **CnnLstmPolicy**. La red convolucional permite extraer caracteristicas visuales desde los frames del juego, mientras que la capa LSTM conserva informacion temporal para mejorar la toma de decisiones.

El entorno de ViZDoom fue adaptado mediante Gymnasium para que el agente pueda interactuar con el de forma estandar. En cada paso del entorno, el agente recibe una observacion, ejecuta una accion, obtiene una recompensa y determina si el episodio termino.

El entrenamiento sigue un ciclo de interaccion: el agente observa el entorno, selecciona una accion, recibe una recompensa y actualiza su politica mediante Recurrent PPO. En algunos escenarios se aplica `reward shaping` para ajustar las recompensas y facilitar el aprendizaje.

Los principales hiperparametros usados fueron: `learning_rate = 0.0001`, `gamma = 0.99`, `gae_lambda = 0.95`, `batch_size = 64`, `n_epochs = 10` y `ent_coef = 0.01`.

**Herramientas y dependencias usadas:**

- `torch`: construye y entrena las redes neuronales CNN y LSTM.
- `sb3-contrib`: implementa `RecurrentPPO`.
- `stable-baselines3`: aporta utilidades de entrenamiento, entornos vectorizados, monitoreo y guardado.
- `gymnasium`: conecta el ciclo `observacion -> accion -> recompensa -> nuevo estado`.
- `opencv-python`: prepara las imagenes antes de entregarlas al modelo.
- `numpy`: codifica acciones y observaciones numericas.

## 5. Escenarios De Entrenamiento

El proyecto contempla los siguientes escenarios:

1. `basic`: escenario base para validar el funcionamiento del pipeline.
2. `defend_the_center`: escenario enfocado en punteria y giros rapidos.
3. `deadly_corridor`: escenario mas complejo, con navegacion, combate y recompensas esparsas.
4. `health_gathering`: escenario de supervivencia, donde el agente debe mantenerse con vida.

Cada escenario cuenta con una configuracion especifica de acciones, recompensas y pasos de entrenamiento. Gymnasium permite manejar estos escenarios bajo una misma estructura de interaccion, facilitando el entrenamiento y la evaluacion del agente.

**Herramientas y dependencias usadas:**

- `vizdoom`: carga archivos `.cfg` y `.wad` de cada escenario.
- `gymnasium`: mantiene la misma interfaz para todos los escenarios.
- `toml` de configuracion del proyecto: define perfiles, escenarios, recompensas, checkpoints y parametros.
- `moviepy`: permite generar o manejar videos de episodios registrados.

## 6. Evaluacion Tecnica Del Modelo

La evaluacion tecnica permite determinar si el agente logro aprender un comportamiento adecuado dentro del entorno. Para ello se analizan metricas como la recompensa media, la duracion promedio de los episodios y la estabilidad del desempeno.

En los resultados actuales, el escenario `basic` obtuvo una recompensa media aproximada de **91.2** en 5 episodios de evaluacion. En el escenario `defend_the_center`, el mejor checkpoint obtuvo una recompensa media aproximada de **3.4**.

Estas estadisticas se complementan con los registros de TensorBoard, los cuales permiten observar la evolucion del entrenamiento a lo largo de los timesteps. De esta manera, no solo se evalua el resultado final, sino tambien el proceso de aprendizaje del agente.

**Herramientas y dependencias usadas:**

- `stable-baselines3`: calcula metricas de evaluacion y permite ejecutar episodios de prueba.
- `tensorboard`: muestra graficas del comportamiento del entrenamiento.
- `numpy`: calcula promedios, desviaciones y longitudes de episodios.
- `artifacts/reports`: almacena resultados finales en archivos JSON.
- `artifacts/videos`: guarda evidencia visual del comportamiento del agente.

## 7. Seleccion Del Mejor Modelo

El mejor modelo se selecciona a partir del checkpoint con mayor desempeno en la evaluacion. Estos checkpoints se almacenan en `artifacts/checkpoints/`, junto con metadata del entrenamiento, configuracion utilizada, escenario, semilla, timesteps y metricas obtenidas.

TensorBoard tambien sirve como apoyo para esta seleccion, ya que permite revisar si el rendimiento del modelo mejora, se estanca o presenta inestabilidad durante el entrenamiento. Posteriormente, esta seccion puede complementarse con graficos de recompensa, perdidas y duracion de episodios.

**Herramientas y dependencias usadas:**

- `stable-baselines3`: guarda y carga checkpoints del modelo.
- `sb3-contrib`: guarda y carga modelos `RecurrentPPO`.
- `tensorboard`: apoya la revision visual de la evolucion del entrenamiento.
- `json` del proyecto: registra metadata del checkpoint, metricas y configuracion usada.
- `artifacts/checkpoints`: almacena el ultimo modelo y el mejor modelo encontrado.

## 8. Resumen De Herramientas Y Dependencias

| Herramienta o dependencia | Uso en la fase de modelado |
| --- | --- |
| `vizdoom` | Ejecutar escenarios de Doom y entregar observaciones/recompensas. |
| `gymnasium` | Estandarizar el entorno con `reset`, `step`, `observation_space` y `action_space`. |
| `stable-baselines3` | Entrenamiento, evaluacion, monitoreo, entornos vectorizados y checkpoints. |
| `sb3-contrib` | Uso de `RecurrentPPO` para aprendizaje por refuerzo con memoria temporal. |
| `torch` | Construccion y entrenamiento de redes neuronales CNN y LSTM. |
| `opencv-python` | Preprocesamiento de imagenes del juego. |
| `numpy` | Manejo de arreglos numericos, acciones, observaciones y metricas. |
| `tensorboard` | Visualizacion de metricas y graficos del entrenamiento. |
| `moviepy` | Registro o procesamiento de videos de episodios. |
| `mypy` | Revision estatica de tipos del codigo. |
| `ruff` | Revision de estilo y calidad del codigo. |
| `pre-commit` | Automatizacion de revisiones antes de confirmar cambios. |

