# Modelo Conceptual — Motor de Investigación de UBIGUIA

Versión: 1.0
Naturaleza: modelo de dominio. No es una especificación técnica.

Este documento no describe cómo se construye el Motor de Investigación. Describe qué existe en su dominio: qué conceptos son reales dentro de él, qué significan, cómo se relacionan y qué reglas gobiernan su existencia — independientemente de cualquier tecnología, formato de archivo o estructura de datos futura.

Toda decisión que dependiera de la implementación se marca explícitamente como:

> Decisión de implementación. Se resolverá en la SPEC técnica.

---

## 1. ¿Qué es una investigación?

Una investigación es el acto de producir conocimiento candidato sobre una entidad, con el propósito de que ese conocimiento eventualmente pueda convertirse en lo que UBIGUIA considera cierto y vigente sobre ella.

**Qué representa.** Representa un intento acotado en el tiempo de responder a la pregunta "¿qué sabemos, o qué deberíamos saber, sobre esta entidad?". No representa el conocimiento en sí — representa el *proceso* de buscarlo y producirlo.

**Cuándo nace.** Nace en el momento en que alguien decide, para una entidad concreta, que hace falta producir (o volver a producir) conocimiento sobre ella. Puede nacer porque la entidad nunca fue investigada, porque su conocimiento vigente quedó desactualizado, o porque un intento anterior no llegó a buen término.

**Cuándo termina.** Termina cuando alcanza una resolución: el conocimiento candidato que produjo fue juzgado y ese juicio tuvo un desenlace — se aceptó (y en algún momento pasó a formar parte del conocimiento vigente de la entidad), se rechazó, o el intento mismo no llegó a producir nada válido. Una investigación no queda "terminada a medias": mientras no tenga una resolución, sigue conceptualmente abierta.

**Qué produce.** Produce, como máximo, un resultado: una pieza de conocimiento candidato, todavía no confiable por sí sola, a la espera de juicio humano.

Una investigación **no es** el conocimiento. Es el proceso que lo intenta producir. Esta distinción es la base de todo el resto del modelo.

---

## 2. Entidades del dominio

El enunciado propone como punto de partida: *Investigación, Entidad Investigable, Resultado, Fuente, Observación, Revisión, Aprobación, Publicación, Historial.* Antes de aceptar esa lista, corresponde revisarla críticamente.

**Se mantienen tal cual:** Entidad Investigable, Investigación, Resultado, Fuente, Observación, Revisión, Historial.

**Se generaliza:** "Aprobación" aparece sola en la lista original, pero una revisión humana no siempre termina en aprobación — también puede terminar en rechazo, y ambos desenlaces son igual de necesarios en el dominio (un rechazo sin representación propia dejaría sin lugar conceptual a las observaciones que lo motivan). Se reemplaza por un concepto más amplio: **Decisión Editorial**, que puede resolverse como aprobación o como rechazo.

**Falta en la lista original:** no hay ningún concepto que represente *lo que la entidad efectivamente sabe hoy*, en contraposición a lo que un resultado candidato propone. Sin este concepto no es posible explicar qué significa "promover" ni distinguir investigación de conocimiento aceptado. Se agrega: **Conocimiento Vigente**.

**Falta, de forma más leve:** no hay ningún concepto para "quién o qué llevó a cabo la investigación". No es indispensable detallarlo en profundidad todavía, pero omitirlo por completo deja huérfano un dato relevante del dominio (una investigación no ocurre sola). Se agrega, de forma deliberadamente abstracta: **Investigador** (rol).

**Sobra, en el sentido de que no pertenece a este dominio:** "Publicación". Ver justificación en la entidad correspondiente más abajo — se conserva como concepto, pero se ubica explícitamente fuera del límite del Motor de Investigación.

Lista final de entidades del dominio: **Entidad Investigable, Investigación, Investigador (rol), Resultado, Fuente, Observación, Revisión, Decisión Editorial, Conocimiento Vigente, Historial.**

---

## 3. Cada entidad: propósito, responsabilidad, contenido y relaciones

### Entidad Investigable

