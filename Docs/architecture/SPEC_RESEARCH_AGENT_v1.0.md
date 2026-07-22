# SPEC — Motor de Investigación de UBIGUIA v1.0

| | |
|---|---|
| Estado | Diseño cerrado y aprobado. Pendiente de implementación. |
| Versión de esta spec | 1.0 |
| Fecha de cierre de diseño | 2026-07-21 |
| Documentos relacionados | `CLAUDE.md` (reglas permanentes del proyecto), `PROJECT_STATUS.md` (estado operativo) |

Este documento es el contrato técnico definitivo del Motor de Investigación de UBIGUIA. Toda implementación futura debe ajustarse a lo descripto acá. Si una decisión necesita cambiar, el cambio se discute y se refleja primero en este documento antes de tocar código.

No contiene código, clases ni firmas de funciones. Describe contratos de datos, responsabilidades y flujos.

**Regla de nomenclatura (permanente, vigente desde esta versión):** los conceptos, módulos, clases, funciones y archivos propios de UBIGUIA se nombran en español. No se traducen nombres impuestos por Python, Tkinter, Anthropic u otras dependencias externas, ni nombres ya existentes del proyecto cuya traducción rompería compatibilidad (por ejemplo `POI_MASTER.md`, `poi.json`, `research.json`, `historial.json`, `fuentes.md`, `TURISMO`, `ANTHROPIC_API_KEY`).

---

## 0. Decisiones fundacionales

Estas cuatro decisiones atraviesan todo el diseño y explican por qué la arquitectura no está modelada "para POIs" sino para conocimiento en general.

**A. El Motor de Investigación de UBIGUIA no investiga solamente POIs. Está diseñado como un motor de investigación genérico y reutilizable.**
Un POI es el primer tipo de entidad que este motor sabe investigar, no el único que sabrá investigar. Ciudades, barrios, recorridos, personajes, monumentos, eventos, árboles, esculturas, gastronomía, o cualquier entidad de conocimiento futura deben poder incorporarse **sin rediseñar el motor**, agregando únicamente un adaptador nuevo.
*Por qué:* si el motor se modela pensando solo en POIs, cada entidad nueva futura obliga a reescribir la orquestación, el manejo de estados y la UI. Modelarlo genérico desde el día uno cuesta un poco más de diseño ahora y ahorra una reescritura completa después.
*Ventaja:* la inversión en el motor (estados, historial, fuentes, aprobación, exportación) se amortiza sobre todos los tipos de entidad futuros, no solo sobre POIs.

**B. El conocimiento es el activo. Los productos derivados no lo son.**
Lo que el Motor de Investigación produce y el editor aprueba (`research.json`, `fuentes.md`, el borrador de ficha) es el activo real del sistema: la base de conocimiento turístico. El texto en español, las traducciones, los audios y el ZIP exportado son **vistas derivadas** de ese conocimiento, generadas para un consumo específico (la app móvil UBIGUIA). Son reproducibles a partir del conocimiento; el conocimiento no es reproducible a partir de ellas.
*Por qué:* si se trata al ZIP o al texto final como la fuente de verdad, cualquier cambio de formato de salida (nueva app, nuevo idioma, nuevo canal) obliga a re-investigar. Si la fuente de verdad es el conocimiento estructurado, generar un nuevo producto derivado es trabajo de transformación, no de investigación.
*Ventaja:* habilita todo lo que el brief original pedía como objetivo final ("textos, audios, traducciones, recorridos, folletos, futuras funcionalidades") sin volver a investigar cada vez.

**C. Tres ejes desacoplados: Motor de Investigación, Motor de Búsqueda, Modelo de IA.**
Son tres responsabilidades distintas y deben poder reemplazarse por separado:
- **Motor de Investigación** — orquesta el flujo (investigar → revisar → aprobar → exportar), gestiona estados y persistencia. No sabe nada de IA ni de búsqueda web.
- **Modelo de IA** — la capacidad de razonar, sintetizar y redactar.
- **Motor de Búsqueda** — la capacidad de encontrar información en fuentes externas.

