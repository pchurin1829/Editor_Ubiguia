# Editor UBIGUIA — Estado del proyecto

## Última actualización

2026-07-16 — equipo/ruta de trabajo: D:\Editor_UBIGUIA

## Objetivo del sistema

Editor UBIGUIA administra POIs (puntos de interés) turísticos: sus textos por idioma, audios, imágenes, videos, metadatos, validación y exportación.

## Ruta oficial de trabajo

La raíz oficial de contenidos es:

D:\Editor_UBIGUIA\TURISMO

La copia del pendrive F: no es la carpeta oficial de trabajo.

## Estructura definitiva de cada POI

```
POI/
├── POI_MASTER.md
├── poi.json
├── imagenes/
├── videos/
├── ESPAÑOL/
│   ├── texto.md
│   ├── meta.json
│   └── audio/
├── INGLES/
│   ├── texto.md
│   ├── meta.json
│   └── audio/
└── PORTUGUES/
    ├── texto.md
    ├── meta.json
    └── audio/
```

Aclaraciones:

- `imagenes` y `videos` son compartidos entre los tres idiomas.
- `audio` es independiente por idioma.
- Las carpetas antiguas dentro de los idiomas no se eliminan automáticamente.
- `ensure_poi_structure()` (src/poi_manager.py) crea las carpetas faltantes de forma segura, sin borrar nada existente.

## Trabajo completado

- TURISMO incorporado al repositorio Git.
- Normalización automática de estructura de POIs.
- Creación de `imagenes` y `videos` compartidos en la raíz del POI.
- Creación de `audio` dentro de cada idioma.
- Botón Imágenes verificado.
- Botón Videos verificado.
- Configuración local (`config.local.json`) apuntando a D:\Editor_UBIGUIA\TURISMO.
- Diagnóstico confirmado: `status_patch.update_status` (no la versión de `ui_main.py`, que queda sobreescrita) es el método real ejecutado al seleccionar un POI en la lista.
- Texto ES del Pasaje Dardo Rocha generado e importado anteriormente.
- Corrección del modal de "Categoría (opcional)" en el alta de POIs: ventana propia (`Toplevel`) con `transient`, `grab_set`, `lift`, `focus_force`, `wait_window`, centrado, foco inicial en el campo, Enter confirma, Escape/X cancela; tras la creación se refresca la lista, se selecciona y se hace scroll al POI nuevo, y se actualiza el panel de estado antes del mensaje final. Commiteada en `6486075 "Corrige ventana modal para categoria opcional de POIs"`.

## Decisiones vigentes

- No rediseñar nuevamente la estructura de carpetas.
- No mover automáticamente imágenes antiguas.
- No subir audios o videos pesados sin evaluar previamente su impacto en Git.
- Un POI debe completarse en el orden:
  1. texto ES;
  2. texto EN;
  3. texto PT;
  4. importación;
  5. audio ES;
  6. audio EN;
  7. audio PT;
  8. verificación;
  9. commit.
- Priorizar producción de contenido sobre nuevas reorganizaciones.

## Cambios pendientes actuales

1. Validar manualmente el modal de "Categoría (opcional)" (ya commiteado, falta validación interactiva):
   - aparece al frente;
   - recibe foco;
   - Enter confirma;
   - Escape cancela;
   - no queda oculto;
   - al confirmar se refresca la lista y se selecciona el POI nuevo.

2. Decidir qué hacer con estos POIs de prueba sin trackear (creados durante las pruebas del bug del modal):
   - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/21-Legislatura`
   - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/22-Tribunales`
   - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/23-Casa Curuchet`

   No borrarlos automáticamente.

3. Completar las pruebas funcionales restantes del Editor.

4. Continuar con Pasaje Dardo Rocha:
   - recuperar o regenerar texto ES en la carpeta oficial;
   - generar EN;
   - generar PT;
   - generar audios.

## Cambios locales al momento de esta actualización

Según `git status` al momento de escribir este documento:

- `src/ui_main.py` **no** aparece modificado: el fix del modal de categoría ya está commiteado (`6486075`) y la rama está sincronizada con `origin/main`.
- Sin trackear (untracked), sin modificar en esta sesión:
  - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/21-Legislatura/`
  - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/22-Tribunales/`
  - `TURISMO/ARGENTINA/BUENOS AIRES/LA PLATA/23-Casa Curuchet/`
- Nuevos en esta actualización: `CLAUDE.md` y `PROJECT_STATUS.md` (sin trackear hasta el commit de esta tarea).

Último commit relevante: `6486075 Corrige ventana modal para categoria opcional de POIs`.

## Cómo retomar en otra PC

1. Abrir una terminal en el repositorio.
2. Ejecutar:
   ```
   git pull
   ```
3. Abrir Claude Code desde la raíz del proyecto.
4. Pedir:
   "Leé CLAUDE.md y PROJECT_STATUS.md, verificá git status y continuá desde la tarea pendiente actual."

## Próxima tarea concreta

Validar manualmente la corrección del modal de "Categoría (opcional)" antes de comenzar nuevas funcionalidades.