- **Propósito.** Es el sujeto sobre el cual el dominio entero existe: aquello de lo cual UBIGUIA quiere tener conocimiento organizado. Hoy, en la práctica, es un punto de interés turístico — pero el concepto no depende de eso.
- **Responsabilidad.** Ser el ancla que da identidad y continuidad a través de múltiples investigaciones a lo largo del tiempo.
- **Información que contiene (conceptualmente).** Aquello que la identifica como *esa* entidad y no otra — no su conocimiento turístico, sino su identidad.
- **Relaciones.** Tiene, a lo largo de su vida, muchas investigaciones (una activa a la vez como máximo — ver sección 9). Tiene, en cada momento, a lo sumo un conocimiento vigente.

### Investigación

- **Propósito.** Ver sección 1.
- **Responsabilidad.** Delimitar un intento concreto de producir conocimiento, con un principio y una resolución.
- **Información que contiene.** El hecho de que ocurrió, para qué entidad, y su desenlace. No contiene el conocimiento en sí — eso pertenece al Resultado.
- **Relaciones.** Pertenece a una Entidad Investigable. Es llevada a cabo por un Investigador. Produce, como máximo, un Resultado. Queda registrada en el Historial.

### Investigador (rol)

- **Propósito.** Representar a quien o a lo que realiza el acto de investigar, sin prejuzgar su naturaleza.
- **Responsabilidad.** Ninguna sobre el juicio de calidad del resultado — solo sobre producirlo. Investigar no es aprobar.
- **Información que contiene.** Que hubo un ejecutor de la investigación. Nada más pertenece al dominio conceptual en este nivel.
- **Relaciones.** Realiza una Investigación.

> Decisión de implementación. Qué formas concretas puede tomar un Investigador (persona, método automatizado, u otra) se resolverá en la SPEC técnica.

### Resultado

- **Propósito.** Ser la pieza concreta de conocimiento candidato que una investigación produjo.
- **Responsabilidad.** Contener el conocimiento propuesto sobre la entidad, sin ninguna pretensión de ser ya confiable.
- **Información que contiene.** El conocimiento propuesto sobre la entidad (su descripción, su historia, lo que la caracteriza), y las fuentes en las que ese conocimiento dice apoyarse.
- **Relaciones.** Es producido por una Investigación. Puede citar una o varias Fuentes. Es objeto de una o varias Revisiones. Si es aceptado, se convierte en la base del nuevo Conocimiento Vigente.

Un Resultado nunca es, por sí mismo, Conocimiento Vigente. Es candidato hasta que una Decisión Editorial y un acto de promoción digan lo contrario.

### Fuente

- **Propósito.** Representar el origen o respaldo de una afirmación de conocimiento.
- **Responsabilidad.** Sostener la credibilidad de una parte del contenido de un Resultado.
- **Información que contiene.** Una referencia a de dónde proviene una afirmación — no el juicio sobre si esa referencia es buena o mala; eso es tarea de la Revisión.
- **Relaciones.** Respalda contenido dentro de uno o varios Resultados.

### Observación

- **Propósito.** Capturar el juicio editorial humano sobre un Resultado, en particular cuando ese juicio no es favorable.
- **Responsabilidad.** Explicar por qué un Resultado no fue suficiente, para que una investigación futura pueda corregir el rumbo.
- **Información que contiene.** Comentario editorial en lenguaje humano — no es conocimiento sobre la entidad, es conocimiento sobre la calidad del intento.
- **Relaciones.** Surge de una Decisión Editorial (obligatoriamente cuando es un rechazo; puede existir también acompañando una aprobación, como comentario adicional).

### Revisión

- **Propósito.** Ser el acto mediante el cual un humano examina un Resultado antes de que pueda tener cualquier efecto sobre el conocimiento vigente.
- **Responsabilidad.** Ejercer criterio editorial. Ningún Resultado avanza sin pasar por este acto.
- **Información que contiene.** El hecho de que un Resultado fue examinado, y por quién.
- **Relaciones.** Examina un Resultado. Concluye en una Decisión Editorial.

### Decisión Editorial

- **Propósito.** Registrar el desenlace del juicio humano sobre un Resultado: aprobación o rechazo.
- **Responsabilidad.** Ser el único punto del dominio donde se decide si un Resultado merece convertirse en Conocimiento Vigente.
- **Información que contiene.** El sentido de la decisión (favorable o desfavorable) y, si es desfavorable, la Observación que la justifica.
- **Relaciones.** Concluye una Revisión. Si es favorable, habilita (pero no ejecuta por sí sola — ver sección 8) la promoción del Resultado a Conocimiento Vigente. Si es desfavorable, se asocia a una Observación y dejará abierta la posibilidad de una nueva Investigación.

