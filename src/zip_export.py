from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import json

def safe_name(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("Ñ", "N")
        .replace("ñ", "n")
    )

def next_export_file(export_root: Path, city: str) -> Path:
    export_root.mkdir(parents=True, exist_ok=True)
    city_safe = safe_name(city)
    today = datetime.now().strftime("%Y%m%d")
    existing = sorted(export_root.glob(f"{city_safe}_POIS_{today}_v*.zip"))
    version = len(existing) + 1
    return export_root / f"{city_safe}_POIS_{today}_v{version:03d}.zip"

def build_manifest(country: str, province: str, city: str, poi_dirs: list[Path]) -> dict:
    return {
        "manifest_version": "1.0",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "country": country,
        "province": province,
        "city": city,
        "count": len(poi_dirs),
        "pois": [p.name for p in poi_dirs]
    }

def export_pois(export_root: Path, turismo_root: Path, country: str, province: str, city: str, poi_dirs: list[Path]) -> Path:
    zip_path = next_export_file(export_root, city)
    manifest = build_manifest(country, province, city, poi_dirs)

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
        z.writestr("MANIFIESTO.json", json.dumps(manifest, ensure_ascii=False, indent=4))
        for poi_dir in poi_dirs:
            for file in poi_dir.rglob("*"):
                if file.is_file():
                    arcname = Path(country) / province / city / poi_dir.name / file.relative_to(poi_dir)
                    z.write(file, arcname)

    return zip_path
