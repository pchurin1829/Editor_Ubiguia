from pathlib import Path
from constants import LANGUAGES, LANGUAGE_FOLDERS, TEXT_FILE, META_FILE, POI_JSON, POI_MASTER_FILE

def validate_poi(poi_dir: Path) -> list[str]:
    errors = []

    if not (poi_dir / POI_MASTER_FILE).exists():
        errors.append("Falta POI_MASTER.md")

    if not (poi_dir / POI_JSON).exists():
        errors.append("Falta poi.json")

    for lang in LANGUAGES:
        lang_dir = poi_dir / lang
        if not lang_dir.exists():
            errors.append(f"Falta carpeta {lang}")
            continue

        if not (lang_dir / TEXT_FILE).exists():
            errors.append(f"Falta {lang}/texto.md")

        if not (lang_dir / META_FILE).exists():
            errors.append(f"Falta {lang}/meta.json")

        for folder in LANGUAGE_FOLDERS:
            if not (lang_dir / folder).exists():
                errors.append(f"Falta {lang}/{folder}/")

    return errors

def validate_text(poi_dir: Path) -> str:
    errors = validate_poi(poi_dir)
    if not errors:
        return "POI válido."
    return "\n".join(errors)