### Conocimiento Vigente

- **Propósito.** Representar lo que UBIGUIA considera, en un momento dado, cierto y aceptado sobre una Entidad Investigable.
- **Responsabilidad.** Ser la única fuente confiable de conocimiento sobre la entidad para cualquier proceso posterior (editorial o de publicación) que necesite partir de una base de verdad.
- **Información que contiene.** El conocimiento aceptado en sí — el contenido de un Resultado que fue aprobado y promovido.
- **Relaciones.** Pertenece a una Entidad Investigable. Se origina en un Resultado que atravesó una Decisión Editorial favorable. Cada actualización queda registrada en el Historial.

Este es el concepto que faltaba en la enumeración original y que resuelve buena parte de las preguntas siguientes: sin él, "investigación" y "verdad aceptada" quedan indistinguibles.

### Historial

- **Propósito.** Preservar, sin excepción, todo lo que ocurrió: cada investigación, cada revisión, cada decisión, cada actualización del conocimiento vigente.
- **Responsabilidad.** No interpretar ni resumir — solo conservar, en orden, lo que sucedió y por qué.
- **Información que contiene.** Los hechos del proceso editorial a través del tiempo.
- **Relaciones.** Referencia a todas las demás entidades del dominio, sin pertenecer exclusivamente a ninguna.

### Publicación (fuera del dominio)

Se incluye aquí solo para justificar por qué se excluye. Publicar es hacer que un conocimiento sea visible y utilizable por el público final de UBIGUIA. Eso requiere pasos que no son investigar: traducir, narrar, dar formato, distribuir. La Publicación **consume** Conocimiento Vigente, pero las reglas que gobiernan cómo y cuándo algo se publica no son parte de lo que significa investigar. Pertenece a un dominio adyacente y posterior. Se la deja fuera de este modelo a propósito, y se retoma su relación con este dominio únicamente en la sección 8.

---

## 4. Qué cambia de estado

No se nombran estados todavía — solo se explica qué cosas evolucionan, por qué, y quién lo provoca.

**La Investigación** evoluciona porque producir conocimiento no es instantáneo ni infalible: hay un momento en que está en marcha, y un momento en que llega a una resolución. Quién provoca ese cambio: el propio desenlace del acto de investigar (si logra o no producir un Resultado válido) y, más adelante, el humano que revisa (cuando decide aceptar o rechazar lo producido).

**El Resultado** evoluciona en su condición de confiabilidad: nace como candidato, sin ningún peso propio, y solo adquiere (o pierde definitivamente) la posibilidad de ser confiable cuando alguien lo juzga. Quién provoca ese cambio: exclusivamente un humano, en el acto de Revisión.

**El Conocimiento Vigente** no evoluciona por etapas — se actualiza en un instante discreto: pasa de una versión a la siguiente cuando un Resultado aprobado se promueve. Quién provoca ese cambio: un acto humano de promoción, consecuencia directa de una Decisión Editorial favorable previa. No cambia por ninguna otra vía.

**La Entidad Investigable**, en sí misma, no tiene una condición propia independiente — su condición observable ("no investigada", "en investigación", "con conocimiento vigente desactualizado", etc.) es siempre un reflejo del estado de su Investigación activa y de la existencia o no de un Conocimiento Vigente. No es una fuente de estado, es un espejo.

---

## 5. Conocimiento generado vs. proceso editorial

Es necesario separar con claridad dos tipos de información que conviven en este dominio y que no deben confundirse:

**Pertenece al conocimiento generado** (información *sobre el mundo*, sobre la entidad): el contenido propuesto por un Resultado — su descripción, su historia, lo que la caracteriza — y las Fuentes que lo respaldan. Esto es lo que, eventualmente, se convierte en Conocimiento Vigente y, más adelante todavía, en algo publicable.

**Pertenece solamente al proceso editorial** (información *sobre el trabajo de producir* ese conocimiento, no sobre la entidad en sí): que hubo una Investigación y cuándo, quién la llevó a cabo, cuántos intentos hicieron falta, qué dijo una Observación al rechazar un Resultado, quién aprobó, cuándo se promovió. Nada de esto describe a la entidad — describe cómo UBIGUIA llegó a saber lo que sabe sobre ella.

