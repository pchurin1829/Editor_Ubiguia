from pathlib import Path
import json
import uuid
from datetime import datetime

from constants import (
    LANGUAGES, LANGUAGE_FOLDERS, TEXT_FILE, META_FILE, POI_JSON,
    POI_MASTER_FILE, OLD_POI_MASTER_PREFIX,
    POI_MASTER_TEMPLATE, TEXT_TEMPLATE, META_TEMPLATE, POI_JSON_TEMPLATE
)
from filesystem import ensure_dir, rewrite_utf8

def slug(value: str) -> str:
    return value.lower().strip().replace(" ", "-")

def city_path(turismo_root: str, country: str, province: str, city: str) -> Path:
    return Path(turismo_root) / country / province / city

def list_pois(turismo_root: str, country: str, province: str, city: str) -> list[str]:
    path = city_path(turismo_root, country, province, city)
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_dir()])

def next_poi_number(pois: list[str]) -> str:
    numbers = []
    for name in pois:
        prefix = name.split("-", 1)[0].strip()
        if prefix.isdigit():
            numbers.append(int(prefix))
    return f"{max(numbers, default=0) + 1:02d}"

def read_template(project_root: Path, filename: str) -> str:
    path = project_root / "templates" / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def fill_template(content: str, data: dict) -> str:
    for key, value in data.items():
        content = content.replace("{{" + key + "}}", str(value))
    return content

def create_poi(project_root: Path, turismo_root: str, country: str, province: str, city: str, number: str, name: str, category: str = "") -> Path:
    clean_name = name.strip()
    poi_dir = city_path(turismo_root, country, province, city) / f"{number}-{clean_name}"

    if poi_dir.exists():
        raise FileExistsError(f"Ya existe el POI: {poi_dir}")

    ensure_dir(poi_dir)

    poi_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{country}-{province}-{city}-{clean_name}"))
    now = datetime.now().isoformat(timespec="seconds")

    data = {
        "POI_ID": poi_id,
        "POI_ORDER": number,
        "POI_NAME": clean_name,
        "COUNTRY": country,
        "PROVINCE": province,
        "CITY": city,
        "CATEGORY": category,
        "COUNTRY_SLUG": slug(country),
        "PROVINCE_SLUG": slug(province),
        "CITY_SLUG": slug(city),
        "UPDATED_AT": now,
        "LANG": ""
    }

    master = fill_template(read_template(project_root, POI_MASTER_TEMPLATE), data)
    (poi_dir / POI_MASTER_FILE).write_text(master, encoding="utf-8")

    poi_template = read_template(project_root, POI_JSON_TEMPLATE)
    if poi_template.strip():
        poi_json_text = fill_template(poi_template, data)
        try:
            poi_json = json.loads(poi_json_text)
        except Exception:
            poi_json = {}
    else:
        poi_json = {}

    poi_json.update({
        "poi_id": poi_id,
        "poi_order": number,
        "poi_name": clean_name,
        "category": category,
        "country": country,
        "province": province,
        "city": city
    })
    (poi_dir / POI_JSON).write_text(json.dumps(poi_json, ensure_ascii=False, indent=4), encoding="utf-8")

    text_template = read_template(project_root, TEXT_TEMPLATE)
    meta_template = read_template(project_root, META_TEMPLATE)

    for lang in LANGUAGES:
        lang_dir = poi_dir / lang
        ensure_dir(lang_dir)
        for subfolder in LANGUAGE_FOLDERS:
            ensure_dir(lang_dir / subfolder)

        lang_data = data.copy()
        lang_data["LANG"] = lang

        (lang_dir / TEXT_FILE).write_text(fill_template(text_template, lang_data), encoding="utf-8")

        try:
            meta_data = json.loads(fill_template(meta_template, lang_data))
        except Exception:
            meta_data = {}

        meta_data.update({
            "poi_id": poi_id,
            "lang": lang,
            "title": clean_name,
            "content_markdown": TEXT_FILE,
            "updated_at": now,
            "version": 1
        })
        (lang_dir / META_FILE).write_text(json.dumps(meta_data, ensure_ascii=False, indent=4), encoding="utf-8")

    return poi_dir

def find_master_file(poi_dir: Path):
    master = poi_dir / POI_MASTER_FILE
    if master.exists():
        return master
    old_files = sorted(poi_dir.glob(f"{OLD_POI_MASTER_PREFIX}*.md"))
    return old_files[0] if old_files else None

def normalize_master_file(poi_dir: Path) -> bool:
    master = poi_dir / POI_MASTER_FILE
    if master.exists():
        return False
    old_files = sorted(poi_dir.glob(f"{OLD_POI_MASTER_PREFIX}*.md"))
    if old_files:
        old_files[0].rename(master)
        return True
    return False

def normalize_utf8_in_poi(poi_dir: Path) -> int:
    count = 0
    for path in poi_dir.rglob("*"):
        if path.is_file() and rewrite_utf8(path):
            count += 1
    return count
