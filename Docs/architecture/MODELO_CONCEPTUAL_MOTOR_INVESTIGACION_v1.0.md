# Modelo Conceptual
# Motor de Investigación de UBIGUIA

Versión: 1.0

Estado: APROBADO

Autor: Proyecto UBIGUIA

---

# Propósito del Documento

Este documento define el modelo conceptual del Motor de Investigación de UBIGUIA.

Su finalidad es describir el dominio del problema y establecer un lenguaje común para todos los desarrolladores, analistas, editores y futuras inteligencias artificiales que participen del proyecto.

No describe cómo se implementa el Motor.

No define tecnologías.

No define estructuras de programación.

No describe proveedores de Inteligencia Artificial.

No especifica formatos de archivos.

Todos esos aspectos pertenecen a documentos de especificación técnica.

Este documento responde únicamente una pregunta:

**¿Qué existe dentro del dominio de la investigación de UBIGUIA?**

---

# Alcance

El Motor de Investigación constituye el primer eslabón del proceso editorial de UBIGUIA.

Su responsabilidad consiste en producir conocimiento estructurado sobre un Punto de Interés (POI).

Ese conocimiento será utilizado posteriormente para generar:

- artículos;
- traducciones;
- audios;
- material multimedia;
- contenido para aplicaciones;
- futuras publicaciones.

El Motor nunca publica contenido.

El Motor produce conocimiento.

---

# Objetivos

El Motor de Investigación persigue los siguientes objetivos permanentes.

## Objetivo 1

Investigar un Punto de Interés utilizando fuentes públicas y confiables.

---

## Objetivo 2

Organizar la información obtenida de forma estructurada.

---

## Objetivo 3

Conservar la trazabilidad de toda afirmación relevante.

---

## Objetivo 4

Permitir que un editor humano pueda revisar el resultado.

---

## Objetivo 5

Construir una base permanente de conocimiento reutilizable.

---

# Principios Fundamentales

Todo el Motor de Investigación se apoya sobre los siguientes principios.

Estos principios deberán mantenerse aunque cambien las tecnologías utilizadas.

---

## 1. El conocimiento es el activo principal.

Los artículos, audios, traducciones o cualquier otra salida son productos derivados.

El verdadero patrimonio del sistema es el conocimiento generado.

---

## 2. La investigación precede a la redacción.

Nunca debe escribirse un artículo antes de haber construido una investigación suficiente.

---

## 3. Toda afirmación importante debe poder justificarse.

Cada dato relevante debería poder rastrearse hasta una o más fuentes.

---

## 4. La incertidumbre también forma parte del conocimiento.

Cuando dos fuentes discrepan, el sistema no debe ocultar la contradicción.

Debe registrarla.

---

## 5. Nunca se completa información inventando datos.

La ausencia de información es preferible a una afirmación falsa.

---

## 6. El editor humano constituye la autoridad final.

La Inteligencia Artificial investiga.

El editor decide.

---

## 7. El conocimiento es permanente.

Los productos derivados pueden regenerarse tantas veces como sea necesario.

La investigación permanece.

---

# Modelo del Dominio

El Motor de Investigación se encuentra compuesto por un conjunto reducido de conceptos fundamentales.

Todos los procesos posteriores derivan de ellos.

Los conceptos principales son:

- Punto de Interés
- Investigación
- Conocimiento
- Fuente
- Evidencia
- Afirmación
- Observación
- Contradicción
- Documento de Investigación
- Producto Derivado

Estos conceptos representan el dominio conceptual del sistema.

No representan clases de programación.

---

# Punto de Interés (POI)

El Punto de Interés constituye la unidad principal de investigación.

Representa un lugar físico que posee valor turístico, histórico, cultural, arquitectónico, natural o social.

Todo el conocimiento generado por el Motor pertenece exactamente a un único Punto de Interés.

El POI constituye el centro alrededor del cual se organiza toda la información.

---

## Características

Un POI:

- posee identidad propia;
- puede investigarse múltiples veces;
- puede enriquecerse con nuevas investigaciones;
- permanece durante toda la vida del sistema.

