# Editor UBIGUIA — Instrucciones permanentes

## Inicio obligatorio de cada sesión

Antes de modificar cualquier archivo:

1. Leer CLAUDE.md completo.
2. Leer PROJECT_STATUS.md completo.
3. Ejecutar git status.
4. Revisar los últimos commits relevantes.
5. Confirmar cuál es la tarea pendiente actual.
6. No asumir que una tarea anterior quedó completa: verificar código, Git y filesystem.

## Principios de trabajo

- Priorizar terminar tareas antes que rediseñar o mejorar continuamente.
- No cambiar arquitectura, estructura de carpetas ni decisiones aprobadas salvo que exista un problema real.
- No crear documentación nueva salvo que sea imprescindible.
- Mantener los cambios pequeños, verificables y con alcance claro.
- No borrar, mover ni sobrescribir archivos existentes sin confirmación.
- No hacer commit ni push salvo que el usuario lo pida expresamente.
- Antes de un commit, revisar git diff y git status.
- No usar git add . cuando existan archivos de prueba, temporales o no relacionados.
- Agregar al commit solamente los archivos correspondientes a la tarea.
- No incluir credenciales, claves API, contraseñas ni archivos locales sensibles.

## Regla obligatoria de cierre de sesión

Antes de terminar cualquier sesión que haya modificado el proyecto:

1. Actualizar PROJECT_STATUS.md.
2. Registrar:
   - fecha;
   - qué se completó;
   - qué quedó pendiente;
   - decisiones nuevas;
   - pruebas realizadas;
   - archivos modificados;
   - último commit relevante, si existe;
   - instrucción concreta para retomar.
3. Ejecutar git status.
4. Informar claramente si existen cambios sin commit o archivos sin trackear.
5. No declarar la tarea terminada si PROJECT_STATUS.md quedó desactualizado.

## Fuente de verdad

- El código y Git son la fuente de verdad técnica.
- CLAUDE.md contiene las reglas permanentes.
- PROJECT_STATUS.md contiene el estado operativo actual.
- Las conversaciones anteriores son contexto auxiliar, no la fuente principal.