Esta separación es la razón de fondo por la que, más adelante, ninguna decisión técnica debería mezclar estos dos tipos de información en un mismo lugar sin justificarlo explícitamente.

---

## 6. Permanencia de la información

**Es permanente:** el Conocimiento Vigente en cada momento de su historia (aun cuando se reemplace por una versión más nueva, el hecho de que existió esa versión y durante cuánto tiempo no debería borrarse), y el Historial completo, por definición.

**Es temporal, en el sentido de que pierde vigencia (no de que deba destruirse):** un Resultado en evaluación es relevante como "el candidato actual" solo mientras su Investigación sigue abierta. Una vez resuelto —aceptado o rechazado— deja de ser el candidato activo, pero el registro de que existió pasa a integrar el Historial, no desaparece.

**Nunca debería perderse:** la secuencia completa de decisiones editoriales y sus razones (por qué se rechazó algo, quién aprobó, cuándo), porque es la base de la confianza en el proceso; y el propio Conocimiento Vigente vigente en cada momento, de modo que siempre sea reconstruible qué consideraba cierto UBIGUIA sobre una entidad en cualquier punto del pasado.

---

## 7. Qué puede publicarse y qué nunca debe publicarse

**Puede publicarse**, eventualmente y tras procesos que exceden este dominio: el Conocimiento Vigente aprobado y promovido de una entidad.

**Nunca debe publicarse:** un Resultado que no fue aprobado; un Resultado rechazado; las Observaciones (son comentario editorial interno, no conocimiento validado para el público); y, en general, cualquier detalle del proceso editorial (quién investigó, cuántos intentos, qué proveedor o método se usó) — eso es información sobre el trabajo, no sobre la entidad, y no tiene lugar frente al usuario final.

Esta regla es consecuencia directa de la separación hecha en la sección 5: solo el conocimiento generado y aceptado cruza la frontera hacia la publicación; el proceso editorial nunca la cruza.

---

## 8. Aprobar, promover y publicar: ¿son lo mismo?

No. Son tres conceptos distintos, y confundirlos es la fuente más probable de errores de diseño más adelante.

**Aprobar** es un juicio: una afirmación humana de que un Resultado es suficientemente bueno para ser considerado confiable. Aprobar no cambia nada fuera del propio Resultado y de la Decisión Editorial que lo registra. Es un acto de evaluación, no de acción.

**Promover** es una transformación: el acto por el cual un Resultado ya aprobado pasa a convertirse en el nuevo Conocimiento Vigente de la entidad, reemplazando lo que había antes. Es consecuencia de una aprobación, pero no es la aprobación misma — es un paso distinto, deliberadamente separado, porque el juicio ("esto es bueno") y la acción ("esto ahora es lo oficial") no tienen por qué ocurrir necesariamente en el mismo instante ni deberían mezclarse conceptualmente.

**Publicar** pertenece a otro dominio: es hacer que un conocimiento (normalmente el Conocimiento Vigente, después de procesos adicionales ajenos a la investigación) llegue al público final de UBIGUIA. No es un acto de esta parte del dominio — es lo que ese dominio adyacente hace *después*, tomando como insumo lo que este dominio produjo.

En síntesis: **aprobar** juzga, **promover** actualiza la verdad interna, **publicar** la entrega hacia afuera. Son tres actos, de tres naturalezas distintas (evaluación, actualización de estado, distribución), y ninguno implica automáticamente al siguiente.

---

## 9. Qué significa una nueva investigación

Una nueva investigación es un nuevo intento de producir conocimiento candidato sobre una entidad. Conceptualmente:

**¿Sobrescribe la anterior?** No. Ninguna investigación puede alterar directamente el Conocimiento Vigente ni borrar un Resultado anterior. Lo único que puede modificar el Conocimiento Vigente es un acto de promoción, y ese acto ocurre después de una Decisión Editorial favorable, nunca automáticamente por el solo hecho de iniciar una nueva investigación.

**¿Genera una nueva versión?** Sí, en el sentido de que cada investigación produce, si tiene éxito en su fase de generación, un Resultado distinto y propio, no una edición del anterior. Cada Resultado es una propuesta completa, no un parche sobre la propuesta previa.

**¿Se conserva la historia?** Siempre. Cada investigación, cada Resultado que produjo, cada Revisión y cada Decisión Editorial quedan en el Historial, se hayan aceptado o no. Nada de esto se descarta por el hecho de que una investigación posterior haya tenido éxito donde una anterior falló o fue rechazada.

