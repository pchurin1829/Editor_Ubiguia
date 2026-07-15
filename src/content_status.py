from pathlib import Path
import json
import re

# Frases típicas de las plantillas antiguas. Si aparecen varias,
# el archivo se considera todavía sin completar.
TEMPLATE_MARKERS = [
    "resumen corto",
    "historia / contexto",
    "historia/contexto",
    "cómo llegar",
    "como llegar",
    "si aplica",
    "entradas / precios",
    "entradas/precios",
    "links / referencias",
    "links/referencias",
    "créditos / fuentes",
    "creditos / fuentes",
    "escriba aquí",
    "escriba aqui",
    "indicación",
    "indicaciones",
    "consejos",
]

# Líneas informativas que no cuentan como contenido turístico real.
METADATA_PREFIXES = [
    "ciudad:",
    "provincia:",
    "país:",
    "pais:",
    "categoría:",
    "categoria:",
    "nombre:",
    "poi:",
    "idioma:",
]

def _strip_markdown(content: str) -> str:
    lines = []

    # Algunas plantillas antiguas quedaron guardadas en una sola línea.
    # Insertamos saltos antes de títulos Markdown para poder analizarlas.
    content = re.sub(r"\s+(#{1,6})\s+", r"\n\1 ", content)

    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Los títulos de sección no son contenido.
        if line.startswith("#"):
            continue

        # Eliminar marcas Markdown.
        line = re.sub(r"[*_`>|]", " ", line)
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        lowered = line.lower()

        # Eliminar datos de cabecera como Ciudad, Provincia, País, etc.
        if any(lowered.startswith(prefix) for prefix in METADATA_PREFIXES):
            continue

        lines.append(line)

    return "\n".join(lines)

def has_real_text(path: Path, min_chars: int = 100) -> bool:
    if not path.exists() or not path.is_file():
        return False

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    normalized = re.sub(r"\s+", " ", content.lower())

    # Si conserva varias frases de la plantilla, todavía no está completo.
    marker_count = sum(1 for marker in TEMPLATE_MARKERS if marker in normalized)
    if marker_count >= 2:
        return False

    cleaned = _strip_markdown(content)

    # Eliminar restos de instrucciones entre paréntesis.
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Exigir texto narrativo real, no sólo etiquetas o palabras sueltas.
    alpha_chars = sum(1 for char in cleaned if char.isalpha())
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", cleaned)

    return (
        len(cleaned) >= min_chars
        and alpha_chars >= 80
        and len(words) >= 18
    )

def has_valid_json(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(data, dict) and bool(data)

def count_media(folder: Path, extensions: set[str]) -> int:
    if not folder.exists():
        return 0
    return sum(
        1 for file in folder.rglob("*")
        if file.is_file() and file.suffix.lower() in extensions
    )
