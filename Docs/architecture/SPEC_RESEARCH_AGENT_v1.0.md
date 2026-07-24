# SPEC — Motor de Investigación de UBIGUIA

Versión: 1.0
Estado: Propuesta — pendiente de aprobación para implementación
Alcance: especificación técnica. No contiene implementación.

Este documento es la traducción técnica del modelo de dominio descrito en `Docs/architecture/MODELO_CONCEPTUAL_RESEARCH_ENGINE_v1.0.md` ("el Modelo"). Toda decisión de esta SPEC debe poder señalarse contra un concepto de ese documento. Donde una decisión no tenga correlato conceptual necesario (formatos de archivo, nombres de campos, algoritmos concretos), se trata como decisión de implementación pura, sin pretensión de que el Modelo la determine.

Se apoya, además, en las convenciones ya vigentes en el Editor UBIGUIA (`src/poi_manager.py`, `src/chatgpt_workflow.py`, `src/config.py`, `src/constants.py`), a las que se ajusta en vez de reemplazarlas.

---

## 1. Objetivo

Producir, de forma asistida y auditable, el Resultado candidato de conocimiento narrativo sobre una Entidad Investigable, manteniendo la investigación completamente separada del Conocimiento Vigente hasta que un humano la revise y la promueva explícitamente.

El motor no reemplaza el criterio editorial: genera Resultados candidatos. Solo la aprobación humana, seguida de la promoción, actualiza el Conocimiento Vigente.

## 2. Principios de diseño

Estos principios son vinculantes para la implementación:

1. **Motor genérico, entidad desacoplada.** El motor no conoce POIs. Conoce `AdaptadorInvestigacion`. La entidad POI es la primera implementación de ese contrato, no una parte del motor.
2. **Proveedor intercambiable.** El motor no conoce Anthropic ni ningún proveedor concreto. Conoce `ProveedorInvestigacion`. El proveedor tampoco conoce POI (ver principio 9).
3. **Investigación ≠ Conocimiento Vigente.** Ningún Resultado producido por una investigación toca el Conocimiento Vigente directamente. Todo pasa primero por `_research/`.
4. **Aprobar y promover son actos distintos.** Aprobar es un juicio humano sobre un Resultado. Promover es la transformación que actualiza el Conocimiento Vigente a partir de un Resultado ya aprobado. El motor nunca promueve automáticamente al aprobar (Modelo, sección 8).
5. **Nada se pierde.** Cada investigación, cada revisión, cada decisión, cada actualización del Conocimiento Vigente queda en el historial. El historial es append-only.
6. **No se toca contenido existente.** El motor no migra, no recalcula ni reescribe POIs que no fueron explícitamente investigados. `_research/` se crea de forma perezosa, solo cuando se inicia una investigación.
7. **Prompts fuera del código.** Los prompts del motor viven en `Docs/prompts/` como archivos versionados. Esta decisión se aparta del patrón histórico del proyecto (prompts embebidos en `.py`, como en `chatgpt_workflow.py`) y queda aprobada explícitamente a pesar de esa diferencia.
8. **Consistencia con el proyecto existente.** Mismo patrón de extensión por `apply_*` usado por `status_patch.py` y `ui_chatgpt.py`, misma convención de `Path` como identificador operativo de POI, mismo esquema de templating `{{PLACEHOLDER}}` de `poi_manager.py`.
9. **La Investigación no tiene autoridad sobre datos estructurales.** Nombre, categoría, coordenadas, ciudad, provincia, país e identidad de la Entidad Investigable quedan fuera del alcance de cualquier Resultado, siempre, sin excepción (desarrollo completo en sección 15).
10. **Todo artefacto del proceso editorial queda excluido de cualquier artefacto de publicación.** Sin excepción, y sin depender de que se recuerde filtrarlo en el código de exportación (desarrollo completo en sección 20).
11. **Una Entidad Investigable no puede tener más de una Investigación activa simultáneamente.** Esta es una regla de dominio, no una restricción técnica de v1: proviene directamente del Modelo Conceptual (sección 9), que la fundamenta en evitar la ambigüedad sobre cuál Resultado es "el" candidato bajo evaluación.

## 3. Trazabilidad con el Modelo Conceptual

Cada concepto del Modelo tiene, en esta SPEC, exactamente una representación técnica:

| Concepto del Modelo | Representación técnica |
|---|---|
| Entidad Investigable | `entidad_id` (en v1, la `Path` de la carpeta del POI) |
| Investigación | El ciclo identificado por `investigacion_id`, cuyo estado operativo vive en `research.json` y cuya secuencia completa de eventos vive en `historial.jsonl` |
| Investigador (rol) | La instancia concreta de `ProveedorInvestigacion` en uso, registrada como `proveedor` en `research.json` y en los metadatos de `respuestas/`; el historial identifica los eventos automáticos con `actor: "sistema"`, sin repetir el nombre del proveedor en ese campo |
| Resultado | `POI_MASTER_BORRADOR.md` (contenido narrativo) + `fuentes.md` (fuentes que lo respaldan), como una unidad |
| Fuente | Cada entrada de `fuentes.md` |
| Observación | El texto de `observaciones_pendientes` en `research.json` (copia operativa del ciclo activo) y el campo `observacion` de cada evento en `historial.jsonl` (registro permanente y autoritativo) |
| Revisión | El evento de dominio `RESULTADO_REVISADO` en el historial; no es un estado propio del ciclo de vida (ver sección 6) |
| Decisión Editorial | Los estados `APROBADA` / `RECHAZADA`, y los eventos `RESULTADO_APROBADO` / `RESULTADO_RECHAZADO` |
| Conocimiento Vigente | Las secciones 2 a 10 de `POI_MASTER.md` (ver sección 16) |
| Historial | `historial.jsonl` |
| Publicación (fuera del dominio) | No representada dentro del motor; ver sección 20 para el único punto de contacto (exclusión obligatoria) |

Esta tabla es normativa: si una futura revisión de esta SPEC introduce una estructura técnica que no pueda ubicarse en esta tabla o justificarse como decisión de implementación pura, esa estructura debe reconsiderarse.