En la práctica de v1.0, un mismo proveedor (`ProveedorInvestigacionAnthropic`) entrega Modelo de IA y Motor de Búsqueda juntos, porque la API de Claude ofrece búsqueda web integrada en la misma llamada de razonamiento. Esto es una decisión de implementación de **ese proveedor concreto**, no una fusión arquitectónica: el Motor de Investigación nunca ve la diferencia entre "modelo" y "búsqueda", solo ve un proveedor que cumple el contrato de investigación. Un proveedor futuro podría combinar un modelo de IA distinto con un motor de búsqueda separado (por ejemplo, otro LLM más una API de búsqueda externa) sin que el Motor de Investigación se entere.
*Por qué:* desacoplar en el punto exacto donde hoy existe una frontera real (motor de investigación vs. proveedor de investigación) es honesto con la tecnología disponible; prometer una interfaz separada para "búsqueda" cuando la propia API las entrega fusionadas sería una abstracción prematura y falsa.
*Ventaja:* cambiar de proveedor de IA es agregar un proveedor nuevo, sin tocar el motor. Si en el futuro conviene separar modelo y búsqueda dentro de un mismo proveedor, ese proveedor lo resuelve puertas adentro sin afectar el contrato con el motor.

**D. Toda decisión debe indicar por qué se tomó.**
A lo largo de este documento, las decisiones relevantes incluyen una nota `Por qué` / `Ventaja`. Esto no es cosmético: permite que en el futuro alguien evalúe si la razón original sigue siendo válida antes de cambiar algo.

---

## 1. Objetivo del Motor de Investigación

Automatizar la etapa de investigación previa a la redacción, que hoy es manual y es el principal cuello de botella de producción de contenido en Editor_UBIGUIA. El agente debe:

- descubrir entidades candidatas dentro de un alcance (en v1.0: POIs dentro de una ciudad);
- investigar una entidad ya existente reuniendo información de fuentes reales;
- detectar contradicciones entre fuentes;
- conservar la trazabilidad de cada fuente consultada;
- producir un borrador de ficha listo para revisión humana;

sin publicar, aprobar ni promover nada por sí mismo. El editor sigue siendo quien decide qué se incorpora a la base de conocimiento.

## 2. Alcance de la versión 1.0

**Incluido:**
- Motor de Investigación genérico (estados, historial, fuentes, promoción, exportación).
- Un único adaptador de entidad concreto: **POI**.
- Dos modalidades: investigar un POI existente, y descubrir POIs candidatos dentro de una ciudad ya cargada.
- Dos proveedores: `ProveedorInvestigacionSimulado` (sin red, sin costo, para desarrollo y pruebas) y `ProveedorInvestigacionAnthropic` (real, vía API de Claude con búsqueda web integrada).
- Integración con la UI existente de Editor_UBIGUIA vía el patrón de extensión ya usado (`apply_X(EditorClass)`).
- Exclusión de `_research/` en la exportación ZIP, y marcado automático de estado `EXPORTADO`.

**Explícitamente fuera de v1.0** (ver sección 4): adaptadores para ciudades, barrios, recorridos, personajes, monumentos, eventos, árboles, esculturas, gastronomía; cualquier proveedor que no sea Anthropic; traducción o generación de audio dentro del propio Motor de Investigación; publicación automática.

## 3. Qué problemas resuelve

- La investigación de un POI hoy depende enteramente del editor buscando, leyendo y comparando fuentes a mano fuera de la herramienta. El agente automatiza esa etapa.
- La ficha maestra (`POI_MASTER.md`) llega vacía o casi vacía a la etapa de redacción (confirmado revisando POIs reales del proyecto). El agente produce un borrador de ficha con contenido real y trazable.
- Hoy no existe ningún mecanismo de trazabilidad de fuentes: la sección "10. Fuentes" del template es un título sin contenido. El agente introduce ese mecanismo de forma estructurada.
- El descubrimiento de qué POIs cargar en una ciudad depende enteramente del criterio manual del editor. El agente puede proponer candidatos con justificación, sin decidir por el editor.

## 4. Qué problemas deliberadamente NO resuelve

