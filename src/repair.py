from pathlib import Path
from constants import BROKEN_LANGUAGE_NAMES, LANGUAGES, LANGUAGE_FOLDERS, TEXT_FILE, META_FILE, POI_MASTER_FILE
from filesystem import ensure_dir
from poi_manager import normalize_master_file, normalize_utf8_in_poi

def poi_title_from_folder(poi_dir: Path) -> str:
    name = poi_dir.name
    if "-" in name:
        return name.split("-", 1)[1].strip()
    return name.strip()

def create_missing_master(poi_dir: Path) -> bool:
    master = poi_dir / POI_MASTER_FILE
    if master.exists():
        return False

    title = poi_title_from_folder(poi_dir)

    content = f"""# POI MASTER

# {title}

## 1. Identificación

Nombre: {title}

## 2. Descripción General

## 3. Historia

## 4. Qué observar

## 5. Curiosidades

## 6. Información útil

## 7. Resumen para audio

## 8. POIs relacionados

## 9. Palabras clave

## 10. Fuentes
"""

    master.write_text(content, encoding="utf-8")
    return True

def repair_poi(poi_dir: Path) -> list[str]:
    actions = []

    # Fix broken language folder names.
    for broken, fixed in BROKEN_LANGUAGE_NAMES.items():
        broken_path = poi_dir / broken
        fixed_path = poi_dir / fixed
        if broken_path.exists() and not fixed_path.exists():
            broken_path.rename(fixed_path)
            actions.append(f"Renombrado {broken} -> {fixed}")

    # Rename old POI_MASTER-*.md if it exists.
    if normalize_master_file(poi_dir):
        actions.append("POI_MASTER antiguo renombrado a POI_MASTER.md")

    # If no master exists at all, create a clean blank one.
    if create_missing_master(poi_dir):
        actions.append("Creado POI_MASTER.md faltante")

    # Ensure language structure.
    for lang in LANGUAGES:
        lang_dir = poi_dir / lang
        if not lang_dir.exists():
            ensure_dir(lang_dir)
            actions.append(f"Creada carpeta {lang}")

        for sub in LANGUAGE_FOLDERS:
            sub_dir = lang_dir / sub
            if not sub_dir.exists():
                ensure_dir(sub_dir)
                actions.append(f"Creada carpeta {lang}/{sub}")

        text_file = lang_dir / TEXT_FILE
        if not text_file.exists():
            text_file.write_text(f"# {poi_title_from_folder(poi_dir)}\n", encoding="utf-8")
            actions.append(f"Creado {lang}/texto.md")

        meta_file = lang_dir / META_FILE
        if not meta_file.exists():
            meta_file.write_text("{}", encoding="utf-8")
            actions.append(f"Creado {lang}/meta.json")

    converted = normalize_utf8_in_poi(poi_dir)
    if converted:
        actions.append(f"Archivos normalizados UTF-8: {converted}")

    return actions

def repair_city(city_dir: Path) -> list[str]:
    report = []
    if not city_dir.exists():
        return ["No existe la carpeta de ciudad."]

    for poi_dir in sorted([p for p in city_dir.iterdir() if p.is_dir()]):
        actions = repair_poi(poi_dir)
        if actions:
            report.append(f"[{poi_dir.name}]")
            report.extend([f" - {a}" for a in actions])

    if not report:
        report.append("No se encontraron cambios necesarios.")

    return report
