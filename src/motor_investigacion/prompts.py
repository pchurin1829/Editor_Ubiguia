"""Carga de prompts versionados del Motor de Investigación de UBIGUIA.

Separa completamente el contenido de los prompts (conocimiento) del
código Python: este módulo solo lee archivos de texto desde
Docs/prompts/. No contiene ninguna lógica de IA ni de negocio, y nunca
devuelve un prompt de respaldo inventado si el archivo pedido no existe.
"""
from pathlib import Path

from config import project_root

NOMBRE_CARPETA_PROMPTS = "prompts"


class PromptNoEncontradoError(Exception):
    """El archivo de prompt solicitado no existe. cargar_prompt() nunca
    devuelve un prompt interno de respaldo ni inventa texto."""


def _carpeta_prompts() -> Path:
    return project_root() / "Docs" / NOMBRE_CARPETA_PROMPTS


def cargar_prompt(nombre: str) -> str:
    """Lee el contenido completo (UTF-8) de Docs/prompts/<nombre>.

    Lanza PromptNoEncontradoError si el archivo no existe — nunca
    devuelve un texto alternativo."""
    ruta = _carpeta_prompts() / nombre
    if not ruta.exists():
        raise PromptNoEncontradoError(f"No se encontró el archivo de prompt '{nombre}' en {_carpeta_prompts()}.")
    return ruta.read_text(encoding="utf-8")


def listar_prompts() -> list[str]:
    """Devuelve los nombres de los archivos de prompt disponibles en
    Docs/prompts/, ordenados alfabéticamente."""
    carpeta = _carpeta_prompts()
    if not carpeta.exists():
        return []
    return sorted(p.name for p in carpeta.iterdir() if p.is_file())
