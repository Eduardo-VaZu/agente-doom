# Guion de exposicion — Agente Doom: Tecnologias y Algoritmo

Guion para presentar las 11 slides de `docs/slides_tecnologias/`. Cada seccion trae:
**Idea central**, **Que decir** (lo que hablas frente al publico) y **Si preguntan** (respuestas de respaldo).

Duracion sugerida: **10–14 minutos** (aprox. 1 minuto por slide + preguntas).

---

## Slide 1 — Portada · Agente Doom

**Idea central:** presentar el proyecto en una frase.

**Que decir:**
> "Este proyecto es un agente que aprende a jugar Doom por si solo, usando Aprendizaje por Refuerzo profundo. No lo programamos con reglas del tipo 'si ves un enemigo, dispara'; el agente descubre como jugar a base de prueba y error. Las piezas clave son las que ven aqui: el algoritmo RecurrentPPO con una red LSTM, una red convolucional para la vision, y el entorno ViZDoom. Voy a explicar cada tecnologia, para que sirve y como encaja en el sistema."

**Si preguntan — que es Aprendizaje por Refuerzo:** un agente actua en un entorno, recibe una recompensa segun lo bien que lo hace, y ajusta su conducta para maximizar esa recompensa a lo largo del tiempo.

---

## Slide 2 — Arquitectura del Pipeline

**Idea central:** vista de pajaro; como fluye la informacion de principio a fin.

**Que decir:**
> "Antes de entrar en detalle, esta es la ruta completa. ViZDoom nos entrega la imagen del juego cuadro a cuadro. OpenCV la limpia: la pasa a gris y la achica a 84 por 84 pixeles. Apilamos 4 cuadros seguidos para captar movimiento. Esa imagen entra a la CNN, que la resume en 512 numeros. El LSTM le agrega memoria de lo que paso antes. Con eso, PPO decide la accion —disparar, moverse, girar— y el entorno devuelve una recompensa que corrige el aprendizaje. En una frase: percepcion, memoria, decision y accion, en un ciclo cerrado por la recompensa."

**Si preguntan — por que gris y 84x84:** para reducir la cantidad de datos. El color y la resolucion alta no aportan mucho y hacen el entrenamiento mas lento.

---

## Slide 3 — Entorno y Percepcion: ViZDoom · Gymnasium · OpenCV

**Idea central:** las tres tecnologias que producen y preparan lo que el agente "ve".

**Que decir:**
> "Aca estan las tres piezas de la entrada. **ViZDoom** es el motor: nos deja controlar Doom por codigo y leer la pantalla en cada cuadro; es un mundo rico pero parcialmente observable —el agente solo ve lo que tiene enfrente—. **Gymnasium** es la interfaz estandar de entornos, con sus funciones reset y step; gracias a ella podemos cambiar de algoritmo sin tocar el entorno. Y **OpenCV** hace el preprocesado de imagen: gris, redimension y normalizacion. El resultado es un entrenamiento mas rapido y estable."

**Si preguntan — que es 'parcialmente observable':** el agente no ve el estado completo del juego (mapa entero, enemigos fuera de cuadro). Solo tiene la vista actual. Por eso mas adelante necesitamos memoria.

---

## Slide 4 — Red Convolucional (CNN)

**Idea central:** como se convierte una imagen en informacion util.

**Que decir:**
> "La CNN es la vista del agente. Son tres capas convolucionales, al estilo de los primeros agentes de Atari, que terminan en un vector de 512 numeros. Cada capa detecta patrones cada vez mas abstractos: primero bordes, luego formas, y al final paredes, enemigos o items. Lo importante es que reconoce esos patrones sin importar en que parte de la pantalla aparezcan. Sin esto, los miles de pixeles crudos serian imposibles de aprovechar. Y el apilado de 4 cuadros permite percibir movimiento y direccion, no solo una foto fija."

**Si preguntan — por que 'invariante a la posicion':** una convolucion aplica el mismo filtro por toda la imagen, asi que detecta a un enemigo este a la izquierda o a la derecha.