- **No reemplaza el juicio editorial.** No aprueba, no publica, no decide qué POI incorporar.
- **No genera el texto final por idioma.** Eso sigue siendo responsabilidad del flujo `chatgpt_workflow.py` ya existente, que consume la ficha ya aprobada.
- **No traduce ni genera audio.** Fuera de alcance de este motor; son consumidores del conocimiento, no parte de la investigación.
- **No investiga otros tipos de entidad en v1.0.** La arquitectura lo permite (decisión A); la implementación de v1.0 no lo incluye.
- **No garantiza exactitud absoluta.** Reduce el trabajo manual y dificulta que pase contenido sin fuente, pero la verificación final sigue siendo humana.
- **No cita obligatoriamente cada frase** (decisión ya cerrada en la ronda anterior): exige trazabilidad a nivel de afirmación importante, no de oración por oración.

## 5. Filosofía general del módulo

1. El conocimiento es el activo (decisión B) — el motor optimiza para producir y conservar conocimiento estructurado y trazable, no para producir el texto final más rápido posible.
2. El motor es genérico; los tipos de entidad son plugins (decisión A) — nada en el núcleo del motor debe mencionar "POI" por nombre.
3. Ninguna escritura automática pisa contenido aprobado. Todo pasa por un estado intermedio explícito y una promoción explícita.
4. Toda fuente se conserva; toda afirmación importante debe poder rastrearse a una fuente.
5. Toda transición de estado y toda modificación relevante queda registrada en un historial append-only, nunca sobrescrito.
6. El agente nunca aprueba contenido: la aprobación es una acción humana, exclusiva y no delegable.
7. Cada eje reemplazable (motor de investigación / motor de búsqueda / modelo de IA) se trata como una frontera de diseño real, no como una promesa vacía (decisión C).

## 6. Arquitectura

```
                         ┌───────────────────────────────────────────┐
                         │                    Motor                   │
                         │  agnóstico de tipo de entidad y proveedor  │
                         │                                             │
                         │  - orquesta: investigar / descubrir /      │
                         │    revisar / aprobar / promover / exportar │
                         │  - gestiona estados y transiciones         │
                         │  - gestiona historial y fuentes            │
                         └───────────────┬─────────────────┬─────────┘
                                          │                 │
                     habla con            │                 │  habla con
                     contrato genérico    ▼                 ▼  contrato genérico
                ┌──────────────────────────────┐   ┌──────────────────────────────┐
                │      Adaptador de Entidad      │   │    Proveedor de Investigación │
                │                                │   │                                │
                │  v1.0: adaptador de POI        │   │  ProveedorInvestigacionSimulado│
                │  (futuro: Ciudad, Barrio,      │   │  ProveedorInvestigacionAnthropic│
                │   Recorrido, Personaje, ...)   │   │  (futuro: otros proveedores)  │
                │                                │   │                                │
                │  sabe DÓNDE y CÓMO viven los   │   │  sabe CÓMO investigar:        │
                │  archivos de esa entidad en    │   │  modelo de IA + motor de      │
                │  el filesystem del proyecto    │   │  búsqueda (ver decisión C)    │
                └──────────────────────────────┘   └──────────────────────────────┘
```

*Por qué esta separación en tres piezas y no dos:* si el Motor conociera directamente la estructura de carpetas de un POI, agregar "Ciudad" como entidad investigable obligaría a tocar el Motor. Si el Motor conociera directamente cómo hablarle a Claude, cambiar de proveedor obligaría a tocar el Motor. Separando ambos ejes, el Motor no cambia nunca por ninguno de los dos motivos — solo cambia si cambia la lógica de negocio del flujo en sí (estados, aprobación, exportación).

*Ventaja:* agregar un tipo de entidad nuevo = escribir un adaptador nuevo. Agregar un proveedor de IA nuevo = escribir un proveedor nuevo. Ninguna de las dos cosas toca la otra ni toca el Motor.

Ubicación en el filesystem del proyecto (Editor_UBIGUIA):

```
src/motor_investigacion/                # Motor de Investigación — agnóstico de entidad
├── __init__.py
├── entidad.py             # contrato de "entidad de conocimiento" y su contexto
├── estados.py              # estados + transiciones válidas + persistencia de research.json
├── proveedor.py             # contrato de "proveedor de investigación"
├── proveedor_simulado.py
├── proveedor_anthropic.py
├── motor.py                  # orquestación: investigar_entidad / descubrir_entidades /
│                              # ejecutar_investigacion / cambiar_estado / promover_a_master /
│                              # marcar_exportado
└── entidades/
    └── poi/                  # único adaptador concreto en v1.0
        ├── __init__.py
        └── adaptador.py       # cómo vive un POI en el filesystem de TURISMO

src/ui_investigacion.py         # extensión de UI (patrón apply_X(EditorClass) ya usado en el proyecto)
```

