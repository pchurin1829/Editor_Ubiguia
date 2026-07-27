# PROJECT STATUS

Este documento refleja únicamente el estado actual del proyecto.

No constituye un historial de cambios. Para el detalle de las implementaciones realizadas deberá consultarse el CHANGELOG del proyecto.

---

# Estado General

Proyecto operativo.

Repositorio sincronizado con GitHub.

La estructura definitiva del Editor UBIGUIA se encuentra establecida.

Actualmente el desarrollo se encuentra dividido en dos grandes áreas:

- Editor de POIs
- Motor de Investigación

---

# Editor de POIs

## Implementado

✔ Organización definitiva de carpetas

✔ Gestión de imágenes

✔ Gestión de videos

✔ Gestión de audios

✔ Configuración local

✔ Alta y edición de POIs

✔ Generación de artículos mediante IA

✔ Sistema de Prompts

✔ Corrección del modal de Categoría

## Validado

✔ Organización de carpetas

✔ Gestión multimedia

✔ Configuración local

✔ Funcionamiento general del Editor

Pendiente únicamente la validación manual definitiva del modal de Categoría.

---

# Motor de Investigación

## Implementado

✔ Arquitectura del Motor de Investigación

✔ Flujo editorial completo

    Investigar → Revisar → Aprobar

✔ Proveedor Simulado

✔ Proveedor Anthropic

✔ Sistema de Prompts externos

✔ Infraestructura para versiones de Prompt

✔ Prompt Maestro de Investigación v1.0 integrado como prompt operativo

✔ Contrato real de salida estructurada (borrador, fuentes, contradicciones, observaciones, nivel de confianza)

✔ Búsqueda web integrada (herramienta oficial `web_search_20250305` del SDK de Anthropic)

✔ Integración con el Editor

✔ Suite de pruebas automatizadas

## Estado actual

Motor completamente operativo para la etapa actual.

El Prompt Maestro de Investigación v1.0 (`Docs/prompts/PROMPT_MAESTRO_INVESTIGACION_v1.0.md`) es la única fuente operativa del prompt utilizado por `ProveedorInvestigacionAnthropic`. El placeholder `PROMPT_INVESTIGACION_v1.md` fue retirado.

`ProveedorInvestigacionAnthropic` ya solicita búsqueda web real (herramienta oficial del SDK) en la misma llamada que genera la respuesta estructurada, y valida los errores propios de esa herramienta. La investigación completa (POI_MASTER definitivo con contenido verificado, contradicciones reales, nivel de confianza calculado a partir de fuentes reales) todavía está pendiente de integración — queda para el Paso 5B.

Total de pruebas automatizadas:

103 pruebas — todas aprobadas.

---

# Etapa Actual

FASE 2 — Editor de POIs

FASE 3 — Motor de Investigación

---

# Próxima Tarea

## Editor

- Validar manualmente el modal de Categoría.

## Motor de Investigación

- Paso 5B: integrar la búsqueda web ya disponible en una investigación completa (POI_MASTER definitivo, contradicciones reales, nivel de confianza calculado).
- Validarlo utilizando POIs reales.
- Ajustar la versión 1.1 del Prompt Maestro si fuera necesario.

---

# Pendiente para etapas futuras

Editor

- Historial
- Versionado
- Validación automática
- Revisión automática
- Administración multimedia
- Exportación
- Sincronización con la App

Motor de Investigación

- Descubrimiento automático de entidades
- Traducción automática
- Generación de audio
- Exportación ZIP
- Integración completa con el flujo editorial

---

# Última actualización

El Editor UBIGUIA se encuentra estable.

El Motor de Investigación se encuentra implementado y listo para comenzar la etapa de validación editorial mediante el Prompt Maestro de Investigación.