---

## Slide 5 — Red neuronal completa: de pixeles a decision

**Idea central:** como se conectan CNN, LSTM y las dos "cabezas" de salida.

**Que decir:**
> "Esta slide arma la red completa, de arriba hacia abajo. Entra la observacion, 4 por 84 por 84. La CNN la comprime a 512 features. En el modo multimodal, ademas, un pequeno MLP procesa features de audio o de notificaciones y se concatena. Todo eso entra al **LSTM**, que mantiene un estado oculto a lo largo del episodio: eso es la memoria. Y al final hay dos salidas: la cabeza **Actor**, que da la probabilidad de cada accion, y la cabeza **Critico**, que estima que tan bueno es el estado. En el codigo esto es la politica CnnLstmPolicy, o MultiInputLstmPolicy cuando hay audio o notificaciones."

**Si preguntan — para que dos cabezas:** es la arquitectura Actor-Critic. El actor decide; el critico juzga esa decision para guiar el aprendizaje. Lo vemos en la siguiente slide.

---

## Slide 6 — Algoritmo Nucleo: RecurrentPPO + LSTM

**Idea central:** el corazon del proyecto; por que esta combinacion y no otra.

**Que decir:**
> "Este es el algoritmo que estamos implementando. Tiene tres ideas. **PPO** mejora la politica de forma controlada, con un mecanismo de clipping que evita cambios bruscos; por eso es estable y es un estandar en la industria. **LSTM** aporta la memoria: como Doom es parcialmente observable, un solo cuadro no dice de donde vengo ni si hay un enemigo detras. Y **RecurrentPPO**, de la libreria sb3-contrib, une las dos cosas: entrena en secuencias temporales usando BPTT, retropropagacion a traves del tiempo. La ventaja practica es que el agente aprende que vale la pena recordar y cuando actuar. Abajo esta la idea Actor-Critic: el actor elige, el critico evalua, y GAE calcula cuanto mejor fue cada accion frente a lo esperado."

**Si preguntan — que es clipping:** PPO limita cuanto puede cambiar la politica en cada actualizacion, para que un mal lote de datos no destruya lo aprendido.

**Si preguntan — que es POMDP:** proceso de decision parcialmente observable. El agente no ve el estado completo, solo una parte.

---

## Slide 7 — Ciclo de entrenamiento (on-policy)

**Idea central:** paso a paso, como aprende el agente en cada vuelta.

**Que decir:**
> "Aca esta el ciclo de aprendizaje, en cinco pasos. **Uno, rollout:** el agente juega 2048 pasos y guarda todo —observacion, accion, recompensa y estado oculto—. **Dos, secuencias y BPTT:** cortamos ese rollout por episodios y, como los episodios tienen largos distintos, usamos padding y una mascara para que el gradiente recorra el tiempo correctamente. **Tres, ventaja con GAE:** estimamos cuanto mejor fue cada accion, con gamma 0.99 y lambda 0.95. **Cuatro, perdida PPO:** combina el actor con clipping, el critico, y un bonus de entropia para explorar; se hacen 4 pasadas sobre lotes de 128. **Cinco, update:** ajustamos los pesos y volvemos a empezar. Es on-policy: el agente aprende solo de sus propias jugadas mas recientes."

**Si preguntan — que es padding y mascara:** como los episodios no duran lo mismo, rellenamos las secuencias cortas con ceros (padding) y marcamos con una mascara cuales pasos son reales, para que el relleno no afecte el aprendizaje.

**Si preguntan — on-policy vs off-policy:** on-policy solo usa datos de la politica actual; por eso hay que recolectar rollouts nuevos en cada vuelta.

---

## Slide 8 — Hiperparametros del algoritmo

**Idea central:** los valores concretos que gobiernan el entrenamiento (datos reales del proyecto).