*Nota de nomenclatura:* el paquete se llama `motor_investigacion`, no `investigacion` ni `research`, para dejar explícito desde el nombre que es un motor genérico y no un módulo "de POIs".

## 7. Responsabilidades de cada componente

| Componente | Responsabilidad | Lo que NO hace |
|---|---|---|
| **Motor** (`motor.py`) | Orquesta el ciclo completo: pide contexto al adaptador, pide investigación al proveedor (`investigar_entidad()` / `descubrir_entidades()`), valida el resultado, escribe vía el adaptador, gestiona transiciones de estado (`cambiar_estado()`), escribe historial. Expone además `ejecutar_investigacion()`, `promover_a_master()` y `marcar_exportado()`. | No sabe qué es un POI ni qué es Claude. No decide si algo se aprueba. |
| **Estados** (`estados.py`) | Define los 5 estados válidos y qué transiciones están permitidas; implementa `cambiar_estado()`; lee/escribe `research.json`. | No decide *cuándo* debe ocurrir una transición — eso lo decide el Motor o el editor. |
| **Adaptador de Entidad** (ej. `entidades/poi/adaptador.py`) | Traduce entre el modelo genérico de "entidad" y la estructura real de archivos de ese tipo (para POI: dónde está `POI_MASTER.md`, dónde va `_research/`, qué template usar). | No conoce proveedores de IA ni hace llamadas de red. |
| **Proveedor de Investigación** (ej. `proveedor_anthropic.py`) | Dado un contexto de entidad, produce un resultado de investigación (`investigar_entidad()`) o una lista de candidatos (`descubrir_entidades()`). Internamente resuelve modelo de IA + búsqueda. | No escribe archivos. No conoce el filesystem de TURISMO ni el estado del POI. |
| **UI de Investigación** (`ui_investigacion.py`) | Expone botones y ventanas en el Editor existente; dispara acciones del Motor; nunca escribe archivos directamente. | No contiene lógica de negocio de investigación. |

*Por qué esta tabla importa:* fija explícitamente qué componente tiene permitido tocar el filesystem (solo el Motor, a través del Adaptador) y cuál tiene permitido llamar a una API externa (solo el Proveedor). Ningún otro componente debe cruzar esa línea.

## 8. Flujo completo de trabajo

```
Ciudad ya cargada en Editor_UBIGUIA
        │
        ▼
¿Investigar POI existente o descubrir POIs nuevos?
        │
   ┌────┴──────────────────────────────┐
   ▼                                    ▼
Investigar POI existente          Descubrir POIs de la ciudad
   │                                    │
   ▼                                    ▼
Motor pide contexto al             Motor pide contexto de ciudad
adaptador de POI                   al adaptador de POI
   │                                    │
   ▼                                    ▼
Motor llama a                      Proveedor.descubrir_entidades()
Proveedor.investigar_entidad()     devuelve lista de candidatos
   │                                (fuera de TURISMO, sin crear
   ▼                                 carpetas)
Proveedor devuelve borrador +           │
fuentes + contradicciones               ▼
   │                                Editor revisa candidatos y
   ▼                                selecciona cuáles crear
Motor ejecuta                           │
ejecutar_investigacion() y              ▼
escribe _research/                 Por cada seleccionado:
(estado BORRADOR → EN_REVISION)    poi_manager.create_poi()
   │                                (ya existente, sin cambios)
   ▼                                    │
Editor revisa                           ▼
   │                                pasa a "Investigar POI existente"
   ├── Observa ──▶ OBSERVADO       (mismo camino de la izquierda)
   │      │
   │      └──▶ vuelve a EN_REVISION tras corrección
   │
   └── Aprueba ──▶ APROBADO
              │
              ▼
     Motor ejecuta promover_a_master():
     POI_MASTER_BORRADOR.md → POI_MASTER.md
     (con respaldo del anterior)
              │
              ▼
     Flujo existente ES→EN→PT→Audio ya disponible con mejor ficha
              │
              ▼
     Exportación ZIP exitosa ──▶ Motor ejecuta marcar_exportado()
```

## 9. Flujo de estados