## 4. Visión general de la arquitectura

```
                         ┌───────────────────────┐
                         │   Editor UBIGUIA UI    │
                         │  (ui_investigacion.py) │
                         └───────────┬───────────┘
                                     │ usa
                                     ▼
                         ┌───────────────────────┐
                         │   MotorInvestigacion    │  ← genérico, sin
                         │   (motor.py)            │    conocimiento de POI
                         └─────┬──────────────┬────┘
                               │              │
                 implementa    │              │  implementa
                               ▼              ▼
                 ┌─────────────────────┐   ┌──────────────────────────┐
                 │ AdaptadorInvestigacion│   │  ProveedorInvestigacion   │
                 │      (contrato)       │   │       (contrato)          │
                 └──────────┬────────────┘   └───────────┬──────────────┘
                            │                              │
                            ▼                              ▼
                 ┌────────────────────┐     ┌────────────────────────────┐
                 │   AdaptadorPOI      │     │ ProveedorInvestigacionSimulado│
                 │  (adaptadores/poi.py)│     │ ProveedorInvestigacionAnthropic│
                 └──────────┬───────────┘     └────────────────────────────┘
                            │
                            ▼
              TURISMO/.../<NN-Nombre>/_research/
              TURISMO/.../<NN-Nombre>/POI_MASTER.md  (solo tras promoción)
```

El motor orquesta; el adaptador sabe *dónde* y *cómo* leer/escribir la entidad, y conoce su forma específica; el proveedor sabe *cómo* investigar, sin conocer la forma de ninguna entidad concreta.

## 5. Identidad de la entidad y regla de investigación activa

`entidad_id` en v1 es la `Path` absoluta de la carpeta del POI (`TURISMO/<país>/<provincia>/<ciudad>/<NN-Nombre>/`), igual que en `poi_manager.py` y `chatgpt_workflow.py`. No se introduce un identificador nuevo para no duplicar la resolución de rutas ya existente.

El `poi_id` (UUID de `poi.json`) se guarda dentro de `research.json` solo como referencia de auditoría, no como clave operativa.

**Regla de dominio:** una Entidad Investigable no puede tener más de una Investigación activa simultáneamente (principio 11). En la práctica, esto se garantiza porque existe, como máximo, un `research.json` por POI, y ese archivo representa siempre el único ciclo activo o más reciente. Esta regla proviene del Modelo Conceptual (sección 9) y no debe eliminarse ni relajarse en implementaciones futuras sin revisar primero el Modelo.

## 6. Estados del ciclo de vida

`EstadoInvestigacion` (enum de cadenas, persistido literal en `research.json`):

| Estado | Significado |
|---|---|
| `NO_INICIADA` | No existe `_research/research.json`. Estado implícito, nunca se persiste con este valor. |
| `EN_PROGRESO` | El Investigador está produciendo un Resultado. |
| `PENDIENTE_REVISION` | El Investigador produjo un Resultado válido. Está a la espera de que un humano lo examine y decida. |
| `FALLIDA` | La investigación no logró producir un Resultado válido. |
| `APROBADA` | Un humano aprobó el Resultado. El Conocimiento Vigente aún no fue actualizado. |
| `RECHAZADA` | Un humano rechazó el Resultado, con Observación obligatoria. |
| `PROMOVIDA` | El Resultado aprobado se convirtió en el nuevo Conocimiento Vigente. Estado terminal de ese ciclo. |

`PENDIENTE_REVISION` fusiona lo que una versión anterior de esta SPEC separaba en `COMPLETADA` y `EN_REVISION`. El Modelo describe la Revisión como un acto que examina un Resultado y concluye en una Decisión Editorial, sin reconocer un estado intermedio de "abierto para revisión pero sin decidir" como algo con significado propio (Modelo, sección 3). En consecuencia, **no existe una transición obligatoria equivalente a "abrir revisión"**: examinar el Resultado es una lectura, no un cambio de estado del dominio. El acto de Revisión queda representado como evento de historial (`RESULTADO_REVISADO`, sección 13), no como estado.

### 6.1 Transiciones válidas

```
NO_INICIADA ──iniciar()──────────────────▶ EN_PROGRESO
FALLIDA ──────reintentar()───────────────▶ EN_PROGRESO
RECHAZADA ────reintentar()───────────────▶ EN_PROGRESO
PROMOVIDA ────iniciar()──────────────────▶ EN_PROGRESO   (nuevo ciclo, version + 1)

EN_PROGRESO ──éxito del Investigador─────▶ PENDIENTE_REVISION
EN_PROGRESO ──error del Investigador─────▶ FALLIDA

PENDIENTE_REVISION ──aprobar()───────────▶ APROBADA
PENDIENTE_REVISION ──rechazar(observaciones)▶ RECHAZADA

APROBADA ─────promover()─────────────────▶ PROMOVIDA
```

Cualquier transición fuera de esta tabla lanza `ErrorInvestigacion`, nunca falla en silencio ni se ajusta al estado más cercano.

Toda transición, y el evento `RESULTADO_REVISADO` (que no es transición), se registran en el historial (sección 13).

## 7. Estructura de archivos por POI

Nueva subcarpeta, análoga en jerarquía a `imagenes/` y `videos/`, creada de forma perezosa (solo al llamar `iniciar()` por primera vez):

```
TURISMO/<país>/<provincia>/<ciudad>/<NN-Nombre>/
├── _research/
│   ├── research.json
│   ├── POI_MASTER_BORRADOR.md
│   ├── fuentes.md
│   ├── historial.jsonl
│   ├── respuestas/
│   │   └── YYYYMMDDTHHMMSS_<proveedor>.json
│   └── promovidos/
│       ├── v0001_POI_MASTER.md
│       ├── v0001_fuentes.md
│       ├── v0002_POI_MASTER.md
│       └── v0002_fuentes.md
├── POI_MASTER.md            (Conocimiento Vigente narrativo + Sección 1 estructural)
├── poi.json
├── imagenes/
├── videos/
├── ESPAÑOL|INGLES|PORTUGUES/...
```