**Que decir:**
> "Estos son los valores reales con los que entrenamos, sacados de los archivos de configuracion. No hace falta memorizarlos, pero vale ver que cada uno controla algo concreto. El learning rate es el tamano del paso de ajuste. n_steps, 2048, define cuanto juega antes de aprender y tambien el horizonte del BPTT. gamma, 0.99, dice cuanto pesa el futuro. gae_lambda equilibra sesgo y varianza en la estimacion. ent_coef controla cuanto explora. Y frame_stack, 4, son los cuadros que apilamos para ver movimiento. La idea es que todo el comportamiento del agente sale de ajustar estas perillas."

**Si preguntan — por que 1e-4:** es un valor conservador y estable para tareas de vision con PPO; pasos mas grandes tienden a desestabilizar el entrenamiento.

---

## Slide 9 — Acciones y Recompensa

**Idea central:** que puede hacer el agente y como sabe si lo hace bien.

**Que decir:**
> "Dos cosas definen el comportamiento. Primero, el **espacio de acciones**: en vez de dejar todos los botones sueltos, usamos combos curados —atacar, avanzar, girar, usar— y descartamos combinaciones inutiles u opuestas, como izquierda y derecha a la vez. Un espacio de acciones mas chico se aprende mas rapido. Segundo, el **reward shaping**: usamos las recompensas nativas de Doom —matar, recoger items, secretos, sobrevivir, morir— con una escala y un recorte. Eso define que significa jugar bien. Y agregamos un **bonus de exploracion** que premia visitar zonas nuevas del mapa, para que el agente no se quede quieto ni gire en circulos."

**Si preguntan — que es reward shaping:** disenar la senal de recompensa para guiar al agente hacia el comportamiento que queremos, sin decirle exactamente que hacer.

---

## Slide 10 — Infraestructura y Herramientas

**Idea central:** el andamiaje que hace el proyecto reproducible y operable.

**Que decir:**
> "Alrededor del algoritmo hay herramientas de soporte. **Stable-Baselines3** y sb3-contrib nos dan la implementacion probada de PPO y RecurrentPPO, asi no reinventamos el algoritmo. **PyTorch** es el motor de calculo y gradientes, con GPU. **TensorBoard** registra las metricas para ver si el agente aprende o se estanca. Y para persistencia usamos **PostgreSQL en Neon** para la metadata de las corridas y **AWS S3** para los checkpoints y artefactos; eso nos permite reproducir experimentos y pasar el trabajo entre varias computadoras."

**Si preguntan — por que base de datos y nube:** para no perder resultados, poder comparar corridas y continuar el entrenamiento desde otra maquina sin rehacer nada.

---

## Slide 11 — Cierre · Que aporta cada pieza

**Idea central:** recapitulacion en una tabla; que se lleva el publico.

**Que decir:**
> "Para cerrar, un resumen de quien hace que. ViZDoom es el mundo. OpenCV reduce la imagen. La CNN es la vision. El LSTM es la memoria que resuelve la observacion parcial. RecurrentPPO es el algoritmo que aprende una politica estable. El reward shaping define el objetivo. Y Neon con S3 dan la persistencia. La idea que quiero que se lleven es simple: el agente combina **percepcion, memoria y decision**, y todo eso se entrena por prueba y error. Gracias, quedo para preguntas."

**Si preguntan — que sigue / limitaciones:** los escenarios de habilidad aislada funcionan; el salto a un nivel completo real es el desafio abierto, porque requiere exploracion de largo alcance y una senal de recompensa mas densa.

---

## Consejos de exposicion

- **No leas los hiperparametros uno por uno.** En la slide 8 resume la idea ("son las perillas del entrenamiento") y menciona 2 o 3.
- **Slides 6 y 7 son el corazon.** Dedica mas tiempo ahi; el resto es contexto.
- **Analogia util para el LSTM:** "es la memoria de corto plazo del agente; sin ella, cada instante empieza de cero".
- **Analogia util para Actor-Critic:** "el actor es el jugador, el critico es el entrenador que le dice que tan buena fue la jugada".
- Si el publico es tecnico, profundiza en BPTT/padding (slide 7). Si es general, quedate en la intuicion.