Estados válidos: `BORRADOR`, `EN_REVISION`, `OBSERVADO`, `APROBADO`, `EXPORTADO`.

| Transición | Disparada por | Automática / Manual |
|---|---|---|
| (no existe) → `BORRADOR` | Se crea `_research/` al iniciar una investigación (`ejecutar_investigacion()`) | Automática (Motor) |
| `BORRADOR` → `EN_REVISION` | La investigación terminó con un resultado válido | Automática (Motor) |
| `EN_REVISION` → `OBSERVADO` | El editor deja observaciones sin aprobar | Manual (editor) |
| `OBSERVADO` → `EN_REVISION` | Se corrige el borrador (nueva corrida o edición manual) | Manual/Automática según el caso |
| `EN_REVISION` → `APROBADO` | El editor aprueba | Manual (editor), exclusivo |
| `APROBADO` → `EN_REVISION` | El editor reabre para re-investigar (con confirmación) | Manual (editor) |
| `APROBADO` → `EXPORTADO` | El POI aprobado fue incluido en una exportación ZIP exitosa | Automática (Motor, disparada por exportación) |

Toda transición pasa por `cambiar_estado()`, que valida que la transición sea legal antes de aplicarla.

**Regla dura, sin excepción:** el Proveedor (el agente) nunca puede producir por sí mismo las transiciones hacia `APROBADO` ni hacia `EXPORTADO`. Solo el Motor (en respuesta a una acción humana explícita, o a una exportación real) puede hacerlo.

*Por qué:* es la traducción directa del principio "el agente nunca aprueba contenido" a una regla verificable en `estados.py`, no solo a una convención de UI.

Cada transición se registra en el historial (sección 15), incluyendo actor (`agent` o `editor`), timestamp y detalle.

## 10. Integración con Editor_UBIGUIA

- Se extiende la UI existente con el mismo patrón ya usado por `ui_chatgpt.py` y `status_patch.py`: una función que envuelve `EditorUBIGUIA` sin modificar `ui_main.py` directamente, registrada junto a los patches existentes en `main.py`.
- No se modifica `poi_manager.py`, `content_status.py`, `validator.py`, `constants.py` ni ningún template existente.
- El único componente nuevo que toca TURISMO es el adaptador de POI, y solo dentro de la subcarpeta `_research/` de cada POI (nunca fuera de ella, salvo el momento explícito de promoción).
- Las credenciales (`ANTHROPIC_API_KEY`) se leen de variables de entorno del sistema operativo, nunca de `config.local.json` ni de ningún archivo versionado.

## 11. Integración con el flujo ES → EN → PT → Audio

El Motor de Investigación termina exactamente donde empieza `chatgpt_workflow.py`: en un `POI_MASTER.md` con contenido real. No hay ningún cambio en ese flujo.

- `build_spanish_prompt()` ya lee `poi_dir / "POI_MASTER.md"` — una vez promovido el borrador, el botón "1. Generar Texto ES" ya existente trabaja automáticamente con una ficha mejor, sin ningún cambio de código en `chatgpt_workflow.py`.
- El orden operativo declarado en `PROJECT_STATUS.md` (texto ES → texto EN → texto PT → importación → audios → verificación → commit) no cambia; el Motor de Investigación se ubica **antes** de ese orden, como una etapa previa opcional.
- Si un editor no quiere usar el Motor de Investigación para un POI en particular, puede seguir completando `POI_MASTER.md` a mano como hasta ahora — el flujo existente no depende de que exista `_research/`.

## 12. Integración con la exportación ZIP

- `zip_export.py` excluye la carpeta `_research/` de cualquier POI al armar el ZIP. Es material editorial interno, nunca llega al programador.
- Tras una exportación exitosa, por cada POI incluido cuyo `research.json` esté en estado `APROBADO`, el Motor ejecuta `marcar_exportado()` y registra el nombre del ZIP.
- Un POI sin ninguna investigación asociada (sin carpeta `_research/`) se exporta exactamente igual que hoy — el pipeline de investigación es opcional y no bloquea ni condiciona la exportación.
- La estructura del ZIP entregado al programador no cambia respecto a la actual.

## 13. Estructura completa de archivos

Para un POI (único tipo de entidad implementado en v1.0):