El POI nunca desaparece cuando cambia el conocimiento.

---

# Investigación

La Investigación representa el proceso mediante el cual el Motor recopila, analiza y organiza información acerca de un Punto de Interés.

Una investigación comienza cuando existe un POI claramente identificado.

Finaliza cuando se obtiene un conocimiento suficientemente organizado para ser revisado.

La investigación constituye un proceso.

No constituye un documento.

---

## Objetivos de una Investigación

Una investigación busca:

- comprender el POI;
- reunir información confiable;
- detectar contradicciones;
- registrar incertidumbres;
- construir conocimiento verificable.

La investigación nunca tiene como objetivo producir directamente un artículo turístico.

---

# Conocimiento

El Conocimiento constituye el resultado principal de una investigación.

No representa texto.

No representa un documento.

No representa un artículo.

Representa la comprensión estructurada del Punto de Interés.

El conocimiento puede ampliarse, corregirse o enriquecerse con nuevas investigaciones sin modificar la identidad del POI.

Todo producto generado posteriormente deriva del conocimiento.

Nunca directamente de las fuentes.

---

# Fuente

Una Fuente representa cualquier origen de información utilizado durante una investigación.

Las fuentes permiten respaldar afirmaciones.

Pueden confirmar información existente.

Pueden aportar nueva información.

Pueden contradecir otras fuentes.

Las fuentes constituyen evidencia documental del proceso de investigación.

No todas las fuentes poseen el mismo nivel de confiabilidad.

La evaluación de esa confiabilidad forma parte de la investigación.

---

# Evidencia

La Evidencia constituye el elemento que permite respaldar una afirmación realizada durante la investigación.

Una evidencia puede estar formada por uno o varios elementos provenientes de una misma fuente o de múltiples fuentes.

Su finalidad es permitir que cualquier afirmación relevante pueda ser comprendida, revisada y eventualmente verificada por un editor humano.

La evidencia no reemplaza la afirmación.

La evidencia la respalda.

---

# Afirmación

Una afirmación representa una unidad mínima de conocimiento obtenida durante una investigación.

Ejemplos de afirmaciones:

- una fecha;
- un nombre;
- un acontecimiento;
- una característica arquitectónica;
- un dato histórico;
- una relación entre personas;
- una ubicación;
- una función original del edificio.

Toda investigación está compuesta por múltiples afirmaciones.

No todas poseen la misma importancia.

No todas requieren el mismo nivel de evidencia.

---

## Características de una afirmación

Una afirmación puede encontrarse en alguno de los siguientes estados conceptuales:

- Confirmada.
- Pendiente de verificación.
- Contradicha.
- Incompleta.

Estos estados representan conocimiento.

No representan estados de implementación.

---

# Observación

Una observación constituye una anotación realizada durante la investigación.

Su objetivo consiste en registrar información útil para el editor que no forma parte del conocimiento definitivo.

Ejemplos:

- dudas encontradas;
- posibles errores en las fuentes;
- hipótesis aún no verificadas;
- recomendaciones para futuras investigaciones;
- información pendiente de confirmar.

Las observaciones nunca forman parte del contenido publicado.

Constituyen únicamente soporte para el proceso editorial.

---

# Contradicción

Existe una contradicción cuando dos o más fuentes presentan información incompatible respecto de una misma afirmación.

Las contradicciones no representan errores del sistema.

Representan información relevante del proceso de investigación.

Su existencia debe conservarse.

La resolución corresponde al editor humano.

---

# Documento de Investigación

El Documento de Investigación representa la organización estructurada del conocimiento generado durante una investigación.

No constituye un artículo turístico.

No constituye una publicación.

No constituye una traducción.

Representa el estado actual del conocimiento disponible sobre un Punto de Interés.

Actualmente este documento se materializa mediante el archivo denominado:

POI_MASTER.md

Sin embargo, el modelo conceptual no depende de ese formato.

En futuras versiones podría representarse mediante cualquier otra estructura sin modificar el dominio.

---

# Producto Derivado