Esta adición a la estructura oficial de un POI queda formalizada por este documento; su reflejo en `CLAUDE.md` (sección "Estructura Oficial de un POI") se realiza en una tarea posterior de documentación, no en esta.

### 7.1 `research.json`

Representa el **estado operativo de la investigación activa**. No es el historial definitivo — esa responsabilidad es exclusiva de `historial.jsonl`.

```json
{
  "investigacion_id": "identificador del ciclo actual",
  "poi_id": "uuid del poi.json (referencia de auditoría)",
  "estado": "PENDIENTE_REVISION",
  "version": 2,
  "proveedor": "anthropic",
  "intentos": 3,
  "creado_en": "2026-07-24T15:03:12",
  "actualizado_en": "2026-07-24T16:10:44",
  "ultima_promocion_en": null,
  "observaciones_pendientes": "",
  "huella_master_al_iniciar": "huella verificable del contenido de POI_MASTER.md al momento de iniciar este ciclo"
}
```

Reglas:
- `version` inicia en `1` al primer `iniciar()` y se incrementa en cada `promover()` exitoso (no en cada intento fallido).
- `intentos` cuenta llamadas al Investigador dentro del ciclo actual (se resetea a `0` al salir de `PROMOVIDA` hacia un nuevo `EN_PROGRESO`).
- `observaciones_pendientes` es la copia operativa del ciclo activo; el registro permanente y autoritativo vive en `historial.jsonl` (ver sección 3 y sección 13).
- `huella_master_al_iniciar` sostiene la protección contra sobrescritura descrita en la sección 17.

### 7.2 `POI_MASTER_BORRADOR.md`

Representa el **Resultado candidato completo** para el POI. Mantiene el mismo formato general que `POI_MASTER.md` (las diez secciones de `POI_MASTER_TEMPLATE.md`) para permitir revisión y comparación directa.

La Sección 1 (Identificación) que aparece en este archivo es completada por `AdaptadorPOI` con los datos estructurales **vigentes** de la entidad (no propuestos por la investigación), únicamente para que la comparación visual con `POI_MASTER.md` sea directa durante la revisión. El Investigador nunca escribe la Sección 1; si su respuesta la incluyera, el adaptador la descarta antes de guardar el borrador. Solo las secciones 2 a 10 son, en sentido estricto, el Resultado.

### 7.3 `fuentes.md`

Representación persistente y legible de las Fuentes que respaldan el Resultado. Tiene el mismo ciclo de vida que `POI_MASTER_BORRADOR.md`: ambos forman una única unidad conceptual (el Resultado, Modelo sección 3: *"el conocimiento propuesto... y las fuentes en las que ese conocimiento dice apoyarse"*). Se sobrescribe en cada nuevo intento, se conserva íntegro mientras el Resultado está pendiente de revisión o fue aprobado, y se snapshotea junto con `POI_MASTER_BORRADOR.md` en `promovidos/` al promover — de modo que las fuentes acompañan conceptualmente al conocimiento promovido y sobreviven después de la aprobación.

Formato: una entrada por fuente, distinguiendo referencia (URL o descripción si no hay URL), título o institución, autor, fecha de consulta y observaciones, cuando esos datos existan.

```markdown
## Fuentes utilizadas

- Referencia: https://ejemplo.org/archivo-historico
  Título o institución: Archivo Histórico Municipal
  Autor: —
  Fecha de consulta: 2026-07-24
  Observaciones: dato de fundación confirmado por dos fuentes independientes

- Referencia: registro interno, entrevista con guía municipal
  Título o institución: —
  Autor: —
  Fecha de consulta: —
  Observaciones: fuente oral, sin registro escrito verificable
```

No queda ningún campo estructurado de fuentes sin destino de persistencia: este archivo es la única representación de Fuente, y es obligatoria (un Resultado sin fuentes se guarda con este archivo indicando explícitamente que no se citaron fuentes, nunca se omite el archivo).

### 7.4 `historial.jsonl`

Ver sección 13.

### 7.5 `respuestas/YYYYMMDDTHHMMSS_<proveedor>.json`

Un archivo por intento (éxito o error), con el prompt exacto enviado y la respuesta cruda del Investigador, para auditoría y depuración. No se sobrescribe nunca.

El nombre de archivo usa un timestamp compacto sin separadores (`YYYYMMDDTHHMMSS`, por ejemplo `20260724T160312_anthropic.json`) para ser válido en Windows, donde `:` no es un carácter permitido en nombres de archivo.

```json
{
  "fecha_hora": "2026-07-24T16:03:12",
  "proveedor": "anthropic",
  "prompt": "texto completo enviado",
  "respuesta_cruda": "texto completo recibido",
  "metadatos": {"modelo": "ver sección 11.2", "tokens_entrada": 1820, "tokens_salida": 940, "duracion_s": 7.4}
}
```

### 7.6 `promovidos/`

Conserva la evolución histórica del Conocimiento Vigente: es la representación técnica de "el Conocimiento Vigente en cada momento de su historia" (Modelo, sección 6 — no debería borrarse). Un par de archivos por cada promoción exitosa, nombrados con el número de versión con cero relleno: `v0001_POI_MASTER.md`, `v0001_fuentes.md`, `v0002_POI_MASTER.md`, `v0002_fuentes.md`, etc. Nunca se sobrescribe una versión anterior.

## 8. Contrato: `MotorInvestigacion`

Módulo: `src/motor_investigacion/motor.py`. No conoce rutas de POI, ni Markdown de POI_MASTER, ni Anthropic.

```
MotorInvestigacion(adaptador: AdaptadorInvestigacion, proveedor: ProveedorInvestigacion)

estado(entidad_id) -> EstadoInvestigacion
iniciar(entidad_id) -> None
resultado_pendiente(entidad_id) -> ResultadoInvestigacion
aprobar(entidad_id, revisor: str, observaciones: str | None = None) -> None
rechazar(entidad_id, observaciones: str, revisor: str) -> None
reintentar(entidad_id) -> None
promover(entidad_id) -> None
historial(entidad_id) -> list[RegistroHistorial]
```