```
POI/
├── POI_MASTER.md                 # sin cambios — ficha aprobada y vigente
├── poi.json                       # sin cambios
├── imagenes/                      # sin cambios
├── videos/                        # sin cambios
├── _research/                     # material editorial interno del Motor de Investigación
│   ├── research.json               # estado + metadatos + fuentes estructuradas
│   ├── POI_MASTER_BORRADOR.md       # borrador de ficha, no promovido todavía
│   ├── fuentes.md                   # fuentes en formato legible humano
│   ├── observaciones.md             # notas del editor cuando el estado es OBSERVADO
│   └── historial.json               # log append-only de eventos y transiciones
├── ESPAÑOL/  INGLES/  PORTUGUES/   # sin cambios
```

**Descubrimiento de POIs candidatos** (modalidad B): como los candidatos no deben crear carpetas automáticamente, sus datos viven **fuera de TURISMO**, en un directorio nuevo a nivel de proyecto:

```
research_discovery/
└── <PAIS>/<PROVINCIA>/<CIUDAD>/
    └── candidatos_<timestamp>.json
```

Nada se escribe dentro de `TURISMO/` hasta que el editor selecciona explícitamente qué candidatos crear; en ese momento se usa `poi_manager.create_poi()` (ya existente, sin cambios) y a partir de ahí ese POI sigue el camino normal de la modalidad A.

**Generalización a futuras entidades:** cuando se implemente un adaptador nuevo (por ejemplo, Ciudad), ese adaptador define su propia estructura de `_research/` equivalente, con el mismo contrato de archivos (`research.json`, borrador, `fuentes.md`, `observaciones.md`, `historial.json`) aplicado a la ubicación real de esa entidad en el filesystem del proyecto. Esta spec no fija esa estructura para entidades no implementadas — la fija solo para POI.

## 14. Formato detallado de `research.json`

```json
{
  "schema_version": "1.0",
  "entity_type": "POI",
  "entity_id": "mismo poi_id que poi.json",
  "state": "BORRADOR",
  "provider": "anthropic",
  "model": "claude-opus-4-8",
  "created_at": "2026-07-21T10:00:00",
  "updated_at": "2026-07-21T10:04:00",
  "approved_at": null,
  "exported_at": null,
  "export_zip": null,
  "sources": [
    {
      "id": "src-01",
      "title": "Historia del Pasaje Dardo Rocha",
      "url": "https://...",
      "site": "Municipalidad de La Plata",
      "consulted_at": "2026-07-21T10:02:00",
      "supports_sections": ["3. Historia", "5. Curiosidades"],
      "confidence": "alta",
      "notes": "Fuente oficial, coincide con otras dos.",
      "contradictions": []
    }
  ],
  "contradictions_detected": [
    {
      "topic": "año de inauguración",
      "sources": ["src-01", "src-03"],
      "detail": "src-01 indica 1883, src-03 indica 1884."
    }
  ]
}
```

Notas sobre el formato:
- `entity_type` existe desde v1.0 aunque hoy solo tenga el valor `"POI"` — es lo que permite que el mismo esquema sirva para futuras entidades sin romper compatibilidad (decisión A).
- `entity_id` reemplaza conceptualmente a un futuro "poi_id" genérico; en v1.0 es literalmente el mismo valor que `poi.json.poi_id`.
- `schema_version` permite evolucionar el formato sin romper archivos ya escritos.
- Los campos de fecha (`created_at`, `updated_at`, `approved_at`, `exported_at`) son ISO 8601 en hora local, igual que el resto del proyecto (ver `poi_manager.py`).
- `sources` es la versión estructurada de la misma información que aparece en `fuentes.md` (ver sección 16) — ambas deben mantenerse consistentes; el Motor es responsable de escribir las dos representaciones a partir de la misma fuente de datos, nunca de mantenerlas por separado.
- Los nombres de campos de este esquema (`schema_version`, `entity_type`, `state`, `sources`, etc.) quedan tal como fueron aprobados en la ronda de diseño anterior — la regla de nomenclatura en español (sección de encabezado) aplica a módulos, clases, funciones y archivos propios del código, no a este contrato de datos ya cerrado.

## 15. Formato de historial (`historial.json`)

Log append-only, separado de `research.json` para que cada evento sea inmutable y no requiera reescribir el archivo de estado completo.