Todo contenido generado a partir del conocimiento recibe el nombre de Producto Derivado.

El conocimiento constituye la fuente común.

Los productos representan distintas formas de utilización de ese conocimiento.

Ejemplos:

- artículo en español;
- artículo en inglés;
- artículo en portugués;
- audio narrado;
- contenido para la aplicación móvil;
- contenido web;
- publicaciones futuras;
- material educativo.

Todos estos productos podrán regenerarse tantas veces como resulte necesario sin repetir la investigación.

---

# Actores del Dominio

Dentro del Motor de Investigación existen cuatro actores conceptuales.

---

## Investigador IA

Es el responsable de ejecutar el proceso de investigación.

Su función consiste en:

- buscar información;
- organizarla;
- identificar contradicciones;
- registrar evidencias;
- construir conocimiento.

No posee autoridad editorial.

---

## Editor Humano

Constituye la autoridad final del proceso.

Sus responsabilidades incluyen:

- revisar la investigación;
- aceptar o rechazar afirmaciones;
- resolver contradicciones;
- aprobar el Documento de Investigación.

Toda publicación requiere su intervención.

---

## Motor de Investigación

Representa el conjunto de procesos que permiten transformar información dispersa en conocimiento organizado.

No constituye una persona.

No constituye un proveedor de IA.

Constituye el proceso conceptual de investigación.

---

## Visitante

Es el destinatario final del conocimiento.

Nunca interactúa directamente con el Motor.

Accede únicamente a los productos derivados.

Sus necesidades constituyen la razón de existir del proceso de investigación.

---

# Estados Conceptuales de una Investigación

Toda investigación evoluciona siguiendo un ciclo de vida conceptual.

Estado 1

INICIADA

Existe un POI identificado.

Todavía no se ha recopilado información suficiente.

---

Estado 2

EN INVESTIGACIÓN

Se están recopilando fuentes.

Se generan afirmaciones.

Se registran observaciones.

Pueden aparecer contradicciones.

---

Estado 3

EN REVISIÓN

La investigación se considera suficientemente completa.

El editor analiza el resultado.

Puede solicitar modificaciones.

---

Estado 4

APROBADA

El conocimiento pasa a formar parte del patrimonio permanente del proyecto.

A partir de este momento pueden generarse productos derivados.

---

Estado 5

ACTUALIZADA

Nuevas investigaciones enriquecen el conocimiento existente.

El conocimiento evoluciona.

La identidad del POI permanece.

---

Estado 6

ARCHIVADA

La investigación deja de utilizarse activamente.

Permanece disponible únicamente con fines históricos.

# Relaciones Conceptuales

El dominio del Motor de Investigación se organiza alrededor de un conjunto reducido de relaciones permanentes.

Estas relaciones forman parte del modelo conceptual y deberán mantenerse independientemente de la tecnología utilizada.

---

## Relación 1

Un Punto de Interés puede poseer múltiples investigaciones.

Cada investigación pertenece siempre a un único Punto de Interés.

```
POI

1
│
├─────────────── N
        Investigación
```

---

## Relación 2

Toda investigación genera conocimiento.

El conocimiento siempre pertenece a una investigación.

```
Investigación

1
│
└─────────────── 1

Conocimiento
```

---

## Relación 3

El conocimiento está compuesto por múltiples afirmaciones.

Cada afirmación pertenece únicamente a un conocimiento.

```
Conocimiento

1
│
├─────────────── N

Afirmación
```

---

## Relación 4

Cada afirmación puede estar respaldada por una o más evidencias.

Cada evidencia puede respaldar múltiples afirmaciones.

```
Afirmación

N
│
├─────────────── N

Evidencia
```

---

## Relación 5

Toda evidencia proviene de una o más fuentes.

```
Fuente

1
│
├─────────────── N

Evidencia
```

---

## Relación 6

Una investigación puede contener observaciones.

Las observaciones pertenecen exclusivamente a la investigación donde fueron generadas.

---

## Relación 7

Una investigación puede contener contradicciones.

Las contradicciones forman parte del conocimiento disponible.