`resultado_pendiente()` reemplaza a la antigua `abrir_revision()`: es una consulta de solo lectura, no una transición de estado. Puede invocarse en cualquier estado que tenga un Resultado disponible (`PENDIENTE_REVISION`, `APROBADA`, `RECHAZADA`, `PROMOVIDA`), y su primera invocación sobre un Resultado en `PENDIENTE_REVISION` es lo que origina el evento de historial `RESULTADO_REVISADO` (sección 13).

`aprobar()` admite una observación opcional, alineado con el Modelo (sección 3: la Observación *"puede existir también acompañando una aprobación, como comentario adicional"*).

Responsabilidades:
- Validar la transición contra la tabla de la sección 6.1 antes de ejecutar cualquier efecto; si es inválida, lanza `ErrorInvestigacion` sin escribir nada.
- Delegar en el adaptador toda lectura/escritura de archivos, toda interpretación de la forma de la entidad, y toda validación de estructura del Resultado.
- Delegar en el proveedor toda llamada de investigación, sin pasarle ni esperar de él conocimiento sobre la forma de ninguna entidad concreta.
- Escribir siempre el evento correspondiente en el historial, incluso en caso de error.
- `iniciar()` internamente: valida transición → registra la huella del Conocimiento Vigente actual (para la sección 17) → persiste `EN_PROGRESO` → construye contexto vía adaptador → construye prompt vía adaptador → invoca al proveedor → si éxito, delega en `adaptador.validar_resultado()` → si la validación pasa, persiste el Resultado (`POI_MASTER_BORRADOR.md` + `fuentes.md`) y `PENDIENTE_REVISION`; si el proveedor falla o la validación del adaptador falla, persiste `FALLIDA` con el detalle en el historial.
- `promover()` internamente delega en `adaptador.promover()`, que aplica el mecanismo de encabezados reconocidos (sección 16) y la protección contra sobrescritura (sección 17) antes de escribir nada.

El proveedor se inyecta por instancia del motor; el cambio de proveedor (simulado ↔ Anthropic) se resuelve en la capa de integración (sección 19), construyendo el `MotorInvestigacion` con el proveedor correspondiente según configuración.

## 9. Contrato: `AdaptadorInvestigacion`

Módulo: `src/motor_investigacion/adaptadores/base.py`.

```
AdaptadorInvestigacion (interfaz)

ruta_research(entidad_id) -> Path
construir_contexto(entidad_id, investigacion_id) -> ContextoInvestigacion
construir_prompt(contexto: ContextoInvestigacion) -> str
validar_resultado(resultado: ResultadoInvestigacion) -> None   # lanza ErrorInvestigacion si la forma no es válida para esta entidad
promover(entidad_id, resultado: ResultadoInvestigacion) -> None
```

`validar_resultado()` es nueva respecto a versiones anteriores de esta SPEC: la validación de estructura y secciones deja de ser responsabilidad del proveedor genérico y pasa a ser exclusiva del adaptador, porque esa estructura (para POI: nueve encabezados correspondientes a `POI_MASTER_TEMPLATE.md`) es propia de cada tipo de entidad, no del acto de investigar en general.

### 9.1 `AdaptadorPOI` (v1)

Módulo: `src/motor_investigacion/adaptadores/poi.py`.

- `ruta_research(poi_dir)` → `poi_dir / "_research"`.
- `construir_contexto(poi_dir, investigacion_id)` lee `poi.json` (nombre, categoría, ciudad, provincia, país) y el `POI_MASTER.md` actual, y arma un `ContextoInvestigacion` genérico (sección 10) empaquetando todo lo específico de POI dentro de `contexto_descriptivo`, un contenido que el motor nunca abre ni interpreta.
- `construir_prompt(contexto)` carga `Docs/prompts/PROMPT_MAESTRO_INVESTIGACION_v1.0.md` + `Docs/prompts/PROMPT_INVESTIGACION_v1.md`, extrae los datos de `contexto.contexto_descriptivo`, reemplaza placeholders (mismo mecanismo `fill()` de `poi_manager.py`), y devuelve el prompt final. Ningún texto de prompt vive hardcodeado en este archivo.
- `validar_resultado(resultado)` verifica que `resultado.contenido` contenga exactamente los encabezados `## 2.` a `## 10.` esperados según `POI_MASTER_TEMPLATE.md`, en ese orden, sin duplicados ni faltantes, y con longitud mínima razonable. Si no cumple, lanza `ErrorInvestigacion`. Esta es la única validación de forma de todo el sistema, y vive exclusivamente aquí.
- `promover(poi_dir, resultado)`:
  1. Recalcula la huella del `POI_MASTER.md` vigente y la compara contra `huella_master_al_iniciar` (sección 17). Si difiere, aborta con conflicto, sin escribir nada, y exige revisión humana.
  2. Verifica que tanto `POI_MASTER_BORRADOR.md` como el `POI_MASTER.md` vigente calcen con el mecanismo de encabezados reconocidos (sección 16). Si no calzan, aborta sin escribir nada, registra el error, y exige revisión humana.
  3. Conserva íntegra la Sección 1 de `POI_MASTER.md` (dato estructural, no investigado).
  4. Reemplaza el bloque de las secciones 2 a 10 por el contenido de `POI_MASTER_BORRADOR.md`.
  5. Escribe `POI_MASTER.md` (UTF-8, `\n`).
  6. Copia `POI_MASTER_BORRADOR.md` a `promovidos/v<NNNN>_POI_MASTER.md` y `fuentes.md` a `promovidos/v<NNNN>_fuentes.md`.
  7. No borra `research.json` ni `historial.jsonl`.

Si el Resultado incluye advertencias sobre posibles datos estructurales (sección 15), `promover()` nunca las aplica: el mecanismo de encabezados reconocidos garantiza que solo puede escribirse dentro del bloque de secciones 2-10, nunca en la Sección 1 ni en `poi.json`.

## 10. `ContextoInvestigacion` (genérico)

Estructura de datos, no proveedor-específica y no entidad-específica:

```
ContextoInvestigacion:
  entidad_id: str            # identificador genérico de la entidad (v1: la ruta del POI, como texto)
  tipo_entidad: str          # p.ej. "poi"; en el futuro "ciudad", "personaje", "ruta", "museo", "hotel", "restaurante"
  contexto_descriptivo: <opaco para el motor y el proveedor>
  metadatos: dict            # metadatos genéricos (p.ej. idioma de trabajo), nunca específicos de una entidad
  investigacion_id: str      # ciclo de investigación al que pertenece este contexto
```

**La capa genérica no conoce, y no debe conocer:** `poi_name`, `city`, `province`, `country`, `category`, la existencia de `POI_MASTER`, cuántas secciones tiene, ni qué encabezados usa. Todo eso vive exclusivamente dentro de `contexto_descriptivo`, cuyo contenido es responsabilidad y conocimiento exclusivo del adaptador que lo produjo (`AdaptadorPOI` en v1) — ni `MotorInvestigacion` ni `ProveedorInvestigacion` lo interpretan en ningún punto del flujo.

## 11. Contrato: `ProveedorInvestigacion`

Módulo: `src/motor_investigacion/proveedores/base.py`.

```
ProveedorInvestigacion (interfaz)

nombre: str
investigar(prompt: str) -> ResultadoInvestigacion   # lanza ErrorInvestigacion en fallo
```

```
ResultadoInvestigacion:
  contenido: str             # conocimiento propuesto, en el formato acordado con el adaptador que solicitó la investigación
  fuentes: list[Fuente]
  advertencias: list[str]    # incluye señales sobre posibles datos estructurales a revisar (sección 15)
  metadatos: dict            # modelo, tokens, duración, lo que aplique por proveedor
```

```
Fuente:
  referencia: str                    # URL, o descripción si no hay URL
  titulo_o_institucion: str | None
  autor: str | None
  fecha_consulta: str | None
  observaciones: str | None
```

Validación mínima obligatoria en el proveedor, aplicable a cualquier entidad: `contenido` no vacío y de longitud razonable. **La validación de forma (estructura de secciones, encabezados esperados) no es responsabilidad del proveedor:** la realiza `AdaptadorInvestigacion.validar_resultado()` después de recibir el resultado (sección 9). Esta separación es lo que permite que el mismo proveedor sirva a cualquier adaptador futuro sin cambios.

### 11.1 `ProveedorInvestigacionSimulado`

Módulo: `src/motor_investigacion/proveedores/simulado.py`.

- No hace red. Determinista dado el mismo `ContextoInvestigacion` (útil para pruebas del motor, del adaptador y de la UI sin costo ni dependencia de API).
- Genera contenido placeholder marcado explícitamente con `[CONTENIDO SIMULADO — reemplazar]`, y al menos una `Fuente` simulada equivalente marcada de la misma forma, para que sea imposible promoverlo por error sin notarlo en la revisión.
- No conoce la forma esperada por ningún adaptador concreto: genera contenido siguiendo únicamente lo que `contexto_descriptivo` le pida a través del prompt construido por el adaptador.
- Nunca falla salvo que se le pida explícitamente simular un error (parámetro de test), para poder probar la rama `FALLIDA` del motor sin depender de Anthropic.

### 11.2 `ProveedorInvestigacionAnthropic`

Módulo: `src/motor_investigacion/proveedores/anthropic.py`.

- Requiere la librería `anthropic` (no instalada aún — instalación pendiente de aprobación en la tarea de implementación, no en esta spec).
- API key: variable de entorno `ANTHROPIC_API_KEY`. **No se guarda en `config.local.json` ni en ningún archivo versionado o no**, ni siquiera ignorado por git. Si la variable no está presente, `investigar()` lanza `ErrorInvestigacion` inmediatamente, sin intentar la llamada.
- Modelo: tomado de `config.local.json["research_model"]`. Esta SPEC no fija un modelo por defecto contractual. A título de ejemplo no vinculante, el valor `claude-sonnet-5` es una referencia razonable al momento de escribir este documento, pero el valor real se decide en configuración, no en código, y puede cambiar sin requerir una revisión de esta SPEC.
- Una sola llamada de mensaje (`prompt` completo como mensaje de usuario), sin streaming, con timeout configurable (constante `TIMEOUT_INVESTIGACION_S`, sugerido 180s).
- Cualquier excepción del SDK (red, autenticación, rate limit, contenido bloqueado) se captura y se re-lanza como `ErrorInvestigacion` con el mensaje original preservado en `detalle`, nunca se propaga la excepción nativa del SDK hacia el motor o la UI.
- Vuelca a `metadatos`: `modelo`, `tokens_entrada`, `tokens_salida`, `duracion_s`.
- No conoce la forma esperada por ningún adaptador concreto, por la misma razón que el proveedor simulado.

## 12. Prompts externos

Nuevos archivos (contenido a redactar en la tarea de implementación, no en esta spec), específicos de `AdaptadorPOI`:

- `Docs/prompts/PROMPT_MAESTRO_INVESTIGACION_v1.0.md`: reglas editoriales de la fase de investigación para POIs (equivalente en función a `PROMPT_MASTER_ES`, pero para producir la ficha/borrador, no el artículo final).
- `Docs/prompts/PROMPT_INVESTIGACION_v1.md`: plantilla concreta con placeholders `{{POI_NAME}}`, `{{CITY}}`, `{{PROVINCE}}`, `{{COUNTRY}}`, `{{CATEGORY}}`, `{{CONTENIDO_APROBADO_ACTUAL}}` y el formato de salida esperado (9 encabezados `##`, en el mismo orden que `POI_MASTER_TEMPLATE.md`).

Estos dos archivos son propiedad exclusiva de `AdaptadorPOI`. Un futuro adaptador para otra entidad (ciudad, personaje, ruta, museo, hotel, restaurante) definiría sus propios archivos de prompt bajo el mismo directorio (por ejemplo, `PROMPT_INVESTIGACION_CIUDAD_v1.md`), sin que el motor ni el proveedor necesiten saber que existen.

El versionado en el nombre del archivo (`_v1.0`, `_v1`) sigue el mismo criterio ya usado por este propio documento; una revisión de prompt que cambie el comportamiento del proveedor debe crear un archivo nuevo, no editar el vigente en caliente, para mantener trazabilidad con `respuestas/*.json`.

