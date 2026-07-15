from pathlib import Path
from constants import (
    LANGUAGES, TEXT_FILE, META_FILE, POI_JSON,
    POI_MASTER_FILE, SHARED_IMAGES_FOLDER, AUDIO_FOLDER
)
from content_status import has_real_text, has_valid_json, count_media

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

def validate_poi(poi_dir: Path) -> list[str]:
    errors = []

    if not has_real_text(poi_dir / POI_MASTER_FILE, 100):
        errors.append("Falta contenido real en la Ficha del POI")

    if not has_valid_json(poi_dir / POI_JSON):
        errors.append("Falta poi.json válido")

    if count_media(poi_dir / SHARED_IMAGES_FOLDER, IMAGE_EXTENSIONS) == 0:
        errors.append("Faltan imágenes")

    for lang in LANGUAGES:
        lang_dir = poi_dir / lang
        if not lang_dir.exists():
            errors.append(f"Falta carpeta {lang}")
            continue

        if not has_real_text(lang_dir / TEXT_FILE, 100):
            errors.append(f"Falta texto real en {lang}")

        if not has_valid_json(lang_dir / META_FILE):
            errors.append(f"Falta meta.json válido en {lang}")

        if count_media(lang_dir / AUDIO_FOLDER, AUDIO_EXTENSIONS) == 0:
            errors.append(f"Falta audio en {lang}")

    return errors

def validate_text(poi_dir: Path) -> str:
    errors = validate_poi(poi_dir)
    return "POI completo y válido." if not errors else "\n".join(errors)