**Regla de dominio que se desprende de esto:** una entidad no puede tener más de una investigación abierta a la vez. Mientras una investigación no llegó a su resolución, no tiene sentido conceptual abrir otra en paralelo para la misma entidad — se generaría ambigüedad sobre cuál de los dos intentos es "el" candidato bajo evaluación. Una nueva investigación solo puede comenzar una vez que la anterior alcanzó su resolución (fue aceptada y promovida, fue rechazada, o no llegó a producir un Resultado válido).

> Decisión de implementación. Cómo se numeran, identifican o listan las sucesivas investigaciones y sus resultados se resolverá en la SPEC técnica.

---

## 10. Diagrama conceptual

```
                    ┌───────────────────────────────────────────────────────────────┐
                    │                DOMINIO DEL MOTOR DE INVESTIGACIÓN               │
                    │                                                                 │
                    │   ┌───────────────────────┐                                     │
                    │   │  Entidad Investigable   │                                     │
                    │   └───────────┬─────────────┘                                     │
                    │               │ 1                                                 │
                    │               │                                                   │
                    │      ┌────────┴─────────┐                                         │
                    │      │                  │                                         │
                    │      │ 0..1 activa       │ 0..1 (en cada momento)                  │
                    │      │ 1..* en el tiempo │                                         │
                    │      ▼                  ▼                                         │
                    │ ┌───────────────┐   ┌────────────────────┐                        │
                    │ │  Investigación  │   │ Conocimiento Vigente │◀──────────┐          │
                    │ └───────┬─────────┘   └────────────────────┘            │          │
                    │         │ 1                                              │ promueve │
                    │         │ realizada por                                  │          │
                    │         ▼                                                │          │
                    │ ┌───────────────┐                                        │          │
                    │ │  Investigador   │                                        │          │
                    │ │     (rol)       │                                        │          │
                    │ └───────────────┘                                        │          │
                    │                                                          │          │
                    │  Investigación ── 0..1 produce ──▶ ┌───────────────┐     │          │
                    │                                     │    Resultado    │─────┘          │
                    │                                     └───┬───────┬───┘                │
                    │                                0..* │       │ 0..*                    │
                    │                        respaldado    │       │ examinado por           │
                    │                              por     ▼       ▼                         │
                    │                          ┌────────┐     ┌──────────┐                   │
                    │                          │ Fuente  │     │ Revisión  │                   │
                    │                          └────────┘     └────┬─────┘                   │
                    │                                              │ 1 concluye en             │
                    │                                              ▼                           │
                    │                                    ┌───────────────────┐                 │
                    │                                    │ Decisión Editorial  │                 │
                    │                                    │ (aprueba / rechaza) │                 │
                    │                                    └─────────┬─────────┘                 │
                    │                                              │ 0..1 (obligatoria           │
                    │                                              │ si es rechazo)               │
                    │                                              ▼                             │
                    │                                       ┌─────────────┐                       │
                    │                                       │ Observación   │                       │
                    │                                       └─────────────┘                       │
                    │                                                                             │
                    │   Investigación, Revisión, Decisión Editorial y cada actualización            │
                    │   del Conocimiento Vigente dejan constancia permanente en:                    │
                    │                                                                             │
                    │                            ┌───────────────┐                                 │
                    │                            │   Historial     │                                 │
                    │                            └───────────────┘                                 │
                    │                                                                             │
                    └───────────────────────────────────────────┬───────────────────────────────┘
                                                                  │ consume
                                                                  ▼
                                                        ┌───────────────────┐
                                                        │     Publicación      │
                                                        │ (dominio adyacente,   │
                                                        │  fuera de este modelo)│
                                                        └───────────────────┘
```

---

## Cierre

Este modelo no resuelve todavía cómo se guarda nada, cómo se numera nada, ni qué tecnología produce un Resultado. Resuelve algo previo y más importante: qué cosas existen en este dominio, qué significan, y qué reglas las gobiernan entre sí. Cualquier decisión técnica posterior —incluida una revisión de la SPEC ya redactada— debería poder justificarse señalando a qué parte de este modelo responde. Si no puede, probablemente esté resolviendo un problema que este documento no reconoce como parte del dominio.

No se modificó ningún otro archivo del repositorio al generar este documento.
