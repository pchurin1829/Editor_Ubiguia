from pathlib import Path
import re
import webbrowser

from filesystem import safe_read_text


MARKERS = {
    "TEXT_ES": ("<<<TEXT_ES>>>", "<<<END_TEXT_ES>>>"),
    "TEXT_EN": ("<<<TEXT_EN>>>", "<<<END_TEXT_EN>>>"),
    "TEXT_PT": ("<<<TEXT_PT>>>", "<<<END_TEXT_PT>>>"),
    "AUDIO_ES": ("<<<AUDIO_ES>>>", "<<<END_AUDIO_ES>>>"),
    "AUDIO_EN": ("<<<AUDIO_EN>>>", "<<<END_AUDIO_EN>>>"),
    "AUDIO_PT": ("<<<AUDIO_PT>>>", "<<<END_AUDIO_PT>>>"),
}


def _write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def build_prompt(poi_dir: Path) -> str:
    master = safe_read_text(poi_dir / "POI_MASTER.md").strip()
    spanish = safe_read_text(poi_dir / "ESPAÑOL" / "texto.md").strip()
    name = poi_dir.name.split("-", 1)[-1].strip()

    if not master:
        master = "[La ficha del POI todavía está vacía.]"
    if not spanish:
        spanish = "[El texto español todavía está vacío.]"

    return f"""Prepará contenido turístico multilingüe para UBIGUIA.

REGLAS OBLIGATORIAS
1. No inventes datos, fechas, horarios, precios, direcciones ni enlaces.
2. Conservá nombres propios, instituciones, obras, referencias y fuentes.
3. Si una afirmación parece dudosa, redactala con prudencia y no agregues datos nuevos.
4. Usá un tono claro, atractivo y profesional para turistas.
5. El inglés debe ser internacional y natural.
6. El portugués debe ser portugués de Brasil.
7. Los guiones de audio deben sonar naturales al ser narrados.
8. Los guiones de audio no deben incluir Markdown, enlaces ni listas técnicas.
9. Devolvé solamente los seis bloques solicitados.
10. Conservá exactamente todos los marcadores <<<...>>>.
11. El texto ES debe quedar listo para publicar, no debe copiar instrucciones de plantilla.
12. EN y PT deben ser traducciones completas del texto ES final.

POI
{name}

FICHA DEL POI
----------------
{master}

TEXTO ESPAÑOL ACTUAL
----------------
{spanish}

FORMATO EXACTO DE RESPUESTA

<<<TEXT_ES>>>
Versión española revisada y lista para publicar en Markdown.
<<<END_TEXT_ES>>>

<<<TEXT_EN>>>
Traducción completa al inglés en Markdown.
<<<END_TEXT_EN>>>

<<<TEXT_PT>>>
Traducción completa al portugués de Brasil en Markdown.
<<<END_TEXT_PT>>>

<<<AUDIO_ES>>>
Guion natural para audio en español.
<<<END_AUDIO_ES>>>

<<<AUDIO_EN>>>
Guion natural para audio en inglés.
<<<END_AUDIO_EN>>>

<<<AUDIO_PT>>>
Guion natural para audio en portugués de Brasil.
<<<END_AUDIO_PT>>>"""


def extract_sections(text: str) -> dict[str, str]:
    result: dict[str, str] = {}

    for key, (start, end) in MARKERS.items():
        pattern = re.escape(start) + r"\s*(.*?)\s*" + re.escape(end)
        match = re.search(pattern, text, flags=re.DOTALL)

        if not match:
            raise ValueError(
                f"No se encontró el bloque {key}. "
                "Copie la respuesta completa de ChatGPT."
            )

        value = match.group(1).strip()
        if len(value) < 40:
            raise ValueError(f"El bloque {key} está vacío o incompleto.")

        result[key] = value

    return result


def save_sections(poi_dir: Path, data: dict[str, str]) -> None:
    _write_utf8(poi_dir / "ESPAÑOL" / "texto.md", data["TEXT_ES"])
    _write_utf8(poi_dir / "INGLES" / "texto.md", data["TEXT_EN"])
    _write_utf8(poi_dir / "PORTUGUES" / "texto.md", data["TEXT_PT"])

    _write_utf8(
        poi_dir / "ESPAÑOL" / "audio" / "guion_audio.md",
        data["AUDIO_ES"],
    )
    _write_utf8(
        poi_dir / "INGLES" / "audio" / "guion_audio.md",
        data["AUDIO_EN"],
    )
    _write_utf8(
        poi_dir / "PORTUGUES" / "audio" / "guion_audio.md",
        data["AUDIO_PT"],
    )


def open_chatgpt() -> None:
    webbrowser.open("https://chatgpt.com/")