No representan errores.

---

## Relación 8

Una investigación aprobada produce un Documento de Investigación.

Actualmente dicho documento recibe el nombre de POI_MASTER.

Ese nombre pertenece a la implementación.

No al dominio.

---

## Relación 9

Del Documento de Investigación pueden derivarse múltiples productos.

Todos ellos comparten exactamente la misma base de conocimiento.

---

# Invariantes del Dominio

Las siguientes reglas deberán cumplirse siempre.

Representan restricciones propias del dominio.

No dependen de la implementación.

---

## Invariante 1

Todo conocimiento pertenece exactamente a un único Punto de Interés.

---

## Invariante 2

Toda investigación pertenece exactamente a un único Punto de Interés.

---

## Invariante 3

Una investigación nunca modifica la identidad del Punto de Interés.

Únicamente modifica el conocimiento disponible acerca de él.

---

## Invariante 4

Toda afirmación pertenece exactamente a una investigación.

---

## Invariante 5

Una fuente puede respaldar múltiples afirmaciones.

---

## Invariante 6

Una contradicción nunca debe eliminarse automáticamente.

Debe permanecer registrada hasta su resolución editorial.

---

## Invariante 7

La ausencia de información constituye un estado válido del conocimiento.

Nunca debe reemplazarse por información inventada.

---

## Invariante 8

El conocimiento aprobado constituye patrimonio permanente del proyecto.

Puede ampliarse.

Puede corregirse.

Nunca debe perder su trazabilidad.

---

# Ciclo de Vida del Conocimiento

El conocimiento evoluciona continuamente.

El ciclo conceptual completo es el siguiente.

```
Punto de Interés

↓

Investigación

↓

Fuentes

↓

Evidencias

↓

Afirmaciones

↓

Conocimiento

↓

Documento de Investigación

↓

Revisión Editorial

↓

Aprobación

↓

Productos Derivados

↓

Actualización

↓

Nueva Investigación

↓

Nuevo Conocimiento
```

El ciclo no termina con la publicación.

Cada nueva investigación puede enriquecer el conocimiento existente.

---

# Responsabilidades Conceptuales

El Motor de Investigación posee responsabilidades claramente delimitadas.

---

## El Motor debe

- investigar;
- recopilar información;
- identificar fuentes;
- registrar evidencias;
- detectar contradicciones;
- organizar conocimiento;
- producir un Documento de Investigación.

---

## El Motor no debe

- publicar contenido;
- resolver contradicciones editoriales;
- decidir qué información eliminar;
- modificar criterios editoriales;
- sustituir la revisión humana.

---

# Límites del Dominio

No pertenecen al Motor de Investigación los siguientes procesos.

- Traducción.
- Generación de audio.
- Publicación.
- Exportación.
- Administración multimedia.
- Sincronización con aplicaciones.
- Versionado del contenido.
- Distribución.

Estos procesos utilizan el conocimiento producido por el Motor, pero forman parte de otros subsistemas del proyecto.

---

# Integración con el Editor UBIGUIA

El Motor de Investigación constituye un subsistema del Editor.

Su única responsabilidad consiste en entregar conocimiento organizado.

El Editor utiliza posteriormente dicho conocimiento para generar y administrar los distintos productos derivados.

La separación entre ambos subsistemas deberá mantenerse en futuras versiones del proyecto.

# Glosario

## Punto de Interés (POI)

Entidad principal del dominio sobre la cual se desarrolla una investigación.

---

## Investigación

Proceso mediante el cual se recopila, analiza y organiza información acerca de un Punto de Interés.

---

## Conocimiento

Resultado estructurado obtenido durante una investigación.

Constituye el activo principal del Motor de Investigación.

---

## Fuente

Origen de la información utilizada durante la investigación.

---

## Evidencia

Elemento que respalda una afirmación.

---

## Afirmación

Unidad mínima de conocimiento obtenida durante una investigación.

---

## Observación

Nota destinada exclusivamente al proceso editorial.

No forma parte del contenido publicado.

---

## Contradicción

