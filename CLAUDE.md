# CLAUDE.md

# Proyecto

Editor UBIGUIA

Sistema para administrar y generar el contenido turístico utilizado por UBIGUIA.

El objetivo principal es producir contenido de alta calidad y administrar los POIs de manera segura y consistente.

---

# Arquitectura

El proyecto administra:

- POIs
- Textos
- Traducciones
- Audios
- Imágenes
- Videos
- Metadatos
- Exportación

La estructura de carpetas definida para los POIs se considera estable.

---

# Principios del Proyecto

- Priorizar terminar funcionalidades antes que reorganizar el proyecto.
- No rediseñar estructuras ya aprobadas.
- No modificar la organización de carpetas salvo autorización.
- No mover automáticamente contenido existente.
- No generar documentación innecesaria.
- Priorizar producción de contenido sobre mejoras cosméticas.
- No reabrir decisiones ya aprobadas.
- Si una decisión figura en esta documentación, se considera definitiva salvo impedimento técnico objetivo.

---

# Estructura Oficial de un POI

Cada POI debe mantener la estructura oficial del proyecto.

Las carpetas compartidas:

- imagenes
- videos

Las carpetas específicas por idioma:

- ESPAÑOL
- INGLES
- PORTUGUES

Cada idioma mantiene:

- texto
- metadatos
- audio

---

# Flujo de Producción

El orden oficial de producción es:

1. Texto Español
2. Texto Inglés
3. Texto Portugués
4. Importación
5. Audio Español
6. Audio Inglés
7. Audio Portugués
8. Verificación
9. Commit

---

# Git

- Commits pequeños.
- Un cambio funcional = un commit.
- Compilar o validar antes de cada commit.
- Mantener origin/main sincronizado.

---

# Documentación

El proyecto utiliza únicamente estos documentos como referencia permanente:

- CLAUDE.md
- ROADMAP.md
- PROJECT_STATUS.md

No generar documentación adicional salvo que aporte valor real.