## 13. Historial — eventos de dominio

`_research/historial.jsonl`, un objeto JSON por línea, solo append, nunca reescritura ni compactación. Cada evento representa un hecho del dominio, no únicamente una transición técnica.

Campos mínimos de cada evento:

```json
{
  "evento_id": "identificador único del evento",
  "investigacion_id": "identificador del ciclo al que pertenece",
  "fecha_hora": "2026-07-24T15:03:12",
  "tipo_evento": "INVESTIGACION_INICIADA",
  "actor": "usuario:pchurin",
  "estado_anterior": "NO_INICIADA",
  "estado_nuevo": "EN_PROGRESO",
  "detalle": "",
  "observacion": null
}
```

`investigacion_id` en cada evento es lo que permite reconstruir, de forma directa y no inferida, qué eventos pertenecen a la misma Investigación.

Tipos de evento (mínimo; pueden ampliarse sin romper el formato):

| `tipo_evento` | Cuándo se registra |
|---|---|
| `INVESTIGACION_INICIADA` | `NO_INICIADA` → `EN_PROGRESO`, o `PROMOVIDA` → `EN_PROGRESO` (nuevo ciclo vía `iniciar()`) |
| `INVESTIGACION_REINTENTADA` | `FALLIDA`/`RECHAZADA` → `EN_PROGRESO` (vía `reintentar()`) |
| `INVESTIGACION_COMPLETADA` | `EN_PROGRESO` → `PENDIENTE_REVISION` |
| `INVESTIGACION_FALLIDA` | `EN_PROGRESO` → `FALLIDA` |
| `RESULTADO_REVISADO` | Primera llamada a `resultado_pendiente()` sobre un Resultado en `PENDIENTE_REVISION`; no cambia de estado (`estado_anterior` == `estado_nuevo`) |
| `RESULTADO_APROBADO` | `PENDIENTE_REVISION` → `APROBADA` |
| `RESULTADO_RECHAZADO` | `PENDIENTE_REVISION` → `RECHAZADA` |
| `CONOCIMIENTO_PROMOVIDO` | `APROBADA` → `PROMOVIDA` |
| `PROMOCION_ABORTADA` | El mecanismo de encabezados o la protección contra sobrescritura (secciones 16-17) impiden promover; no cambia de estado |

`actor` es `"sistema"` para transiciones automáticas (resultado del Investigador) y `"usuario:<nombre>"` para acciones humanas.

**Lectura tolerante a corrupción:** la lectura de `historial.jsonl` procesa línea por línea; si la última línea (u otra) no puede parsearse como JSON válido — típicamente por una escritura interrumpida — esa línea se descarta de la lectura, se conserva sin eliminar del archivo para inspección manual, y el resto del historial se devuelve como válido. Una línea corrupta nunca invalida las líneas anteriores.

## 14. Manejo de errores

Módulo: `src/motor_investigacion/excepciones.py`.

Una única excepción de dominio: `ErrorInvestigacion(mensaje: str, detalle: str | None = None)`. No se crean subclases por proveedor ni por adaptador salvo necesidad concreta descubierta durante la implementación.

El motor captura `ErrorInvestigacion` proveniente del proveedor o del adaptador (incluyendo fallos de validación de resultado, del mecanismo de encabezados, o de la protección contra sobrescritura), la registra en el historial con `detalle`, transiciona el estado cuando aplica (o registra un evento sin transición, como `PROMOCION_ABORTADA`), y la vuelve a lanzar hacia la UI. El motor nunca traga errores en silencio.

## 15. Datos estructurales: límites de autoridad de la Investigación

La Investigación no tiene autoridad para modificar, ni automática ni semiautomáticamente, ninguno de los siguientes datos de la Entidad Investigable: nombre, categoría, coordenadas, ciudad, provincia, país, ni ningún otro dato de identidad o ubicación estructural.

Esta regla es absoluta y no admite excepciones basadas en la confianza del Investigador, la claridad de la evidencia, ni la insistencia de un Resultado. Se fundamenta directamente en el Modelo: un Resultado contiene *"su descripción, su historia, lo que la caracteriza"* (sección 3), no datos de identidad, que pertenecen a la Entidad Investigable, gobernada por un proceso distinto.

Comportamiento esperado cuando un Resultado detecta una posible corrección estructural:

- Se presenta como advertencia editorial, en el campo `advertencias` de `ResultadoInvestigacion` (sección 11).
- Queda visible durante la revisión (la UI la muestra junto al Resultado, sección 19).
- Nunca se aplica automáticamente, bajo ninguna circunstancia.
- Su resolución, si corresponde, ocurre exclusivamente a través del proceso de mantenimiento de la Entidad Investigable ya existente en el Editor (edición manual de `poi.json` y de la Sección 1 de `POI_MASTER.md`), fuera del alcance del Motor de Investigación.

El mecanismo de encabezados reconocidos (sección 16) es la garantía técnica de que esta regla se cumple: `promover()` no puede, por construcción, escribir fuera del bloque de secciones 2-10.

## 16. Conocimiento Vigente y mecanismo de promoción

Declaración explícita:

- Las secciones 2 a 10 de `POI_MASTER.md` representan el **Conocimiento Vigente narrativo** del POI — la representación técnica directa de ese concepto del Modelo.
- `poi.json` y la Sección 1 de `POI_MASTER.md` representan **información estructural de la Entidad Investigable**, un concepto distinto del Modelo, fuera del dominio de la Investigación.
- La promoción actualiza **solamente** el Conocimiento Vigente narrativo (secciones 2-10). La promoción **nunca** modifica `poi.json` ni la Sección 1.

**Mecanismo seguro basado en encabezados reconocidos.** `AdaptadorPOI` mantiene la lista cerrada de los encabezados esperados (`## 2.` a `## 10.`, correspondientes a `POI_MASTER_TEMPLATE.md`). Antes de promover, valida que tanto `POI_MASTER_BORRADOR.md` como el `POI_MASTER.md` vigente contengan exactamente esos encabezados, en ese orden, delimitando bloques localizables sin ambigüedad.