Incompatibilidad entre dos o más afirmaciones respaldadas por distintas fuentes.

Debe conservarse hasta su resolución editorial.

---

## Documento de Investigación

Representación organizada del conocimiento generado.

Actualmente se implementa mediante el archivo denominado POI_MASTER.md.

---

## Producto Derivado

Cualquier contenido generado utilizando el conocimiento aprobado.

Ejemplos:

- artículos;
- traducciones;
- audios;
- publicaciones;
- contenido para aplicaciones.

---

# Principios Permanentes

Los siguientes principios deberán mantenerse en cualquier evolución futura del Motor de Investigación.

## Principio 1

El conocimiento constituye el activo principal del sistema.

---

## Principio 2

Toda investigación pertenece a un único Punto de Interés.

---

## Principio 3

Toda afirmación relevante deberá poder justificarse mediante evidencia.

---

## Principio 4

Las contradicciones forman parte del conocimiento y nunca deberán eliminarse automáticamente.

---

## Principio 5

La Inteligencia Artificial investiga.

El Editor decide.

---

## Principio 6

La investigación precede siempre a la redacción.

---

## Principio 7

Los productos derivados podrán regenerarse sin repetir la investigación.

---

## Principio 8

La trazabilidad del conocimiento constituye un requisito permanente del sistema.

---

# Principios de Evolución

El presente modelo conceptual deberá permanecer estable a lo largo del tiempo.

Las futuras versiones del Motor podrán incorporar:

- nuevos proveedores de Inteligencia Artificial;
- nuevas fuentes de información;
- nuevos formatos documentales;
- nuevos productos derivados;
- nuevas tecnologías de implementación.

Sin embargo, ninguna de estas incorporaciones deberá modificar los conceptos definidos en este documento.

Cuando una evolución requiera alterar alguno de estos conceptos, deberá generarse una nueva versión del Modelo Conceptual.

Las modificaciones de implementación nunca deberán introducir cambios implícitos en el dominio.

---

# Relación con otros Documentos

La arquitectura documental del Motor de Investigación se organiza de la siguiente manera.

```

MODELO_CONCEPTUAL_MOTOR_INVESTIGACION

↓

SPEC_RESEARCH_AGENT

↓

PROMPT_INVESTIGACION

↓

Implementación

↓

Productos Derivados

```

Cada documento posee una responsabilidad claramente definida.

## MODELO CONCEPTUAL

Define el dominio.

Describe qué existe.

No describe cómo se implementa.

---

## SPEC

Define el comportamiento esperado del sistema.

Describe responsabilidades funcionales.

No define detalles de programación.

---

## PROMPT

Define el comportamiento esperado del modelo de Inteligencia Artificial.

No modifica el dominio.

No modifica la arquitectura.

---

## IMPLEMENTACIÓN

Materializa técnicamente las decisiones definidas en los documentos anteriores.

---

# Alcance de este Documento

Este documento constituye la referencia conceptual oficial del Motor de Investigación de UBIGUIA.

Las decisiones técnicas deberán respetar los conceptos aquí definidos.

Las implementaciones podrán evolucionar libremente siempre que no contradigan este modelo.

---

# Conclusión

El Motor de Investigación de UBIGUIA no tiene como finalidad producir artículos turísticos.

Su misión consiste en construir conocimiento confiable, estructurado y reutilizable acerca de los Puntos de Interés.

Ese conocimiento constituye un patrimonio permanente del proyecto.

Los artículos, traducciones, audios y cualquier otro contenido representan únicamente distintas formas de aprovechar ese conocimiento.

La separación entre conocimiento, investigación e implementación constituye uno de los principios fundamentales de la arquitectura del sistema y deberá preservarse en todas las futuras versiones.

---

# Estado del Documento

Versión:

1.0

Estado:

APROBADO

Tipo:

Modelo Conceptual

Ubicación:

Docs/architecture/

Archivo:

MODELO_CONCEPTUAL_MOTOR_INVESTIGACION_v1.0.md

---

DOCUMENTO FINALIZADO

Versión: 1.0

Estado:

✓ Listo para Git