```json
[
  {"timestamp": "2026-07-21T10:00:00", "event": "CREATED", "actor": "agent"},
  {"timestamp": "2026-07-21T10:04:00", "event": "STATE_CHANGE", "from": "BORRADOR", "to": "EN_REVISION", "actor": "agent"},
  {"timestamp": "2026-07-21T11:15:00", "event": "OBSERVATION_ADDED", "actor": "editor", "detail": "Falta verificar fecha de inauguración"},
  {"timestamp": "2026-07-21T11:16:00", "event": "STATE_CHANGE", "from": "EN_REVISION", "to": "OBSERVADO", "actor": "editor"},
  {"timestamp": "2026-07-21T15:00:00", "event": "STATE_CHANGE", "from": "OBSERVADO", "to": "EN_REVISION", "actor": "agent"},
  {"timestamp": "2026-07-21T15:30:00", "event": "APPROVED", "actor": "editor"},
  {"timestamp": "2026-07-21T15:30:00", "event": "PROMOTED", "master_backup": "POI_MASTER.md.bak-20260721-153000"},
  {"timestamp": "2026-07-07T18:00:00", "event": "EXPORTED", "zip": "LA_PLATA_POIS_20260707_v001.zip"}
]
```

Reglas:
- Nunca se borra ni se edita un evento existente.
- Todo evento `ERROR` (ver sección 19) también se registra acá, con el detalle suficiente para diagnosticar sin tener que reproducir la llamada.
- Este archivo es, junto con `research.json`, el registro de auditoría exigido por el principio "toda modificación debe quedar registrada".

## 16. Gestión de fuentes

Cada fuente relevante se registra en **dos formatos simultáneos**, generados a partir del mismo dato:

- **`research.json.sources`** — estructurado, para uso programático (por ejemplo, para que una futura funcionalidad calcule cobertura de fuentes por sección).
- **`fuentes.md`** — legible por humanos, para que el editor revise de un vistazo qué se consultó.

Campos por fuente (cuando estén disponibles — no todos son siempre obtenibles):
título, URL, entidad o sitio, fecha de consulta, secciones de la ficha que respalda, nivel de confianza, observaciones, contradicciones detectadas con otras fuentes.

**Nivel de exigencia de trazabilidad (decisión ya cerrada):** no se exige una cita por cada frase del borrador. Se exige que toda afirmación importante (dato histórico concreto, fecha, nombre propio, cifra) sea rastreable a una o más fuentes registradas en `sources`. El Proveedor es responsable de mantener esa trazabilidad al construir el borrador (`investigar_entidad()`); el Motor no verifica automáticamente cada frase — la verificación de que la trazabilidad es suficiente es parte de la revisión humana (sección 18).

## 17. Descubrimiento de entidades (POIs en v1.0)

- El descubrimiento opera sobre un **alcance** (en v1.0: una ciudad ya cargada en Editor_UBIGUIA) y produce, vía `descubrir_entidades()`, una lista de **candidatos** de un tipo de entidad (en v1.0: POI).
- Cada candidato incluye: nombre, tipo/categoría, descripción breve, relevancia estimada, fuentes encontradas, justificación de por qué tendría sentido incorporarlo a UBIGUIA.
- Los candidatos se muestran al editor antes de crear nada. El editor selecciona cuáles crear; ninguno se crea automáticamente (decisión ya cerrada, principio 12 de la ronda anterior).
- Al seleccionar candidatos, se usa `poi_manager.create_poi()` ya existente — el descubrimiento no introduce una forma alternativa de crear POIs.
- Una vez creado, cada POI seleccionado pasa a la modalidad "investigar POI existente" (sección 8), con el mismo flujo de estados que cualquier otro POI.
- **Generalización futura:** cuando se implementen adaptadores nuevos, el concepto de "alcance → candidatos de un tipo de entidad" se reutiliza (por ejemplo: descubrir personajes históricos dentro de un barrio). v1.0 no implementa ningún alcance ni entidad más allá de Ciudad → POI.

## 18. Criterios de aprobación

Un POI puede pasar de `EN_REVISION` a `APROBADO` únicamente cuando:

1. La acción la ejecuta un editor humano desde la UI del Editor — nunca el Proveedor ni un proceso automático.
2. El editor tuvo acceso, antes de aprobar, a: el borrador de ficha completo, la lista de fuentes, y cualquier contradicción detectada.
3. No es requisito técnico que todas las contradicciones estén resueltas — es una decisión editorial; el sistema las muestra, no las bloquea.
4. Aprobar dispara inmediatamente la promoción (`promover_a_master()`: `POI_MASTER_BORRADOR.md → POI_MASTER.md`, con respaldo del archivo anterior) como parte de la misma operación — no queda un estado intermedio donde algo esté "aprobado pero no promovido".

## 19. Tratamiento de errores

- **Resultados parciales se tratan como fallo, no como éxito parcial.** Si la respuesta del proveedor se corta, es rechazada por políticas de contenido, o no cumple la forma esperada, el estado no cambia y no se escribe ningún archivo de borrador incompleto.
- **Escritura atómica.** El Motor escribe a un archivo temporal y solo lo promueve a su nombre final si el resultado completo es válido — nunca deja `POI_MASTER_BORRADOR.md` a medio escribir.
- **Todo error se registra en `historial.json`** con evento `ERROR`, detalle suficiente para diagnóstico, y sin modificar el estado vigente del POI.
- **Reintentos de red/límite de uso** (errores transitorios del proveedor) se manejan a nivel del proveedor, de forma transparente para el Motor; si se agotan, se reportan como error normal.
- **Salida estructurada como mitigación de errores de formato.** El Proveedor exige al modelo de IA una respuesta con forma validable (no texto libre a interpretar), reduciendo la probabilidad de resultados mal formados frente al enfoque de marcadores de texto que usa hoy el flujo manual de `chatgpt_workflow.py`.
*Por qué:* ese flujo manual usa marcadores de texto (`<<<TEXT_ES>>>...`) porque depende de copiar y pegar desde un chat web sin control de formato. El Motor de Investigación sí tiene una API real, así que puede exigir una forma de respuesta verificable en vez de parsear texto libre — es una mejora justificada por tener una capacidad que el flujo anterior no tenía.
- **Costos.** El modelo de IA a usar queda configurable (no hardcodeado) para permitir que el editor use un modelo más económico en corridas exploratorias de descubrimiento, que pueden evaluar muchos candidatos. Esta configuración no involucra ningún secreto y puede vivir en la configuración local ya existente del proyecto.

## 20. Criterios de aceptación de la versión 1.0

1. El Motor no contiene ninguna referencia directa a "POI" en su núcleo (`motor.py`, `estados.py`, `proveedor.py`) — toda especificidad de POI vive exclusivamente en `entidades/poi/adaptador.py`.
2. Investigar un POI existente genera `_research/` completo (los 5 archivos) sin modificar `POI_MASTER.md`.
3. El estado nunca llega a `APROBADO` ni a `EXPORTADO` por acción del Proveedor — solo por acción explícita del editor o por una exportación real ya aprobada.
4. Aprobar promueve `POI_MASTER_BORRADOR.md` a `POI_MASTER.md`, conservando o registrando la versión anterior antes del reemplazo.
5. `fuentes.md` y `research.json.sources` son consistentes entre sí en todo momento.
6. El modo descubrimiento nunca crea carpetas de POI automáticamente.
7. El ZIP exportado no contiene `_research/` en ningún POI y mantiene la estructura actual esperada por el programador.
8. Un POI aprobado y exportado con éxito queda en `EXPORTADO`, con el nombre del ZIP registrado.
9. Ningún error de proveedor deja archivos corruptos, a medio escribir, o cambia el estado sin que corresponda.
10. El flujo ES→EN→PT→Audio existente sigue funcionando exactamente igual, sin ninguna modificación de código.
11. `ProveedorInvestigacionSimulado` permite ejercitar todo el Motor y toda la UI de Investigación sin red y sin costo.
12. Las credenciales de Anthropic no aparecen en ningún archivo versionado en Git.
13. Agregar un tipo de entidad nuevo en el futuro (fuera de alcance de v1.0) requeriría, según este diseño, únicamente un adaptador nuevo — sin modificar `motor.py`, `estados.py` ni `proveedor.py`. Este criterio se valida por inspección de diseño, no por implementación, ya que ningún adaptador adicional se construye en v1.0.

---

*Fin de la especificación. Cualquier cambio a este documento debe registrarse como una nueva decisión explícita, no como una edición silenciosa.*