Si la estructura del borrador o del archivo vigente no coincide con la esperada (encabezado faltante, duplicado, fuera de orden, o el vigente fue editado manualmente de forma que ya no calza con el patrón):

- se aborta la promoción sin escribir nada;
- `POI_MASTER.md` no se modifica;
- se registra el error en el historial (`PROMOCION_ABORTADA`, sección 13);
- se exige revisión humana; no hay reintento automático.

## 17. Protección contra sobrescritura concurrente de `POI_MASTER.md`

El Editor UBIGUIA permite hoy editar `POI_MASTER.md` manualmente en cualquier momento (`edit_master()` en `ui_main.py`), sin pasar por el Motor de Investigación. Para que una promoción no descarte silenciosamente una edición manual concurrente:

- Al iniciar una investigación (`iniciar()`), se registra en `research.json` una huella verificable del contenido de `POI_MASTER.md` vigente en ese momento (`huella_master_al_iniciar`).
- Antes de promover, se recalcula esa huella sobre el `POI_MASTER.md` actual y se compara contra la registrada.
- Si difieren, significa que el archivo cambió por otra vía mientras la investigación estaba en curso: se aborta la promoción, no se escribe nada, se informa el conflicto, y se exige revisión humana antes de continuar.

El algoritmo concreto de la huella (hash de contenido, fecha de modificación, u otro) no se fija en este documento; debe ser capaz de detectar cualquier modificación de contenido, no solo de metadatos de archivo.

## 18. Configuración

Cambios a `config.template.json` (y por copia, a `config.local.json` de cada instalación) — a aplicar en la tarea de implementación:

```json
{
  "research_provider": "simulado",
  "research_model": "claude-sonnet-5"
}
```

- `research_provider`: `"simulado" | "anthropic"`. Default `"simulado"` para que el motor sea usable y testeable sin API key desde el primer día.
- `research_model`: string libre, sin validación contra una lista cerrada en código. El valor de ejemplo mostrado arriba no es contractual (ver sección 11.2).
- La API key de Anthropic **no** se agrega a esta configuración (ver 11.2).

## 19. Integración con el Editor UBIGUIA

Sigue el patrón ya establecido por `status_patch.py` y `ui_chatgpt.py`, no introduce uno nuevo.

- Nuevo módulo `src/ui_investigacion.py` con `apply_research_ui(EditorUBIGUIA)`, aplicado en `src/main.py` junto a los `apply_*` existentes.
- Construye `MotorInvestigacion` con `AdaptadorPOI()` y el proveedor resuelto según `config.local.json["research_provider"]`.
- Sobre el POI actualmente seleccionado en el Editor (mismo `poi_dir` que ya usa `ui_chatgpt.py`), agrega:
  - Indicador del `EstadoInvestigacion` actual (`motor.estado(poi_dir)`).
  - Acción **Investigar** → `motor.iniciar(poi_dir)`.
  - Acción **Ver resultado pendiente** → `motor.resultado_pendiente(poi_dir)`, muestra `POI_MASTER_BORRADOR.md` y `fuentes.md`, junto con cualquier advertencia estructural (sección 15). Disponible siempre que exista un Resultado, no solo en `PENDIENTE_REVISION`.
  - Acciones **Aprobar** (con campo de observación opcional) / **Rechazar** (con campo de observaciones obligatorio) → `motor.aprobar` / `motor.rechazar`.
  - Acción **Promover a POI_MASTER** → `motor.promover(poi_dir)`, habilitada solo en estado `APROBADA`. Si `promover()` aborta por conflicto o por estructura inválida, la UI muestra el motivo exacto devuelto por `ErrorInvestigacion`.
  - Acción **Reintentar** → `motor.reintentar(poi_dir)`, habilitada en `FALLIDA` y `RECHAZADA`.
  - Vista de **Historial** → lista `motor.historial(poi_dir)`.
- No reemplaza ni modifica `ui_chatgpt.py`: el flujo de generación de texto ES/EN/PT sigue intacto y sigue leyendo `POI_MASTER.md` como fuente. El Motor de Investigación es un paso anterior y opcional que mejora esa fuente antes de generar el artículo.

## 20. Publicación: exclusión obligatoria del ZIP

**Principio de arquitectura obligatorio:** todo artefacto perteneciente al proceso de investigación y revisión editorial queda excluido de cualquier ZIP o artefacto de publicación. La carpeta `_research/` completa — en su totalidad, no una parte de ella — nunca debe exportarse.

`zip_export.py` deberá excluir explícitamente cualquier ruta cuyo componente sea `_research`, en cualquier nivel de profundidad bajo un POI. Esta modificación sobre `zip_export.py` queda fuera del alcance de esta SPEC (que no programa), pero su necesidad queda establecida aquí como requisito de arquitectura no negociable, y debe resolverse antes o junto con la primera implementación funcional del motor — el motor no se considera completo mientras esta exclusión no exista.

## 21. Control de versiones (Git)

**Se versiona:** `research.json`, `POI_MASTER_BORRADOR.md`, `fuentes.md`, `historial.jsonl`, `promovidos/`.

**No se versiona:** `respuestas/`. Contiene trazas técnicas y respuestas crudas del proveedor — información de proceso, de alto volumen y sin valor editorial curado — candidata a excluirse vía `.gitignore` (`_research/*/respuestas/` o equivalente) en la tarea de implementación.

## 22. Árbol completo de archivos nuevos (referencia para la implementación)

```
src/
  motor_investigacion/
    __init__.py
    estados.py            # EstadoInvestigacion
    modelos.py             # ContextoInvestigacion, ResultadoInvestigacion, Fuente, RegistroHistorial
    excepciones.py           # ErrorInvestigacion
    persistencia.py           # lectura/escritura de research.json, historial.jsonl, POI_MASTER_BORRADOR.md, fuentes.md
    motor.py                  # MotorInvestigacion
    adaptadores/
      __init__.py
      base.py                   # AdaptadorInvestigacion
      poi.py                     # AdaptadorPOI
    proveedores/
      __init__.py
      base.py                     # ProveedorInvestigacion
      simulado.py                  # ProveedorInvestigacionSimulado
      anthropic.py                  # ProveedorInvestigacionAnthropic
  ui_investigacion.py

Docs/
  prompts/
    PROMPT_MAESTRO_INVESTIGACION_v1.0.md
    PROMPT_INVESTIGACION_v1.md

tests/
  motor_investigacion/
    test_estados.py
    test_motor.py
    test_adaptador_poi.py          # incluye validar_resultado() y el mecanismo de encabezados
    test_proveedor_simulado.py
    test_proveedor_anthropic.py    # con mocks; nunca llama a la API real
```

## 23. Compatibilidad futura: otras entidades investigables

El núcleo (`MotorInvestigacion`, `ProveedorInvestigacion`, `ContextoInvestigacion`, `ResultadoInvestigacion`) no contiene, tras esta revisión, ningún nombre de campo ni regla de validación específica de POI. Investigar una ciudad, un personaje, una ruta, un museo, un hotel o un restaurante en el futuro requeriría únicamente:

- Un nuevo adaptador (`AdaptadorCiudad`, `AdaptadorPersonaje`, etc.) que implemente `AdaptadorInvestigacion`, con su propia forma de `contexto_descriptivo`, su propia `validar_resultado()`, y su propio mecanismo de promoción hacia lo que sea el Conocimiento Vigente de esa entidad.
- Sus propios archivos de prompt en `Docs/prompts/`.
- Opcionalmente, un proveedor distinto si el método de investigación lo justifica — aunque `ProveedorInvestigacionSimulado` y `ProveedorInvestigacionAnthropic` ya son reutilizables sin cambios, porque no conocen la forma de ninguna entidad.

Ninguno de estos agregados requiere modificar `motor.py`, `estados.py`, ni los contratos base. Esto es lo que el principio 1 ("motor genérico, entidad desacoplada") exige, y esta sección deja constancia de que, tras las correcciones de esta revisión, se cumple.

## 24. Fuera de alcance en v1

Explícitamente no se resuelve en esta versión, para no sobrediseñar:

- Descubrimiento automático de nuevas entidades (por ejemplo, POIs no registrados aún para una ciudad). El diseño motor/adaptador lo admite a futuro, pero no se especifica ni se implementa ahora.
- Adaptadores para entidades distintas de POI — arquitectónicamente habilitados (sección 23), no implementados en v1.
- Versionado avanzado más allá del contador simple de `research.json` (Fase 2 del ROADMAP, "Versionado", sigue pendiente como tema separado).
- Selección de proveedor por entidad individual (el proveedor se configura globalmente en `config.local.json`).
- Concurrencia multiusuario o locking de archivos (aplicación de escritorio, un usuario a la vez, igual que el resto del Editor).

## 25. Criterios de aceptación de la primera implementación

- `EstadoInvestigacion` tiene exactamente los 7 estados de la sección 6, y la tabla de transiciones de 6.1 está implementada y cubierta por tests que verifiquen que las transiciones inválidas lanzan `ErrorInvestigacion`.
- Con `ProveedorInvestigacionSimulado`, el ciclo completo `iniciar → aprobar → promover` funciona de punta a punta sobre un POI real del repositorio en un entorno de prueba, sin tocar `POI_MASTER.md` hasta el `promover()`, y sin requerir ninguna transición equivalente a "abrir revisión".
- `_research/` no se crea para ningún POI hasta que se llama `iniciar()` sobre ese POI puntual.
- `historial.jsonl` contiene un evento de dominio (no genérico) por cada hecho relevante del ciclo anterior, cada uno con su `investigacion_id`.
- La lectura de `historial.jsonl` tolera una última línea corrupta sin perder el resto del historial.
- `promover()` conserva intacta la Sección 1 de `POI_MASTER.md`, reemplaza únicamente las secciones 2 a 10, y aborta sin escribir nada si el mecanismo de encabezados reconocidos no calza o si se detecta una modificación concurrente de `POI_MASTER.md`.
- `fuentes.md` se genera junto con todo Resultado, incluso cuando no hay fuentes que citar, y sobrevive en `promovidos/` después de cada promoción.
- `ContextoInvestigacion` y `ResultadoInvestigacion`, tal como quedan implementados, no contienen ningún nombre de campo específico de POI.
- `ProveedorInvestigacionAnthropic` sin `ANTHROPIC_API_KEY` en el entorno falla con `ErrorInvestigacion` antes de cualquier intento de red.
- La UI (`ui_investigacion.py`) refleja el estado real leído del motor, no un estado propio en memoria.

## 26. Plan de pruebas (para la tarea de implementación, no para esta)

- Unitarias sobre `estados.py`: tabla de transiciones exhaustiva de los 7 estados.
- Unitarias sobre `motor.py`: cada método del motor con un adaptador y un proveedor *fake* (no el simulado real) para aislar la orquestación, incluyendo `resultado_pendiente()` como consulta sin efecto de estado.
- Unitarias sobre `adaptadores/poi.py`: `construir_contexto`, `construir_prompt`, `validar_resultado` (incluyendo casos de encabezados faltantes/duplicados/fuera de orden) y `promover` contra una carpeta de POI temporal (fixture), incluyendo el caso de reemplazo de secciones 2-10 preservando la Sección 1, y el caso de conflicto por modificación concurrente de `POI_MASTER.md`.
- Unitarias sobre `proveedores/simulado.py`: determinismo, generación de al menos una `Fuente` simulada, y validación de longitud mínima genérica (sin conocer estructura de secciones).
- Unitarias sobre `proveedores/anthropic.py`: con mock del cliente Anthropic; sin `ANTHROPIC_API_KEY`; con error del SDK simulado; nunca contra la API real en la suite automática.
- Unitarias sobre lectura de `historial.jsonl`: tolerancia a última línea corrupta.
- No se define aún el comando de ejecución de la suite (`pytest` u otro) porque no hay dependencias de testing instaladas en el proyecto; eso se decide y se propone antes de instalar nada, en la tarea de implementación.

---

Fin de la especificación.
